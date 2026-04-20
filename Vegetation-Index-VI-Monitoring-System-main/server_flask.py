
"""
Flask server for Soil Health prediction + recommendations with Bootstrap UI + Chart.js.

Usage:
  python3 server_flask.py
"""

from flask import Flask, request, jsonify, render_template_string
import joblib, os, math, json
import numpy as np
import pandas as pd

# --- Config (same logic as your pipeline) ---
THRESHOLDS = {'N': {'good': 80, 'medium': 40}, 'P': {'good': 30, 'medium': 15}, 'K': {'good': 150, 'medium': 80}}
BASE_DOSES = {'N': 60, 'P': 30, 'K': 80}
CROP_MULTIPLIERS = {"rice":1.0,"wheat":1.0,"maize":1.15,"groundnut":0.9,"soybean":0.8,"cotton":1.05,"sugarcane":1.2,"sunflower":0.95,"pulses":0.7}
SAFETY_CAPS = {'N': {'max_per_application': 200, 'max_per_year':250}, 'P': {'max_per_application':150,'max_per_year':200}, 'K': {'max_per_application':250,'max_per_year':300}}

CROP_DB = {
    "rice": {"N":(80,160),"P":(30,60),"K":(100,300),"pH":(5.5,6.5)},
    "wheat": {"N":(80,140),"P":(30,60),"K":(80,200),"pH":(6.0,7.5)},
    "maize": {"N":(80,200),"P":(30,70),"K":(100,250),"pH":(5.5,7.0)},
    "groundnut": {"N":(40,80),"P":(20,50),"K":(60,150),"pH":(5.0,6.5)},
    "soybean": {"N":(20,60),"P":(20,50),"K":(50,150),"pH":(5.5,7.0)},
    "cotton": {"N":(60,120),"P":(30,60),"K":(80,200),"pH":(5.5,7.5)},
    "sugarcane": {"N":(100,250),"P":(30,80),"K":(200,400),"pH":(5.5,7.0)},
    "sunflower": {"N":(40,100),"P":(30,60),"K":(80,160),"pH":(6.0,7.5)},
    "pulses": {"N":(10,40),"P":(15,40),"K":(50,120),"pH":(6.0,7.5)}
}

POSSIBLE_MODEL_PATHS = [
    "rf_soil_model.pkl",
    "outputs/rf_soil_model.pkl",
    "/mnt/data/rf_soil_model.pkl",
    os.path.join(os.getcwd(), "rf_soil_model.pkl")
]

app = Flask(__name__, static_folder='static')

# ----------------- Utility functions (copied/adapted) -----------------
def _range_distance(value, preferred_min, preferred_max):
    try:
        value = float(value)
    except Exception:
        return 1.0
    if math.isnan(value):
        return 1.0
    if preferred_min <= value <= preferred_max:
        return 0.0
    if value < preferred_min:
        diff = preferred_min - value
    else:
        diff = value - preferred_max
    span = max(1.0, (preferred_max - preferred_min))
    return min(3.0, diff / span)

def recommend_crops_for_soil(row: dict, crop_db: dict = CROP_DB, top_k: int = 3):
    soil_N = float(row.get('N', float('nan')))
    soil_P = float(row.get('P', float('nan')))
    soil_K = float(row.get('K', float('nan')))
    soil_pH = float(row.get('pH', float('nan')))
    soil_temp = row.get('temperature', None)
    soil_rain = row.get('rainfall', None)
    soil_hum = row.get('humidity', None)

    results = []
    for crop, req in crop_db.items():
        dN = _range_distance(soil_N, req['N'][0], req['N'][1])
        dP = _range_distance(soil_P, req['P'][0], req['P'][1])
        dK = _range_distance(soil_K, req['K'][0], req['K'][1])
        dpH = _range_distance(soil_pH, req['pH'][0], req['pH'][1])
        dtemp = 0.0; drain = 0.0; dhum = 0.0
        if soil_temp is not None and req.get('temp') is not None:
            try:
                dtemp = _range_distance(float(soil_temp), req['temp'][0], req['temp'][1])
            except: dtemp = 0.0
        if soil_rain is not None and req.get('rainfall') is not None:
            try:
                drain = _range_distance(float(soil_rain), req['rainfall'][0], req['rainfall'][1])
            except: drain = 0.0
        if soil_hum is not None and req.get('humidity') is not None:
            try:
                dhum = _range_distance(float(soil_hum), req['humidity'][0], req['humidity'][1])
            except: dhum = 0.0
        score = (0.35 * dN) + (0.20 * dK) + (0.15 * dP) + (0.15 * dpH) + (0.10 * dtemp) + (0.03 * drain) + (0.02 * dhum)
        reasons = []
        if dN > 0: reasons.append(f"N outside preferred ({req['N'][0]}-{req['N'][1]}): dist={dN:.2f}")
        if dP > 0: reasons.append(f"P outside preferred ({req['P'][0]}-{req['P'][1]}): dist={dP:.2f}")
        if dK > 0: reasons.append(f"K outside preferred ({req['K'][0]}-{req['K'][1]}): dist={dK:.2f}")
        if dpH > 0: reasons.append(f"pH outside preferred ({req['pH'][0]}-{req['pH'][1]}): dist={dpH:.2f}")
        results.append({
            'crop': crop,
            'score': float(score),
            'suitability_pct': max(0.0, round(100 * (1 - min(score / 3.0, 1.0)), 1)),
            'reasons': reasons
        })
    results = sorted(results, key=lambda x: x['score'])
    return results[:top_k]

def simple_recommendation(row: dict, proba=None, crop_multiplier: float = 1.0):
    recs = []
    tgt_N = THRESHOLDS['N']['good']
    tgt_P = THRESHOLDS['P']['good']
    tgt_K = THRESHOLDS['K']['good']
    if row.get('N', 0) < tgt_N:
        deficit_percent = max(0, (tgt_N - row['N']) / tgt_N)
        base = BASE_DOSES['N']
        raw_dose = base * (1 + deficit_percent*1.5)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['N']['max_per_application'], scaled)
        recs.append({'nutrient':'N','fertilizer':'Urea','dose_kg_per_ha':dose,
                     'rationale':f'N={row["N"]:.1f} < {tgt_N} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})
    if row.get('P', 0) < tgt_P:
        deficit_percent = max(0, (tgt_P - row['P']) / tgt_P)
        base = BASE_DOSES['P']
        raw_dose = base * (1 + deficit_percent*1.2)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['P']['max_per_application'], scaled)
        recs.append({'nutrient':'P','fertilizer':'DAP/SSP','dose_kg_per_ha':dose,
                     'rationale':f'P={row["P"]:.1f} < {tgt_P} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})
    if row.get('K', 0) < tgt_K:
        deficit_percent = max(0, (tgt_K - row['K']) / tgt_K)
        base = BASE_DOSES['K']
        raw_dose = base * (1 + deficit_percent*1.3)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['K']['max_per_application'], scaled)
        recs.append({'nutrient':'K','fertilizer':'MOP','dose_kg_per_ha':dose,
                     'rationale':f'K={row["K"]:.1f} < {tgt_K} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})
    conf = 'Unknown'
    if proba is not None:
        tp = max(proba)
        if tp >= 0.8: conf = 'High'
        elif tp >= 0.6: conf = 'Medium'
        else: conf = 'Low'
    return recs, conf

# ------------------ Model loading ------------------
# ------------------ Model loading (FIXED) ------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "rf_soil_model.pkl")

MODEL = None
MODEL_PATH_USED = None

if os.path.exists(MODEL_PATH):
    try:
        MODEL = joblib.load(MODEL_PATH)
        MODEL_PATH_USED = MODEL_PATH
        print("✅ Loaded model from:", MODEL_PATH)
    except Exception as e:
        print("❌ Failed to load model:", e)
else:
    print("❌ Model file not found at:", MODEL_PATH)

# try to load crop_requirements.csv if present (optional)
CROP_CSV_PATHS = ["crop_requirements.csv", "outputs/crop_requirements.csv", "/mnt/data/crop_requirements.csv"]
for pc in CROP_CSV_PATHS:
    if os.path.exists(pc):
        try:
            df_crop = pd.read_csv(pc)
            crop_db = {}
            for _, r in df_crop.iterrows():
                crop = str(r['crop'])
                crop_db[crop] = {
                    'N': (float(r['N_min']), float(r['N_max'])),
                    'P': (float(r['P_min']), float(r['P_max'])),
                    'K': (float(r['K_min']), float(r['K_max'])),
                    'pH': (float(r['pH_min']), float(r['pH_max']))
                }
            CROP_DB = crop_db
            print("Loaded crop CSV from:", pc)
            break
        except Exception as e:
            print("Found crop CSV but failed to parse:", pc, e)

# ------------------ Templates (Bootstrap + Chart.js) ------------------
INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Soil Health Advisor</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body class="bg-light">
<div class="container py-4">

  <!-- Header -->
  <div class="text-center mb-4">
    <h1 class="fw-bold">🌱 Soil Health Advisor</h1>
    <p class="text-muted">AI-powered soil analysis & crop recommendations</p>
  </div>

  <!-- Input Card -->
  <div class="card shadow-sm mb-4">
    <div class="card-body">
      <form id="soilForm" class="row g-3">
        <div class="col-md-3">
          <label class="form-label">Nitrogen (N)</label>
          <input class="form-control" name="N" required value="50">
        </div>
        <div class="col-md-3">
          <label class="form-label">Phosphorus (P)</label>
          <input class="form-control" name="P" required value="20">
        </div>
        <div class="col-md-3">
          <label class="form-label">Potassium (K)</label>
          <input class="form-control" name="K" required value="80">
        </div>
        <div class="col-md-3">
          <label class="form-label">pH</label>
          <input class="form-control" name="pH" required value="6.5">
        </div>

        <div class="col-md-4">
          <label class="form-label">Temperature (°C)</label>
          <input class="form-control" name="temperature">
        </div>
        <div class="col-md-4">
          <label class="form-label">Rainfall (mm)</label>
          <input class="form-control" name="rainfall">
        </div>
        <div class="col-md-4">
          <label class="form-label">Humidity (%)</label>
          <input class="form-control" name="humidity">
        </div>

        <div class="col-12 text-center">
          <button class="btn btn-success px-5">Analyze Soil</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Results -->
  <div id="results" style="display:none">

    <!-- Summary -->
    <div class="row mb-4">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-body text-center">
            <h6 class="text-muted">Soil Health</h6>
            <h3 id="soilLabel"></h3>
          </div>
        </div>
      </div>

      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-body">
            <h6 class="mb-2">Recommended Crops</h6>
            <ul class="list-group" id="cropList"></ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="row mb-4">
      <div class="col-md-6">
        <div class="card shadow-sm p-3">
          <h6>NPK Levels</h6>
          <canvas id="npkChart"></canvas>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card shadow-sm p-3">
          <h6>Crop Suitability (%)</h6>
          <canvas id="cropChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Fertilizer -->
    <div class="card shadow-sm">
      <div class="card-body">
        <h6>Fertilizer Recommendations</h6>
        <ul class="list-group" id="fertList"></ul>
      </div>
    </div>

  </div>
</div>

<script>
let npkChart, cropChart;

document.getElementById("soilForm").addEventListener("submit", async e => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const payload = Object.fromEntries(formData.entries());

  const res = await fetch("/predict", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json();

  document.getElementById("results").style.display = "block";
  document.getElementById("soilLabel").innerText = data.predicted_label;

  // Crops
  const cropList = document.getElementById("cropList");
  cropList.innerHTML = "";
  data.crop_recs.forEach(c => {
    cropList.innerHTML += `
      <li class="list-group-item d-flex justify-content-between">
        <span>${c.crop}</span>
        <span class="badge bg-success">${c.suitability_pct}%</span>
      </li>`;
  });

  // Fertilizers
  const fertList = document.getElementById("fertList");
  fertList.innerHTML = "";
  data.fertilizer_recs.forEach(f => {
    fertList.innerHTML += `
      <li class="list-group-item">
        <strong>${f.fertilizer}</strong> — ${f.dose_kg_per_ha} kg/ha
        <div class="text-muted small">${f.rationale}</div>
      </li>`;
  });

  // Charts
  const N = Number(payload.N), P = Number(payload.P), K = Number(payload.K);

  if (npkChart) npkChart.destroy();
  npkChart = new Chart(document.getElementById("npkChart"), {
    type: "bar",
    data: {
      labels: ["N","P","K"],
      datasets: [
        { label: "Actual", data: [N,P,K], backgroundColor: "#4caf50" },
        { label: "Good", data: [80,30,150], backgroundColor: "#c8e6c9" }
      ]
    }
  });

  if (cropChart) cropChart.destroy();
  cropChart = new Chart(document.getElementById("cropChart"), {
    type: "bar",
    data: {
      labels: data.crop_recs.map(c => c.crop),
      datasets: [{ data: data.crop_recs.map(c => c.suitability_pct), backgroundColor: "#ff9800" }]
    },
    options: { indexAxis: "y", scales: { x: { max: 100 } } }
  });
});
</script>

</body>
</html>
"""

# Backward-compatible alias for the legacy /predict_form route.
RESULT_HTML = INDEX_HTML



# ------------------ Routes ------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML, model_loaded=(MODEL is not None), model_path=MODEL_PATH_USED)

@app.route("/predict", methods=["POST"])
def predict():
    data = {}
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
        for k in ['N','P','K','pH','temperature','rainfall','humidity']:
            if k in data and data[k] != '':
                try:
                    data[k] = float(data[k])
                except:
                    pass
    for k in ['N','P','K','pH']:
        if k not in data:
            return jsonify({"error": f"Missing required field: {k}"}), 400

    X_row = pd.DataFrame([{
        'N': float(data['N']),
        'P': float(data['P']),
        'K': float(data['K']),
        'pH': float(data['pH']),
        'N_P_ratio': float(data['N'])/(float(data['P'])+1e-6),
        'N_K_ratio': float(data['N'])/(float(data['K'])+1e-6),
        'sum_NPK': float(data['N'])+float(data['P'])+float(data['K'])
    }])

    if MODEL is None:
        return jsonify({"error":"Model not loaded on server."}), 500

    pred = MODEL.predict(X_row)[0]
    proba = MODEL.predict_proba(X_row)[0].tolist()

    crop_input = {'N': float(data['N']), 'P': float(data['P']), 'K': float(data['K']), 'pH': float(data['pH'])}
    for opt in ['temperature','rainfall','humidity']:
        if opt in data and data[opt] != '' and data[opt] is not None:
            try:
                crop_input[opt] = float(data[opt])
            except:
                pass

    crop_recs = recommend_crops_for_soil(crop_input, CROP_DB, top_k=3)
    top_crop = crop_recs[0]['crop'] if len(crop_recs)>0 else None
    crop_mult = CROP_MULTIPLIERS.get(top_crop, 1.0)
    fert_recs, fert_conf = simple_recommendation(crop_input, proba=proba, crop_multiplier=crop_mult)

    return jsonify({
        "predicted_label": str(pred),
        "predicted_prob": proba,
        "fertilizer_recs": fert_recs,
        "fertilizer_confidence": fert_conf,
        "crop_recs": crop_recs
    })

@app.route("/predict_form", methods=["POST"])
def predict_form():
    # read & coerce form inputs
    form = request.form.to_dict()
    for k in ['N','P','K','pH','temperature','rainfall','humidity']:
        if k in form and form[k] != '':
            try:
                form[k] = float(form[k])
            except:
                pass

    # re-use predict logic but inline here to get extra context (actuals + thresholds)
    for k in ['N','P','K','pH']:
        if k not in form:
            return "Missing field: " + k, 400

    X_row = pd.DataFrame([{
        'N': float(form['N']),
        'P': float(form['P']),
        'K': float(form['K']),
        'pH': float(form['pH']),
        'N_P_ratio': float(form['N'])/(float(form['P'])+1e-6),
        'N_K_ratio': float(form['N'])/(float(form['K'])+1e-6),
        'sum_NPK': float(form['N'])+float(form['P'])+float(form['K'])
    }])

    if MODEL is None:
        return "Model not loaded on server.", 500

    pred = MODEL.predict(X_row)[0]
    proba = MODEL.predict_proba(X_row)[0].tolist()

    crop_input = {'N': float(form['N']), 'P': float(form['P']), 'K': float(form['K']), 'pH': float(form['pH'])}
    for opt in ['temperature','rainfall','humidity']:
        if opt in form and form[opt] != '' and form[opt] is not None:
            try:
                crop_input[opt] = float(form[opt])
            except:
                pass

    crop_recs = recommend_crops_for_soil(crop_input, CROP_DB, top_k=3)
    top_crop = crop_recs[0]['crop'] if len(crop_recs)>0 else None
    crop_mult = CROP_MULTIPLIERS.get(top_crop, 1.0)
    fert_recs, fert_conf = simple_recommendation(crop_input, proba=proba, crop_multiplier=crop_mult)

    # prepare chart data
    actuals = {'N': crop_input['N'], 'P': crop_input['P'], 'K': crop_input['K']}
    thresholds_vals = {'N': THRESHOLDS['N']['good'], 'P': THRESHOLDS['P']['good'], 'K': THRESHOLDS['K']['good']}

    return render_template_string(RESULT_HTML,
                                  predicted_label=str(pred),
                                  predicted_prob=proba,
                                  fertilizer_recs=fert_recs,
                                  fertilizer_confidence=fert_conf,
                                  crop_recs=crop_recs,
                                  model_path=MODEL_PATH_USED,
                                  actuals_json=json.dumps(actuals),
                                  thresholds_json=json.dumps(thresholds_vals),
                                  crop_recs_json=json.dumps(crop_recs))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
