#!/usr/bin/env python3
"""
soil_health_pipeline.py

Usage:
    python3 soil_health_pipeline.py --data Crop_recommendation.csv --outdir outputs [--crop-csv crop_requirements.csv]

Requirements:
    pip install pandas scikit-learn joblib matplotlib seaborn shap

Notes:
 - This script uses N, P, K, pH as features by default.
 - Thresholds and recommendation rules are configurable in the THRESHOLDS / BASE_DOSES dicts.
 - It will create an outputs directory (default: ./outputs) and save plots/models there.
 - New: supports crop_requirements CSV via --crop-csv and expands crop recs into separate columns.
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import json
import math
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

# Optional: shap for explainability
try:
    import shap
    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False

# ---------- Config (tweakable) ----------
RANDOM_SEED = 42

THRESHOLDS = {
    'N': {'good': 80, 'medium': 40},    # N >= 80 -> Good; 40-79 -> Medium; <40 -> Poor
    'P': {'good': 30, 'medium': 15},
    'K': {'good': 150, 'medium': 80}
}

BASE_DOSES = {
    'N': 60,   # kg/ha base for N
    'P': 30,   # kg/ha base for P
    'K': 80    # kg/ha base for K
}

# Crop-specific multipliers (used to scale recommended doses per crop)
# Edit as needed for your region/crop management: e.g., maize may need more N -> 1.2
CROP_MULTIPLIERS = {
    "rice": 1.0,
    "wheat": 1.0,
    "maize": 1.15,
    "groundnut": 0.9,
    "soybean": 0.8,
    "cotton": 1.05,
    "sugarcane": 1.2,
    "sunflower": 0.95,
    "pulses": 0.7
}

# Safety caps to avoid recommending unrealistic single-application doses
SAFETY_CAPS = {
    'N': {'max_per_application': 200, 'max_per_year': 250},  # kg/ha
    'P': {'max_per_application': 150, 'max_per_year': 200},
    'K': {'max_per_application': 250, 'max_per_year': 300}
}

# ---------- Crop DB (fallback) ----------
CROP_DB = {
    "rice": {
        "N": (80, 160), "P": (30, 60), "K": (100, 300), "pH": (5.5, 6.5),
        "temp": (20, 35), "rainfall": (1000, 2500), "humidity": (60, 95)
    },
    "wheat": {
        "N": (80, 140), "P": (30, 60), "K": (80, 200), "pH": (6.0, 7.5),
        "temp": (10, 25), "rainfall": (300, 900), "humidity": (50, 80)
    },
    "maize": {
        "N": (80, 200), "P": (30, 70), "K": (100, 250), "pH": (5.5, 7.0),
        "temp": (18, 32), "rainfall": (500, 1200), "humidity": (50, 80)
    },
    "groundnut": {
        "N": (40, 80), "P": (20, 50), "K": (60, 150), "pH": (5.0, 6.5),
        "temp": (20, 30), "rainfall": (500, 1000), "humidity": (50, 80)
    },
    "soybean": {
        "N": (20, 60), "P": (20, 50), "K": (50, 150), "pH": (5.5, 7.0),
        "temp": (20, 30), "rainfall": (400, 900), "humidity": (50, 80)
    },
    "cotton": {
        "N": (60, 120), "P": (30, 60), "K": (80, 200), "pH": (5.5, 7.5),
        "temp": (20, 32), "rainfall": (400, 1200), "humidity": (50, 80)
    },
    "sugarcane": {
        "N": (100, 250), "P": (30, 80), "K": (200, 400), "pH": (5.5, 7.0),
        "temp": (20, 35), "rainfall": (1000, 2000), "humidity": (60, 95)
    },
    "sunflower": {
        "N": (40, 100), "P": (30, 60), "K": (80, 160), "pH": (6.0, 7.5),
        "temp": (20, 30), "rainfall": (400, 900), "humidity": (40, 70)
    },
    "pulses": {
        "N": (10, 40), "P": (15, 40), "K": (50, 120), "pH": (6.0, 7.5),
        "temp": (15, 30), "rainfall": (300, 900), "humidity": (40, 70)
    }
}

# ---------- Utility functions ----------
def parse_args():
    p = argparse.ArgumentParser(description="Soil health pipeline (NPK-based)")
    p.add_argument("--data", "-d", type=str, default="Crop_recommendation.csv", help="Path to input CSV")
    p.add_argument("--outdir", "-o", type=str, default="outputs", help="Directory to write outputs")
    p.add_argument("--no-derived-eval", action="store_true",
                   help="Also run evaluation without derived features (ratios/sum) and compare")
    p.add_argument("--crop-csv", type=str, default=None,
                   help="Optional CSV path with crop requirements (overrides built-in CROP_DB).")
    return p.parse_args()

def load_crop_db_from_csv(path: str):
    """Load crop requirements from CSV file path and return crop_db dict."""
    crop_db = {}
    try:
        df_crop = pd.read_csv(path)
    except Exception as e:
        print(f"Could not read crop requirements from {path}: {e}")
        return None
    # Expect columns: crop, N_min, N_max, P_min, P_max, K_min, K_max, pH_min, pH_max, temp_min, temp_max, rainfall_min, rainfall_max, humidity_min, humidity_max
    for _, r in df_crop.iterrows():
        crop = str(r['crop'])
        crop_db[crop] = {
            'N': (float(r['N_min']), float(r['N_max'])),
            'P': (float(r['P_min']), float(r['P_max'])),
            'K': (float(r['K_min']), float(r['K_max'])),
            'pH': (float(r['pH_min']), float(r['pH_max'])),
            'temp': (float(r['temp_min']), float(r['temp_max'])) if 'temp_min' in r and not pd.isna(r['temp_min']) else None,
            'rainfall': (float(r['rainfall_min']), float(r['rainfall_max'])) if 'rainfall_min' in r and not pd.isna(r['rainfall_min']) else None,
            'humidity': (float(r['humidity_min']), float(r['humidity_max'])) if 'humidity_min' in r and not pd.isna(r['humidity_min']) else None
        }
    return crop_db

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

def recommend_crops_for_soil(row: Dict, crop_db: Dict = CROP_DB, top_k: int = 3):
    """
    Given a dict-like row with keys: N, P, K, pH, optionally temperature, rainfall, humidity
    Returns: list of top_k crops with (crop_name, score, suitability_pct, reasons)
    """
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
        dtemp = 0.0
        drain = 0.0
        dhum = 0.0
        if soil_temp is not None and req.get('temp') is not None:
            try:
                dtemp = _range_distance(float(soil_temp), req['temp'][0], req['temp'][1])
            except Exception:
                dtemp = 0.0
        if soil_rain is not None and req.get('rainfall') is not None:
            try:
                drain = _range_distance(float(soil_rain), req['rainfall'][0], req['rainfall'][1])
            except Exception:
                drain = 0.0
        if soil_hum is not None and req.get('humidity') is not None:
            try:
                dhum = _range_distance(float(soil_hum), req['humidity'][0], req['humidity'][1])
            except Exception:
                dhum = 0.0

        score = (0.35 * dN) + (0.20 * dK) + (0.15 * dP) + (0.15 * dpH) + (0.10 * dtemp) + (0.03 * drain) + (0.02 * dhum)
        reasons = []
        if dN > 0:
            reasons.append(f"N outside preferred ({req['N'][0]}-{req['N'][1]}): dist={dN:.2f}")
        if dP > 0:
            reasons.append(f"P outside preferred ({req['P'][0]}-{req['P'][1]}): dist={dP:.2f}")
        if dK > 0:
            reasons.append(f"K outside preferred ({req['K'][0]}-{req['K'][1]}): dist={dK:.2f}")
        if dpH > 0:
            reasons.append(f"pH outside preferred ({req['pH'][0]}-{req['pH'][1]}): dist={dpH:.2f}")
        if dtemp > 0:
            reasons.append(f"temp outside preferred ({req.get('temp')}): dist={dtemp:.2f}")
        if drain > 0:
            reasons.append(f"rainfall outside preferred ({req.get('rainfall')}): dist={drain:.2f}")

        results.append({
            'crop': crop,
            'score': float(score),
            'suitability_pct': max(0.0, round(100 * (1 - min(score / 3.0, 1.0)), 1)),
            'reasons': reasons
        })

    results = sorted(results, key=lambda x: x['score'])
    return results[:top_k]

# ---------- Other helpers (loading/cleaning/labeling) ----------
def load_and_clean(path):
    """Load CSV, drop irrelevant columns, rename to canonical names, drop NaNs in NPK."""
    df = pd.read_csv(path)
    print(f"Loaded dataset with shape: {df.shape}")
    # Drop unnamed columns
    unnamed = [c for c in df.columns if "Unnamed" in str(c)]
    if unnamed:
        df = df.drop(columns=unnamed)
    # Standardize column names if present in various cases
    col_map = {}
    lower_cols = {c.lower(): c for c in df.columns}
    if 'nitrogen' in lower_cols:
        col_map[lower_cols['nitrogen']] = 'N'
    if 'phosphorus' in lower_cols:
        col_map[lower_cols['phosphorus']] = 'P'
    if 'potassium' in lower_cols:
        col_map[lower_cols['potassium']] = 'K'
    if 'ph' in lower_cols:
        col_map[lower_cols['ph']] = 'pH'
    # handle label/crop columns if present
    if 'label' in lower_cols:
        col_map[lower_cols['label']] = 'crop_label'
    if 'soil_health_label' in lower_cols:
        col_map[lower_cols['soil_health_label']] = 'soil_health_label'
    df = df.rename(columns=col_map)
    # Ensure required columns exist
    required = ['N','P','K','pH']
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Required column '{r}' not found in dataset after renaming. Columns: {df.columns.tolist()}")
    # Drop rows missing N/P/K
    before = len(df)
    df = df.dropna(subset=['N','P','K'])
    after = len(df)
    print(f"Dropped {before-after} rows with missing N/P/K. Remaining: {len(df)}")
    # Ensure numeric types
    df['N'] = pd.to_numeric(df['N'], errors='coerce')
    df['P'] = pd.to_numeric(df['P'], errors='coerce')
    df['K'] = pd.to_numeric(df['K'], errors='coerce')
    df['pH'] = pd.to_numeric(df['pH'], errors='coerce')
    df = df.dropna(subset=['N','P','K','pH'])
    return df.reset_index(drop=True)

def nutrient_level(x, t_good, t_med):
    """Return 'G', 'M' or 'P'"""
    if x >= t_good:
        return 'G'
    if x >= t_med:
        return 'M'
    return 'P'

def create_soil_health_label(row, thresholds=THRESHOLDS):
    """Combine nutrient levels into overall soil health label: Good/Medium/Poor"""
    n = nutrient_level(row['N'], thresholds['N']['good'], thresholds['N']['medium'])
    p = nutrient_level(row['P'], thresholds['P']['good'], thresholds['P']['medium'])
    k = nutrient_level(row['K'], thresholds['K']['good'], thresholds['K']['medium'])
    levels = [n,p,k]
    good_count = levels.count('G')
    poor_count = levels.count('P')
    if good_count >= 2:
        return 'Good'
    if poor_count >= 2:
        return 'Poor'
    return 'Medium'

def add_features(df):
    """Add derived features used by the model"""
    df = df.copy()
    df['N_P_ratio'] = df['N'] / (df['P'] + 1e-6)
    df['N_K_ratio'] = df['N'] / (df['K'] + 1e-6)
    df['sum_NPK'] = df['N'] + df['P'] + df['K']
    return df

def simple_recommendation(row, proba=None, crop_multiplier: float = 1.0):
    """
    Rule-based recommendation list based on deficits.
    Applies crop_multiplier and safety caps.
    Returns: (recs_list, confidence_str)
    Each rec: dict with nutrient, fertilizer, dose_kg_per_ha, rationale
    """
    recs = []
    tgt_N = THRESHOLDS['N']['good']
    tgt_P = THRESHOLDS['P']['good']
    tgt_K = THRESHOLDS['K']['good']

    # N
    if row['N'] < tgt_N:
        deficit_percent = max(0, (tgt_N - row['N']) / tgt_N)
        base = BASE_DOSES['N']
        raw_dose = base * (1 + deficit_percent*1.5)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['N']['max_per_application'], scaled)
        recs.append({'nutrient':'N', 'fertilizer':'Urea (46% N) or local N source',
                     'dose_kg_per_ha':dose,
                     'rationale':f'N={row["N"]:.1f} < {tgt_N} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})
    # P
    if row['P'] < tgt_P:
        deficit_percent = max(0, (tgt_P - row['P']) / tgt_P)
        base = BASE_DOSES['P']
        raw_dose = base * (1 + deficit_percent*1.2)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['P']['max_per_application'], scaled)
        recs.append({'nutrient':'P', 'fertilizer':'DAP / SSP or local P source',
                     'dose_kg_per_ha':dose,
                     'rationale':f'P={row["P"]:.1f} < {tgt_P} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})
    # K
    if row['K'] < tgt_K:
        deficit_percent = max(0, (tgt_K - row['K']) / tgt_K)
        base = BASE_DOSES['K']
        raw_dose = base * (1 + deficit_percent*1.3)
        scaled = int(round(raw_dose * crop_multiplier))
        dose = min(SAFETY_CAPS['K']['max_per_application'], scaled)
        recs.append({'nutrient':'K', 'fertilizer':'MOP (Murate of Potash) or local K source',
                     'dose_kg_per_ha':dose,
                     'rationale':f'K={row["K"]:.1f} < {tgt_K} (deficit {deficit_percent*100:.0f}%) | raw:{raw_dose:.1f}, mult:{crop_multiplier:.2f}, capped:{dose}'})

    # Confidence
    if proba is not None:
        top_prob = max(proba)
        if top_prob >= 0.8:
            conf = 'High'
        elif top_prob >= 0.6:
            conf = 'Medium'
        else:
            conf = 'Low'
    else:
        conf = 'Unknown'
    return recs, conf

# ---------- Main pipeline ----------
def run_pipeline(data_path: str, outdir: str, run_no_derived_eval: bool = False, crop_csv: Optional[str] = None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    print("=== Soil Health Pipeline (NPK-based) ===")
    print(f"Data: {data_path}")
    print(f"Outputs: {outdir.resolve()}\n")

    if not os.path.exists(data_path):
        print(f"ERROR: Data file not found at {data_path}")
        sys.exit(1)

    # Load crop DB (from CSV if provided or available)
    crop_db = None
    if crop_csv and os.path.exists(crop_csv):
        crop_db = load_crop_db_from_csv(crop_csv)
        if crop_db:
            print(f"Loaded crop requirements from: {crop_csv}")
    else:
        # also try default file name in cwd
        default_crop_csv = "crop_requirements.csv"
        if os.path.exists(default_crop_csv):
            crop_db = load_crop_db_from_csv(default_crop_csv)
            if crop_db:
                print(f"Loaded crop requirements from: {default_crop_csv}")

    if crop_db is None:
        crop_db = CROP_DB
        print("Using built-in CROP_DB (no external crop CSV found).")

    df = load_and_clean(data_path)
    print("Columns after cleaning:", df.columns.tolist())

    # Compare existing labels (if present) with derived
    if 'soil_health_label' not in df.columns:
        df['soil_health_label'] = df.apply(create_soil_health_label, axis=1)
    else:
        df, frac_same = (df, None)  # keep existing behavior minimal here

    # Add derived features
    df = add_features(df)
    feature_cols = ['N','P','K','pH','N_P_ratio','N_K_ratio','sum_NPK']
    X = df[feature_cols]
    y = df['soil_health_label']

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                        stratify=y, random_state=RANDOM_SEED)

    # Train model
    clf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED)
    clf.fit(X_train, y_train)

    # Evaluation
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest accuracy (with derived features): {acc:.4f}\n")
    print("Classification report:")
    print(classification_report(y_test, y_pred))
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, y_pred))

    # CV
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring='f1_macro')
    print(f"\n5-fold CV macro-F1 scores: {np.round(cv_scores,3)}")
    print(f"Mean CV macro-F1: {cv_scores.mean():.3f}")

    # Feature importance plot
    fi = pd.Series(clf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\nFeature importances:")
    print(fi)
    plt.figure(figsize=(8,4))
    sns.barplot(x=fi.values, y=fi.index)
    plt.title("Feature importances (RandomForest)")
    plt.tight_layout()
    fi_path = Path(outdir) / "feature_importances.png"
    plt.savefig(fi_path, bbox_inches='tight')
    plt.close()
    print(f"Saved feature importances plot to {fi_path}")

    # SHAP (if available)
    if SHAP_AVAILABLE:
        try:
            print("\nComputing SHAP summary (sample of training data)...")
            explainer = shap.TreeExplainer(clf)
            sample = X_train.sample(min(200, len(X_train)), random_state=RANDOM_SEED)
            shap_values = explainer.shap_values(sample)
            shap_plot_path = Path(outdir) / "shap_summary.png"
            shap.summary_plot(shap_values, sample, show=False)
            plt.savefig(shap_plot_path, bbox_inches='tight')
            plt.close()
            print(f"Saved SHAP summary plot to {shap_plot_path}")
        except Exception as e:
            print("SHAP summary plotting failed:", e)
    else:
        print("\nNote: shap not installed — skip SHAP explainability. To enable, install `shap` via pip.")

    # Save model
    model_out = Path(outdir) / "rf_soil_model.pkl"
    joblib.dump(clf, model_out)
    print(f"\nSaved trained model to: {model_out}")

    # --- Predictions + recommendations for all test rows (and CSV export) ---
    X_test_full = X_test.copy().reset_index(drop=True)
    preds_full = clf.predict(X_test_full)
    probs_full = clf.predict_proba(X_test_full)
    out_df = X_test_full.copy()
    out_df['true_label'] = y_test.reset_index(drop=True)
    out_df['predicted_label'] = preds_full
    out_df['predicted_prob_max'] = probs_full.max(axis=1)

    fert_recs_list = []
    fert_conf_list = []
    crop_recs_json_list = []
    # also prepare expanded crop columns
    crop1, crop1_s, crop1_reasons = [], [], []
    crop2, crop2_s, crop2_reasons = [], [], []
    crop3, crop3_s, crop3_reasons = [], [], []

    for i, row in out_df.iterrows():
        row_dict = row.to_dict()

        # Prepare crop input with optional climate fields from original df (if available)
        crop_input = {'N': float(row_dict.get('N', np.nan)),
                      'P': float(row_dict.get('P', np.nan)),
                      'K': float(row_dict.get('K', np.nan)),
                      'pH': float(row_dict.get('pH', np.nan))}
        for opt in ['temperature', 'rainfall', 'humidity']:
            if opt in df.columns:
                # try to find matching original row
                mask = (df['N'] == row_dict.get('N')) & (df['P'] == row_dict.get('P')) & (df['K'] == row_dict.get('K')) & (df['pH'] == row_dict.get('pH'))
                if mask.any():
                    crop_input[opt] = df.loc[mask, opt].iloc[0]

        # Crop recommendations using loaded crop_db
        crop_recs = recommend_crops_for_soil(crop_input, crop_db, top_k=3)
        crop_recs_json_list.append(crop_recs)

        # Expand into columns
        def push_crop(rank, target_lists):
            if len(crop_recs) >= rank:
                item = crop_recs[rank-1]
                target_lists[0].append(item['crop'])
                target_lists[1].append(item['suitability_pct'])
                target_lists[2].append("; ".join(item['reasons']) if item['reasons'] else "")
            else:
                target_lists[0].append("")
                target_lists[1].append(np.nan)
                target_lists[2].append("")

        push_crop(1, (crop1, crop1_s, crop1_reasons))
        push_crop(2, (crop2, crop2_s, crop2_reasons))
        push_crop(3, (crop3, crop3_s, crop3_reasons))

        # Determine crop multiplier from top recommended crop (if exists)
        top_crop = crop_recs[0]['crop'] if len(crop_recs) > 0 else None
        crop_multiplier = CROP_MULTIPLIERS.get(top_crop, 1.0)

        # Fertilizer recommendations (apply multiplier + safety caps inside function)
        proba = probs_full[i]
        fert_recs, fert_conf = simple_recommendation(row_dict, proba=proba, crop_multiplier=crop_multiplier)
        fert_recs_list.append(fert_recs)
        fert_conf_list.append(fert_conf)

    out_df['fertilizer_recs'] = [json.dumps(x) for x in fert_recs_list]
    out_df['fertilizer_confidence'] = fert_conf_list
    out_df['crop_recs'] = [json.dumps(x) for x in crop_recs_json_list]

    # expanded crop columns
    out_df['crop1'] = crop1
    out_df['crop1_suitability'] = crop1_s
    out_df['crop1_reasons'] = crop1_reasons
    out_df['crop2'] = crop2
    out_df['crop2_suitability'] = crop2_s
    out_df['crop2_reasons'] = crop2_reasons
    out_df['crop3'] = crop3
    out_df['crop3_suitability'] = crop3_s
    out_df['crop3_reasons'] = crop3_reasons

    predictions_csv = Path(outdir) / "predictions_with_recs.csv"
    out_df.to_csv(predictions_csv, index=False)
    print(f"\nSaved predictions + recommendations CSV to: {predictions_csv}")

    # also save expanded CSV that's easier to open in Excel
    expanded_csv = Path(outdir) / "predictions_with_recs_expanded.csv"
    out_df.to_csv(expanded_csv, index=False)
    print(f"Saved expanded predictions CSV to: {expanded_csv}")

    # --------------- Demo small sample with crop recs (saved separately) ---------------
    print("\nExample predictions and recommendations (first 10 test samples):")
    X_test_small = X_test.head(10).copy().reset_index(drop=True)
    preds = clf.predict(X_test_small)
    probs = clf.predict_proba(X_test_small)
    demo_rows = X_test_small.copy()
    demo_rows['predicted_label'] = preds
    demo_rows['predicted_prob_max'] = probs.max(axis=1)
    print(demo_rows.head(10))

    demo_crop_list = []
    for i, row in demo_rows.iterrows():
        row_dict = row.to_dict()
        proba = probs[i]
        # get crop recs for demo input
        crop_input = {'N': float(row_dict.get('N', np.nan)),
                      'P': float(row_dict.get('P', np.nan)),
                      'K': float(row_dict.get('K', np.nan)),
                      'pH': float(row_dict.get('pH', np.nan))}
        crop_recs = recommend_crops_for_soil(crop_input, crop_db, top_k=3)

        # top crop multiplier
        top_crop = crop_recs[0]['crop'] if len(crop_recs) > 0 else None
        crop_multiplier = CROP_MULTIPLIERS.get(top_crop, 1.0)

        fert_recs, fert_conf = simple_recommendation(row_dict, proba=proba, crop_multiplier=crop_multiplier)
        demo_crop_list.append({'index': i, 'fert_recs': fert_recs, 'fert_conf': fert_conf, 'crop_recs': crop_recs})
        print(f"\nSample #{i} | Pred: {row_dict['predicted_label']} | TopProb: {probs[i].max():.3f} | Confidence: {fert_conf}")
        if fert_recs:
            for r in fert_recs:
                print(" -", r)
        else:
            print(" - No fertilizer recommendation (nutrients at/above target).")
        print(" Crop recommendations:")
        for rc in crop_recs:
            print(f"  - {rc['crop']} | suitability: {rc['suitability_pct']}% | reasons: {rc['reasons'][:2]}")

    demo_out_df = demo_rows.reset_index().merge(pd.DataFrame(demo_crop_list), left_index=True, right_index=True, how='left')
    demo_csv = Path(outdir) / "demo_with_crop_recs.csv"
    demo_out_df.to_csv(demo_csv, index=False)
    print(f"\nSaved demo crop recommendations to: {demo_csv}")

    # Optional: evaluate without derived features
    if run_no_derived_eval:
        print("\n--- Running evaluation WITHOUT derived features (ratios / sum_NPK) ---")
        base_features = ['N','P','K','pH']
        X_base = df[base_features]
        Xb_train, Xb_test, yb_train, yb_test = train_test_split(X_base, y, test_size=0.2,
                                                                stratify=y, random_state=RANDOM_SEED)
        clf2 = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED)
        clf2.fit(Xb_train, yb_train)
        yb_pred = clf2.predict(Xb_test)
        acc2 = accuracy_score(yb_test, yb_pred)
        print(f"\nTest accuracy (base features only): {acc2:.4f}")
        print(classification_report(yb_test, yb_pred))
        fi2 = pd.Series(clf2.feature_importances_, index=base_features).sort_values(ascending=False)
        print("\nFeature importances (base features):")
        print(fi2)
        # save model
        joblib.dump(clf2, Path(outdir) / "rf_soil_model_base_features.pkl")
        print(f"Saved base-features model to: {Path(outdir) / 'rf_soil_model_base_features.pkl'}")

    print("\nPipeline finished.")

def main():
    args = parse_args()
    run_pipeline(args.data, args.outdir, run_no_derived_eval=args.no_derived_eval, crop_csv=args.crop_csv)

if __name__ == "__main__":
    main()
