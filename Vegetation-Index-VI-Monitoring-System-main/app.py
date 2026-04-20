try:
    import ee
except ImportError:
    ee = None
import requests
import os
import sqlite3
import socket
import math
try:
    import joblib
except ImportError:
    joblib = None
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
try:
    from geopy.geocoders import Nominatim
except ImportError:
    Nominatim = None
import json
import ast
try:
    import pandas as pd
except ImportError:
    pd = None
from flask import make_response
import zipfile
import io
import sys
from datetime import timedelta
import traceback

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(APP_ROOT, "templates"),
    static_folder=os.path.join(APP_ROOT, "static"),
)

# -------------------------
# NETWORK CHECK
# -------------------------
def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        socket.create_connection(("oauth2.googleapis.com", 443), timeout=3)
        return True
    except OSError:
        return False

if not check_internet():
    print("⚠️ Warning: No internet connection detected")
    print("Earth Engine features will not work")

# -------------------------
# EARTH ENGINE INITIALIZATION
# -------------------------
EE_INITIALIZED = False

if ee is None:
    print("⚠️ Earth Engine package not installed - Earth Engine features disabled")
    EE_INITIALIZED = False
elif check_internet():
    try:
        try:
            ee.Initialize(project='mvaia-469805') #--------------replace your google project ID-------------
            EE_INITIALIZED = True
            print("✓ Earth Engine initialized successfully")
        except ee.EEException:
            print("⚠️ Need to authenticate Earth Engine")
            print("Run this command in terminal:")
            print("python -c \"import ee; ee.Authenticate()\"")
            print("Then restart the application.")
            EE_INITIALIZED = False
    except Exception as e:
        print(f"Earth Engine error: {e}")
        EE_INITIALIZED = False
else:
    print("⚠️ Running in offline mode - Earth Engine disabled")
    EE_INITIALIZED = False

if Nominatim is not None:
    geolocator = Nominatim(user_agent="ndvi_app")
else:
    geolocator = None
    print("⚠️ geopy is not installed - reverse geocoding disabled")
DB_FILE = "ndvi.db"
STATIC_DIR = "static/ndvi"
os.makedirs(STATIC_DIR, exist_ok=True)

def resolve_stored_path(path_value):
    """Resolve DB-stored file value to an on-disk path."""
    if not path_value:
        return None

    normalized = str(path_value).strip()
    if normalized.startswith("/static/"):
        normalized = normalized.lstrip("/")
    elif os.path.isabs(normalized):
        return normalized

    if normalized.startswith("static/"):
        return os.path.join(APP_ROOT, normalized)
    if os.path.dirname(normalized):
        return os.path.join(APP_ROOT, normalized)
    return os.path.join(APP_ROOT, STATIC_DIR, normalized)

def static_url_from_db_value(path_value):
    """Return public static URL from DB-stored file name/path."""
    if not path_value:
        return None
    return f"/static/ndvi/{os.path.basename(str(path_value))}"

def parse_polygon_coords(raw_value):
    """Parse polygon coordinates safely from DB text."""
    if not raw_value:
        return []

    if isinstance(raw_value, (list, tuple)):
        return list(raw_value)

    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    try:
        parsed = ast.literal_eval(raw_value)
        if isinstance(parsed, (list, tuple)):
            return list(parsed)
    except Exception:
        pass

    return []

# -------------------------
# UPDATED DATABASE SETUP WITH ALL METRICS
# -------------------------
def init_db():
    with sqlite3.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS ndvi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_name TEXT,
                datetime TEXT,
                timestamp TEXT,
                ndvi_png TEXT,
                ndvi_tif TEXT,
                polygon TEXT,
                rgb_png TEXT,
                savi_png TEXT,
                gndvi_png TEXT,
                evi_png TEXT,
                soil_health_png TEXT,
                crop_health_png TEXT,
                -- Soil Health Metrics
                soil_health_score REAL,
                moisture_index REAL,
                organic_matter REAL,
                texture_score REAL,
                ph_level REAL,
                -- Crop Health Metrics
                crop_health_score REAL,
                vigor_index REAL,
                stress_level REAL,
                yield_potential REAL,
                chlorophyll_content REAL
            )
        """)
        # Check if we need to migrate old schema
        cursor = con.execute("PRAGMA table_info(ndvi_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add missing columns if they don't exist
        new_columns = [
            'soil_health_score', 'moisture_index', 'organic_matter', 'texture_score', 'ph_level',
            'crop_health_score', 'vigor_index', 'stress_level', 'yield_potential', 'chlorophyll_content'
        ]
        
        for column in new_columns:
            if column not in columns:
                try:
                    con.execute(f"ALTER TABLE ndvi_history ADD COLUMN {column} REAL")
                    print(f"✓ Added column: {column}")
                except Exception as e:
                    print(f"⚠️ Could not add column {column}: {e}")

init_db()

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def calculate_polygon_area(bounds):
    """Calculate approximate area in square degrees"""
    min_lon, max_lon = bounds[0][0], bounds[2][0]
    min_lat, max_lat = bounds[0][1], bounds[2][1]
    return abs(max_lon - min_lon) * abs(max_lat - min_lat)

def reduce_polygon_size(polygon, target_area=0.1):
    """Reduce polygon size while maintaining center"""
    center = polygon.centroid().coordinates().getInfo()
    radius = math.sqrt(target_area) / 2
    
    smaller_coords = [
        [center[0] - radius, center[1] - radius],
        [center[0] + radius, center[1] - radius],
        [center[0] + radius, center[1] + radius],
        [center[0] - radius, center[1] + radius],
        [center[0] - radius, center[1] - radius]
    ]
    return ee.Geometry.Polygon(smaller_coords)

def normalize_value(value, min_val, max_val):
    """Normalize value to 0-1 range"""
    if value is None:
        return 0.5
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

def calculate_soil_health_metrics(image, polygon):
    """Calculate detailed soil health metrics"""
    try:
        print("Calculating soil health metrics...")
        
        # Get required bands
        nir = image.select('B8')
        red = image.select('B4')
        green = image.select('B3')
        blue = image.select('B2')
        swir1 = image.select('B11')
        swir2 = image.select('B12')
        
        # 1. Moisture Index (NDMI: (NIR - SWIR1) / (NIR + SWIR1))
        moisture_index = nir.subtract(swir1).divide(nir.add(swir1)).rename('moisture')
        
        # 2. Organic Matter Estimation
        # Using color indices - darker soils typically have more organic matter
        brightness = red.add(green).add(blue).divide(3)
        color_ratio = red.divide(green.add(blue).divide(2).add(0.001))  # Avoid division by zero
        organic_matter = brightness.multiply(color_ratio).rename('organic_matter')
        
        # 3. Texture Score (using SWIR bands - clay content affects SWIR reflectance)
        texture_score = swir1.subtract(swir2).divide(swir1.add(swir2).add(0.001)).rename('texture')
        
        # 4. pH Level estimation (simplified spectral model)
        # More alkaline soils often have higher red reflectance
        ph_estimation = red.divide(green.add(blue).divide(2).add(0.001)).rename('ph')
        
        # 5. Soil Adjusted Vegetation Index for soil exposure
        savi = nir.subtract(red).divide(nir.add(red).add(0.5)).multiply(1.5).rename('savi')
        
        # Calculate region statistics
        region_stats = ee.Dictionary({
            'moisture': moisture_index.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=30,
                maxPixels=1e9
            ).get('moisture'),
            'organic_matter': organic_matter.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=30,
                maxPixels=1e9
            ).get('organic_matter'),
            'texture': texture_score.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=30,
                maxPixels=1e9
            ).get('texture'),
            'ph': ph_estimation.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=30,
                maxPixels=1e9
            ).get('ph'),
            'savi': savi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=30,
                maxPixels=1e9
            ).get('savi')
        })
        
        stats = region_stats.getInfo()
        print(f"Soil stats raw: {stats}")
        
        # Extract and normalize values
        moisture_val = stats.get('moisture', 0.1) or 0.1
        organic_val = stats.get('organic_matter', 0.2) or 0.2
        texture_val = stats.get('texture', 0.05) or 0.05
        ph_val = stats.get('ph', 1.2) or 1.2
        savi_val = stats.get('savi', 0.1) or 0.1
        
        # Normalize to 0-100 scale
        moisture_norm = normalize_value(moisture_val, -0.3, 0.5) * 100
        organic_norm = normalize_value(organic_val, 0, 0.8) * 100
        texture_norm = normalize_value(texture_val, -0.2, 0.2) * 100
        
        # pH optimization (6.5-7.5 is optimal for most crops)
        # Convert our spectral index to approximate pH (6-8 range)
        ph_approx = 6.0 + (ph_val - 0.8) * 2.5
        ph_norm = max(0, min(100, 100 - abs(ph_approx - 7.0) * 20))
        
        # Soil exposure (lower SAVI means more soil exposure, which can be good or bad)
        soil_exposure = max(0, min(100, (0.3 - savi_val) * 333))
        
        # Calculate overall soil health score (weighted average)
        soil_health_score = (
            moisture_norm * 0.25 +          # Moisture importance
            organic_norm * 0.35 +           # Organic matter importance
            texture_norm * 0.15 +           # Texture importance
            ph_norm * 0.15 +                # pH importance
            soil_exposure * 0.10            # Soil exposure (not too vegetated, not too bare)
        )
        
        # Ensure scores are within 0-100 range
        soil_health_score = max(0, min(100, soil_health_score))
        moisture_norm = max(0, min(100, moisture_norm))
        organic_norm = max(0, min(100, organic_norm))
        texture_norm = max(0, min(100, texture_norm))
        
        return {
            'soil_health_score': round(soil_health_score, 1),
            'moisture_index': round(moisture_norm, 1),
            'organic_matter': round(organic_norm, 1),
            'texture_score': round(texture_norm, 1),
            'ph_level': round(ph_approx, 1)  # Actual estimated pH value
        }
        
    except Exception as e:
        print(f"❌ Error calculating soil metrics: {e}")
        traceback.print_exc()
        return {
            'soil_health_score': 50.0,
            'moisture_index': 50.0,
            'organic_matter': 50.0,
            'texture_score': 50.0,
            'ph_level': 7.0
        }

def calculate_crop_health_metrics(image, polygon):
    """Calculate detailed crop health metrics"""
    try:
        print("Calculating crop health metrics...")
        
        # Get required bands
        nir = image.select('B8')
        red = image.select('B4')
        green = image.select('B3')
        blue = image.select('B2')
        
        # 1. NDVI for plant vigor
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
        
        # 2. GNDVI for chlorophyll content
        gndvi = nir.subtract(green).divide(nir.add(green)).rename('gndvi')
        
        # 3. EVI for canopy structure
        evi = image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))',
            {'NIR': nir, 'RED': red, 'BLUE': blue}
        ).rename('evi')
        
        # 4. NDRE for nitrogen content (using red-edge if available, otherwise approximate)
        # For Sentinel-2, we can use B5 (red-edge 1) if available
        try:
            red_edge = image.select('B5')
            ndre = nir.subtract(red_edge).divide(nir.add(red_edge)).rename('ndre')
        except:
            # Approximate NDRE using other bands
            ndre = nir.subtract(red).divide(nir.add(red).add(0.1)).multiply(0.8).rename('ndre')
        
        # 5. Stress Index
        stress_index = image.expression(
            '1.0 - (0.7*NDVI + 0.3*GNDVI)',
            {'NDVI': ndvi, 'GNDVI': gndvi}
        ).rename('stress')
        
        # Calculate region statistics
        region_stats = ee.Dictionary({
            'ndvi': ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=20,
                maxPixels=1e9
            ).get('ndvi'),
            'gndvi': gndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=20,
                maxPixels=1e9
            ).get('gndvi'),
            'evi': evi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=20,
                maxPixels=1e9
            ).get('evi'),
            'ndre': ndre.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=20,
                maxPixels=1e9
            ).get('ndre'),
            'stress': stress_index.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=20,
                maxPixels=1e9
            ).get('stress')
        })
        
        stats = region_stats.getInfo()
        print(f"Crop stats raw: {stats}")
        
        # Extract values
        ndvi_val = stats.get('ndvi', 0.3) or 0.3
        gndvi_val = stats.get('gndvi', 0.2) or 0.2
        evi_val = stats.get('evi', 0.2) or 0.2
        ndre_val = stats.get('ndre', 0.15) or 0.15
        stress_val = stats.get('stress', 0.5) or 0.5
        
        # Calculate individual metrics (0-100 scale)
        # 1. Vigor Index (primarily based on NDVI)
        vigor_index = max(0, min(100, (ndvi_val + 0.3) * 100))
        
        # 2. Chlorophyll Content (primarily based on GNDVI and NDRE)
        chlorophyll_content = max(0, min(100, (gndvi_val * 0.7 + ndre_val * 0.3) * 100))
        
        # 3. Stress Level (inverse of health)
        stress_level = max(0, min(100, stress_val * 100))
        
        # 4. Canopy Structure (based on EVI)
        canopy_structure = max(0, min(100, (evi_val + 0.2) * 100))
        
        # 5. Yield Potential (composite index)
        yield_potential = (
            vigor_index * 0.30 +           # Biomass
            chlorophyll_content * 0.25 +    # Chlorophyll
            canopy_structure * 0.25 +       # Canopy structure
            (100 - stress_level) * 0.20     # Low stress
        )
        
        # Overall Crop Health Score
        crop_health_score = (
            vigor_index * 0.25 +
            chlorophyll_content * 0.25 +
            canopy_structure * 0.20 +
            (100 - stress_level) * 0.20 +
            yield_potential * 0.10
        )
        
        # Ensure scores are within 0-100 range
        crop_health_score = max(0, min(100, crop_health_score))
        vigor_index = max(0, min(100, vigor_index))
        chlorophyll_content = max(0, min(100, chlorophyll_content))
        stress_level = max(0, min(100, stress_level))
        yield_potential = max(0, min(100, yield_potential))
        
        return {
            'crop_health_score': round(crop_health_score, 1),
            'vigor_index': round(vigor_index, 1),
            'chlorophyll_content': round(chlorophyll_content, 1),
            'stress_level': round(stress_level, 1),
            'yield_potential': round(yield_potential, 1)
        }
        
    except Exception as e:
        print(f"❌ Error calculating crop metrics: {e}")
        traceback.print_exc()
        return {
            'crop_health_score': 50.0,
            'vigor_index': 50.0,
            'chlorophyll_content': 50.0,
            'stress_level': 50.0,
            'yield_potential': 50.0
        }

# -------------------------
# COLOR PALETTE DEFINITIONS
# -------------------------
COLOR_PALETTES = {
    'NDVI': {
        'palette': ['#8B0000', '#FF0000', '#FF8C00', '#FFD700', '#ADFF2F', '#32CD32', '#228B22', '#006400'],
        'min': 0,
        'max': 1,
        'ranges': [
            {'min': 0.0, 'max': 0.2, 'color': '#8B0000', 'label': 'Severe Stress'},
            {'min': 0.2, 'max': 0.3, 'color': '#FF0000', 'label': 'High Stress'},
            {'min': 0.3, 'max': 0.4, 'color': '#FF8C00', 'label': 'Moderate Stress'},
            {'min': 0.4, 'max': 0.5, 'color': '#FFD700', 'label': 'Fair'},
            {'min': 0.5, 'max': 0.6, 'color': '#ADFF2F', 'label': 'Good'},
            {'min': 0.6, 'max': 0.7, 'color': '#32CD32', 'label': 'Very Good'},
            {'min': 0.7, 'max': 0.8, 'color': '#228B22', 'label': 'Excellent'},
            {'min': 0.8, 'max': 1.0, 'color': '#006400', 'label': 'Optimal'}
        ]
    },
    'SOIL_HEALTH': {
        'palette': ['#654321', '#8B4513', '#D2691E', '#F4A460', '#D2B48C', '#F5DEB3'],
        'min': 0,
        'max': 100,
        'ranges': [
            {'min': 0, 'max': 20, 'color': '#654321', 'label': 'Very Poor (0-20)'},
            {'min': 20, 'max': 40, 'color': '#8B4513', 'label': 'Poor (20-40)'},
            {'min': 40, 'max': 60, 'color': '#D2691E', 'label': 'Fair (40-60)'},
            {'min': 60, 'max': 75, 'color': '#F4A460', 'label': 'Good (60-75)'},
            {'min': 75, 'max': 90, 'color': '#D2B48C', 'label': 'Very Good (75-90)'},
            {'min': 90, 'max': 100, 'color': '#F5DEB3', 'label': 'Excellent (90-100)'}
        ]
    },
    'CROP_HEALTH': {
        'palette': ['#8B0000', '#FF0000', '#FF8C00', '#FFD700', '#9ACD32', '#32CD32', '#228B22', '#006400'],
        'min': 0,
        'max': 100,
        'ranges': [
            {'min': 0, 'max': 20, 'color': '#8B0000', 'label': 'Critical (0-20)'},
            {'min': 20, 'max': 40, 'color': '#FF0000', 'label': 'Poor (20-40)'},
            {'min': 40, 'max': 60, 'color': '#FF8C00', 'label': 'Fair (40-60)'},
            {'min': 60, 'max': 75, 'color': '#FFD700', 'label': 'Good (60-75)'},
            {'min': 75, 'max': 85, 'color': '#9ACD32', 'label': 'Very Good (75-85)'},
            {'min': 85, 'max': 95, 'color': '#32CD32', 'label': 'Excellent (85-95)'},
            {'min': 95, 'max': 100, 'color': '#006400', 'label': 'Optimal (95-100)'}
        ]
    },
    'GNDVI': {
        'palette': ['#2c3e50', '#95a5a6', '#f1c40f', '#f39c12', '#27ae60', '#2ecc71', '#1e8449'],
        'min': -1,
        'max': 1,
        'ranges': [
            {'min': -1.0, 'max': 0.0, 'color': '#2c3e50', 'label': 'Water/Clouds'},
            {'min': 0.0, 'max': 0.3, 'color': '#f1c40f', 'label': 'Stress/Chlorophyll Deficiency'},
            {'min': 0.3, 'max': 0.6, 'color': '#27ae60', 'label': 'Light to Medium Greens'},
            {'min': 0.6, 'max': 0.8, 'color': '#2ecc71', 'label': 'Healthy Vegetation'},
            {'min': 0.8, 'max': 1.0, 'color': '#1e8449', 'label': 'Very Healthy, High Chlorophyll'}
        ]
    },
    'SAVI': {
        'palette': ['#8B4513', '#D2B48C', '#F4A460', '#90EE90', '#32CD32', '#228B22'],
        'min': -1,
        'max': 1,
        'ranges': [
            {'min': -1.0, 'max': 0.1, 'color': '#8B4513', 'label': 'Bare Soil, Water'},
            {'min': 0.1, 'max': 0.3, 'color': '#F4A460', 'label': 'Sparse Vegetation'},
            {'min': 0.3, 'max': 0.5, 'color': '#90EE90', 'label': 'Yellow-Greens'},
            {'min': 0.5, 'max': 0.7, 'color': '#32CD32', 'label': 'Medium Greens'},
            {'min': 0.7, 'max': 1.0, 'color': '#228B22', 'label': 'Dense Vegetation'}
        ]
    },
    'EVI': {
        'palette': ['#4B0082', '#4169E1', '#FF4500', '#FF8C00', '#FFD700', '#9ACD32', '#006400'],
        'min': -1,
        'max': 1,
        'ranges': [
            {'min': -1.0, 'max': 0.1, 'color': '#4B0082', 'label': 'Water, Clouds, Snow'},
            {'min': 0.1, 'max': 0.3, 'color': '#FF4500', 'label': 'Sparse Vegetation, Soil'},
            {'min': 0.3, 'max': 0.5, 'color': '#FFD700', 'label': 'Yellows/Light Greens'},
            {'min': 0.5, 'max': 0.7, 'color': '#9ACD32', 'label': 'Medium to Bright Greens'},
            {'min': 0.7, 'max': 1.0, 'color': '#006400', 'label': 'Very Dense Canopy'}
        ]
    }
}

# -------------------------
# ROUTES
# -------------------------
@app.route("/")
def index():
    """Render the main map page"""
    return render_template("map.html")

@app.route("/map")
def map_page():
    """Render the main map page"""
    return render_template("map.html")

@app.route("/soil")
def soil_page():
    return render_template("soil.html")

@app.route("/statistics")
def statistics_page():
    """Render the statistics dashboard page"""
    return render_template("statistics.html")

@app.route("/history")
def history():
    """Render the new history page"""
    return render_template("history.html")

@app.route("/health_analysis")
def health_analysis():
    """Render the Soil & Crop Health Analysis page"""
    return render_template("health_analysis.html")

@app.route("/get_ndvi", methods=["POST"])
def get_ndvi():
    if not EE_INITIALIZED or ee is None:
        return jsonify({"error": "Earth Engine is not available on this server"}), 503

    data = request.get_json(silent=True) or {}
    polygon_coords = data.get("polygon")
    if not polygon_coords:
        return jsonify({"error": "Missing required field: polygon"}), 400
    
    # Create polygon with validation
    try:
        polygon = ee.Geometry.Polygon(polygon_coords)
        bounds = polygon.bounds().getInfo()['coordinates'][0]
        
        # Ensure polygon isn't too large
        area = calculate_polygon_area(bounds)
        if area > 0.25:  # More than ~0.25 sq degrees
            polygon = reduce_polygon_size(polygon, target_area=0.1)
            print(f"⚠️ Reduced polygon size to ~0.1 sq degrees")
    except Exception as e:
        print(f"Error creating polygon: {e}")
        return jsonify({"error": "Invalid polygon coordinates"})
    
    # Get place name
    if geolocator is None:
        place_name = "Unknown_Area"
    else:
        try:
            center = polygon.centroid().coordinates().getInfo()
            location = geolocator.reverse(f"{center[1]}, {center[0]}", timeout=5)
            place_name = location.address.split(",")[0] if location else "Unknown_Area"
            place_name = place_name.replace(" ", "_")
        except Exception as e:
            print(f"Geocoding error: {e}")
            place_name = "Unknown_Area"
    
    # Create timestamps
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    display_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Define file paths
    files = {}
    for index in ['NDVI', 'RGB', 'SAVI', 'GNDVI', 'EVI', 'SOIL_HEALTH', 'CROP_HEALTH']:
        files[index.lower()] = f"{STATIC_DIR}/{place_name}_{timestamp}_{index}.png"
    
    # Get image collection
    try:
        # Try to get recent imagery (last 3 months)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(polygon)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
            .sort('CLOUDY_PIXEL_PERCENTAGE')
        )
        
        if collection.size().getInfo() == 0:
            # Try with less strict cloud filter
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(polygon)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                .sort('CLOUDY_PIXEL_PERCENTAGE')
            )
        
        collection_size = collection.size().getInfo()
        print(f"Found {collection_size} images in collection")
        
        if collection_size == 0:
            return jsonify({"no_data": True, "message": "No cloud-free satellite imagery available for this location and time period."})
        
        # Get the least cloudy image
        image = collection.first().clip(polygon)
        print(f"Using image with {image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()}% cloud cover")
        print(f"Image bands: {image.bandNames().getInfo()}")
        
    except Exception as e:
        print(f"Error getting image collection: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to get satellite imagery", "details": str(e)})
    
    # Calculate detailed metrics
    print("\n=== Calculating Health Metrics ===")
    soil_metrics = calculate_soil_health_metrics(image, polygon)
    crop_metrics = calculate_crop_health_metrics(image, polygon)
    
    print(f"\nSoil Health Metrics: {soil_metrics}")
    print(f"Crop Health Metrics: {crop_metrics}")
    
    # Common thumbnail parameters
    thumb_params = {
        "region": polygon,
        "dimensions": 350,
        "format": "png"
    }
    
    results = {}
    errors = []
    
    # Generate NDVI
    try:
        nir = image.select("B8")
        red = image.select("B4")
        ndvi_raw = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        ndvi_manual = ndvi_raw.max(0).rename("NDVI")
        
        ndvi_params = thumb_params.copy()
        ndvi_params.update({
            "min": COLOR_PALETTES['NDVI']['min'],
            "max": COLOR_PALETTES['NDVI']['max'],
            "palette": COLOR_PALETTES['NDVI']['palette']
        })
        
        ndvi_url = ndvi_manual.getThumbURL(ndvi_params)
        response = requests.get(ndvi_url, timeout=60)
        if response.status_code == 200:
            with open(files['ndvi'], "wb") as f:
                f.write(response.content)
            results['image'] = "/" + files['ndvi']
            print("✓ NDVI generated successfully")
        else:
            errors.append(f"NDVI HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ NDVI generation failed: {e}")
        errors.append("NDVI")
    
    # Generate RGB
    try:
        rgb_params = {
            'region': polygon,
            'dimensions': 350,
            'format': 'png',
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 3000,
            'gamma': 1.4
        }
        
        rgb_url = image.getThumbURL(rgb_params)
        response = requests.get(rgb_url, timeout=60)
        if response.status_code == 200:
            with open(files['rgb'], "wb") as f:
                f.write(response.content)
            results['rgb'] = "/" + files['rgb']
            print(f"✓ RGB image saved")
        else:
            errors.append(f"RGB HTTP {response.status_code}")
    except Exception as e:
        print(f"RGB generation failed: {str(e)}")
        errors.append("RGB")
    
    # Generate other indices
    indices = [
        ('SAVI', image.expression(
            '((NIR - RED) / (NIR + RED + 0.5)) * (1 + 0.5)',
            {'NIR': image.select('B8'), 'RED': image.select('B4')}
        ).rename('SAVI')),
        ('GNDVI', image.normalizedDifference(["B8", "B3"]).rename('GNDVI')),
        ('EVI', image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))',
            {'NIR': image.select('B8'), 'RED': image.select('B4'), 'BLUE': image.select('B2')}
        ).rename('EVI')),
        # Soil Health Index (scaled to 0-100)
        ('SOIL_HEALTH', image.expression(
            '50 + (SAVI * 50)',  # Scale SAVI from [-1,1] to [0,100]
            {'SAVI': image.expression(
                '((NIR - RED) / (NIR + RED + 0.5)) * (1 + 0.5)',
                {'NIR': image.select('B8'), 'RED': image.select('B4')}
            )}
        ).rename('SOIL_HEALTH')),
        # Crop Health Index (scaled to 0-100)
        ('CROP_HEALTH', image.expression(
            '50 + (NDVI * 50)',  # Scale NDVI from [-1,1] to [0,100]
            {'NDVI': image.normalizedDifference(["B8", "B4"])}
        ).rename('CROP_HEALTH'))
    ]
    
    for name, idx in indices:
        try:
            idx_params = thumb_params.copy()
            
            if name in COLOR_PALETTES:
                palette_info = COLOR_PALETTES[name]
                idx_params.update({
                    "min": palette_info['min'],
                    "max": palette_info['max'],
                    "palette": palette_info['palette']
                })
            
            idx_url = idx.getThumbURL(idx_params)
            response = requests.get(idx_url, timeout=30)
            
            if response.status_code == 200:
                with open(files[name.lower()], "wb") as f:
                    f.write(response.content)
                results[name.lower()] = "/" + files[name.lower()]
                print(f"✓ {name} generated")
        except Exception as e:
            print(f"{name} error: {e}")
            errors.append(name)
    
    # Save to database with metrics
    if results:
        try:
            with sqlite3.connect(DB_FILE) as con:
                cursor = con.execute("""
                    INSERT INTO ndvi_history
                    (place_name, datetime, timestamp, ndvi_png, ndvi_tif, polygon, 
                    rgb_png, savi_png, gndvi_png, evi_png, soil_health_png, crop_health_png,
                    soil_health_score, moisture_index, organic_matter, texture_score, ph_level,
                    crop_health_score, vigor_index, stress_level, yield_potential, chlorophyll_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    place_name, 
                    display_date,
                    timestamp,
                    os.path.basename(files['ndvi']) if os.path.exists(files['ndvi']) else None,
                    None,  # GeoTIFF placeholder
                    str(polygon_coords),
                    os.path.basename(files['rgb']) if os.path.exists(files['rgb']) else None,
                    os.path.basename(files['savi']) if os.path.exists(files['savi']) else None,
                    os.path.basename(files['gndvi']) if os.path.exists(files['gndvi']) else None,
                    os.path.basename(files['evi']) if os.path.exists(files['evi']) else None,
                    os.path.basename(files['soil_health']) if os.path.exists(files['soil_health']) else None,
                    os.path.basename(files['crop_health']) if os.path.exists(files['crop_health']) else None,
                    soil_metrics['soil_health_score'],
                                        soil_metrics['moisture_index'],
                    soil_metrics['organic_matter'],
                    soil_metrics['texture_score'],
                    soil_metrics['ph_level'],
                    crop_metrics['crop_health_score'],
                    crop_metrics['vigor_index'],
                    crop_metrics['stress_level'],
                    crop_metrics['yield_potential'],
                    crop_metrics['chlorophyll_content']
                ))
                analysis_id = cursor.lastrowid
            print(f"✓ Database entry saved with metrics (ID: {analysis_id})")
        except Exception as e:
            print(f"❌ Database error: {e}")
            traceback.print_exc()
    
    # Return results
    if errors:
        results['warnings'] = f"Failed to generate: {', '.join(errors)}"
    
    results['place'] = place_name
    results['timestamp'] = display_date
    
    # Add metrics to results
    results['soil_metrics'] = soil_metrics
    results['crop_metrics'] = crop_metrics
    
    # Add recommendations
    results['recommendations'] = get_health_recommendations(soil_metrics, crop_metrics)
    
    # Add color palette information
    results['color_info'] = {
        'NDVI': {'ranges': COLOR_PALETTES['NDVI']['ranges']},
        'SOIL_HEALTH': {'ranges': COLOR_PALETTES['SOIL_HEALTH']['ranges']},
        'CROP_HEALTH': {'ranges': COLOR_PALETTES['CROP_HEALTH']['ranges']},
        'GNDVI': {'ranges': COLOR_PALETTES['GNDVI']['ranges']},
        'SAVI': {'ranges': COLOR_PALETTES['SAVI']['ranges']},
        'EVI': {'ranges': COLOR_PALETTES['EVI']['ranges']}
    }
    
    return jsonify(results)

def get_health_recommendations(soil_metrics, crop_metrics):
    """Generate recommendations based on health metrics"""
    recommendations = []
    
    # Soil recommendations
    soil_score = soil_metrics.get('soil_health_score', soil_metrics.get('health_score', 50))
    moisture = soil_metrics.get('moisture_index', 50)
    organic = soil_metrics.get('organic_matter', 50)
    ph = soil_metrics.get('ph_level', 7.0)
    
    if soil_score < 40:
        recommendations.append("🚨 **Urgent Soil Improvement Needed**: Soil health is critically low. Consider comprehensive soil testing and amendment.")
    elif soil_score < 60:
        recommendations.append("⚠️ **Soil Improvement Recommended**: Soil health is below optimal. Consider adding organic amendments.")
    
    if moisture < 30:
        recommendations.append("💧 **Low Soil Moisture**: Consider irrigation or water conservation practices.")
    elif moisture > 80:
        recommendations.append("🌧️ **High Soil Moisture**: Ensure proper drainage to prevent waterlogging.")
    
    if organic < 40:
        recommendations.append("🌱 **Low Organic Matter**: Add compost, manure, or cover crops to improve soil fertility.")
    
    if ph < 6.0:
        recommendations.append("🧪 **Acidic Soil (pH < 6.0)**: Consider adding lime to raise pH for better nutrient availability.")
    elif ph > 7.5:
        recommendations.append("🧪 **Alkaline Soil (pH > 7.5)**: Consider adding sulfur or organic matter to lower pH.")
    
    # Crop recommendations
    crop_score = crop_metrics.get('crop_health_score', crop_metrics.get('health_score', 50))
    vigor = crop_metrics.get('vigor_index', 50)
    stress = crop_metrics.get('stress_level', 50)
    chlorophyll = crop_metrics.get('chlorophyll_content', 50)
    
    if crop_score < 40:
        recommendations.append("🚨 **Critical Crop Health**: Immediate intervention needed. Check for pests, diseases, or nutrient deficiencies.")
    elif crop_score < 60:
        recommendations.append("⚠️ **Moderate Crop Stress**: Monitor closely and consider targeted interventions.")
    
    if vigor < 40:
        recommendations.append("📉 **Low Plant Vigor**: Consider nitrogen-rich fertilizer or growth promoters.")
    
    if stress > 60:
        recommendations.append("😓 **High Stress Levels**: Check for water stress, heat stress, or pest pressure.")
    
    if chlorophyll < 40:
        recommendations.append("🍃 **Low Chlorophyll**: Consider nitrogen or magnesium supplementation.")
    
    # Positive feedback for good conditions
    if soil_score > 75:
        recommendations.append("✅ **Excellent Soil Health**: Maintain current management practices.")
    
    if crop_score > 75:
        recommendations.append("✅ **Excellent Crop Health**: Optimal growing conditions detected.")
    
    # General recommendations
    if len(recommendations) == 0:
        recommendations.append("✅ **Good overall conditions**: Continue current management practices.")
    
    return recommendations

@app.route("/get_detailed_health_metrics")
def get_detailed_health_metrics():
    """Get detailed health metrics for a specific analysis"""
    try:
        analysis_id = request.args.get('id')
        
        if not analysis_id:
            return jsonify({'success': False, 'error': 'No ID provided'}), 400
        
        with sqlite3.connect(DB_FILE) as con:
            row = con.execute("""
                SELECT 
                    soil_health_score, moisture_index, organic_matter, texture_score, ph_level,
                    crop_health_score, vigor_index, stress_level, yield_potential, chlorophyll_content,
                    place_name, datetime, timestamp, ndvi_png, rgb_png, soil_health_png, crop_health_png
                FROM ndvi_history 
                WHERE id = ?
            """, (analysis_id,)).fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Analysis not found'}), 404
        
        # Organize metrics
        soil_metrics = {
            'health_score': row[0] if row[0] is not None else 0,
            'moisture_index': row[1] if row[1] is not None else 0,
            'organic_matter': row[2] if row[2] is not None else 0,
            'texture_score': row[3] if row[3] is not None else 0,
            'ph_level': row[4] if row[4] is not None else 7.0
        }
        
        crop_metrics = {
            'health_score': row[5] if row[5] is not None else 0,
            'vigor_index': row[6] if row[6] is not None else 0,
            'stress_level': row[7] if row[7] is not None else 0,
            'yield_potential': row[8] if row[8] is not None else 0,
            'chlorophyll_content': row[9] if row[9] is not None else 0
        }
        
        # Check if files exist
        file_status = {}
        files_to_check = {
            'ndvi_png': row[13],
            'rgb_png': row[14],
            'soil_health_png': row[15],
            'crop_health_png': row[16]
        }
        
        for key, filename in files_to_check.items():
            if filename:
                full_path = resolve_stored_path(filename)
                file_status[key] = {
                    'exists': os.path.exists(full_path),
                    'url': static_url_from_db_value(filename) if os.path.exists(full_path) else None
                }
            else:
                file_status[key] = {'exists': False, 'url': None}
        
        # Get recommendations
        recommendations = get_health_recommendations(soil_metrics, crop_metrics)
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'place_name': row[10],
            'datetime': row[11],
            'timestamp': row[12],
            'soil_metrics': soil_metrics,
            'crop_metrics': crop_metrics,
            'file_status': file_status,
            'recommendations': recommendations,
            'interpretation': get_health_interpretation(soil_metrics, crop_metrics)
        })
        
    except Exception as e:
        print(f"Error getting health metrics: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def get_health_interpretation(soil_metrics, crop_metrics):
    """Provide interpretation of health metrics"""
    interpretation = {
        'soil_summary': '',
        'crop_summary': '',
        'overall_health': ''
    }
    
    # Soil interpretation
    soil_score = soil_metrics.get('health_score', 0)
    if soil_score >= 80:
        interpretation['soil_summary'] = 'Excellent soil health with optimal properties for plant growth.'
    elif soil_score >= 65:
        interpretation['soil_summary'] = 'Good soil health with suitable conditions for most crops.'
    elif soil_score >= 50:
        interpretation['soil_summary'] = 'Moderate soil health. Some improvements could enhance productivity.'
    elif soil_score >= 35:
        interpretation['soil_summary'] = 'Poor soil health requiring attention and amendments.'
    else:
        interpretation['soil_summary'] = 'Very poor soil health. Significant improvement needed.'
    
    # Crop interpretation
    crop_score = crop_metrics.get('health_score', 0)
    if crop_score >= 80:
        interpretation['crop_summary'] = 'Excellent crop health with optimal growth conditions.'
    elif crop_score >= 65:
        interpretation['crop_summary'] = 'Good crop health with normal growth patterns.'
    elif crop_score >= 50:
        interpretation['crop_summary'] = 'Moderate crop health. Monitor for stress signs.'
    elif crop_score >= 35:
        interpretation['crop_summary'] = 'Poor crop health requiring intervention.'
    else:
        interpretation['crop_summary'] = 'Critical crop health. Immediate action required.'
    
    # Overall interpretation
    overall_score = (soil_score + crop_score) / 2
    if overall_score >= 75:
        interpretation['overall_health'] = 'Excellent overall health. Ideal conditions for agriculture.'
    elif overall_score >= 60:
        interpretation['overall_health'] = 'Good overall health. Sustainable agricultural conditions.'
    elif overall_score >= 45:
        interpretation['overall_health'] = 'Fair overall health. Some improvements recommended.'
    elif overall_score >= 30:
        interpretation['overall_health'] = 'Poor overall health. Significant improvements needed.'
    else:
        interpretation['overall_health'] = 'Critical overall health. Urgent action required.'
    
    return interpretation

@app.route("/get_health_history")
def get_health_history():
    """Get history of health analyses with metrics"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        with sqlite3.connect(DB_FILE) as con:
            rows = con.execute("""
                SELECT id, place_name, datetime, 
                       soil_health_score, crop_health_score,
                       ndvi_png, rgb_png, soil_health_png, crop_health_png
                FROM ndvi_history 
                WHERE soil_health_score IS NOT NULL 
                AND crop_health_score IS NOT NULL
                ORDER BY datetime DESC 
                LIMIT ?
            """, (limit,)).fetchall()
        
        history_list = []
        for row in rows:
            history_list.append({
                'id': row[0],
                'place_name': row[1],
                'datetime': row[2],
                'soil_score': row[3] if row[3] is not None else 0,
                'crop_score': row[4] if row[4] is not None else 0,
                'has_ndvi': bool(row[5]),
                'has_rgb': bool(row[6]),
                'has_soil_map': bool(row[7]),
                'has_crop_map': bool(row[8]),
                'overall_score': round(((row[3] or 0) + (row[4] or 0)) / 2, 1)
            })
        
        return jsonify({
            'success': True,
            'count': len(history_list),
            'history': history_list
        })
        
    except Exception as e:
        print(f"Error getting health history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/get_health_stats")
def get_health_stats():
    """Get statistics about health metrics"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            # Get overall stats
            stats = con.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(soil_health_score) as avg_soil,
                    AVG(crop_health_score) as avg_crop,
                    MIN(soil_health_score) as min_soil,
                    MAX(soil_health_score) as max_soil,
                    MIN(crop_health_score) as min_crop,
                    MAX(crop_health_score) as max_crop
                FROM ndvi_history 
                WHERE soil_health_score IS NOT NULL 
                AND crop_health_score IS NOT NULL
            """).fetchone()
            
            # Get distribution
            distribution = con.execute("""
                SELECT 
                    CASE 
                        WHEN soil_health_score >= 80 THEN 'Excellent (80-100)'
                        WHEN soil_health_score >= 65 THEN 'Good (65-79)'
                        WHEN soil_health_score >= 50 THEN 'Fair (50-64)'
                        WHEN soil_health_score >= 35 THEN 'Poor (35-49)'
                        ELSE 'Critical (0-34)'
                    END as category,
                    COUNT(*) as count
                FROM ndvi_history 
                WHERE soil_health_score IS NOT NULL
                GROUP BY category
                ORDER BY 
                    CASE category
                        WHEN 'Excellent (80-100)' THEN 1
                        WHEN 'Good (65-79)' THEN 2
                        WHEN 'Fair (50-64)' THEN 3
                        WHEN 'Poor (35-49)' THEN 4
                        ELSE 5
                    END
            """).fetchall()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_analyses': stats[0] if stats else 0,
                'average_soil_score': round(stats[1], 1) if stats and stats[1] else 0,
                'average_crop_score': round(stats[2], 1) if stats and stats[2] else 0,
                'soil_score_range': {
                    'min': round(stats[3], 1) if stats and stats[3] else 0,
                    'max': round(stats[4], 1) if stats and stats[4] else 0
                },
                'crop_score_range': {
                    'min': round(stats[5], 1) if stats and stats[5] else 0,
                    'max': round(stats[6], 1) if stats and stats[6] else 0
                }
            },
            'distribution': [
                {'category': row[0], 'count': row[1]} for row in distribution
            ]
        })
        
    except Exception as e:
        print(f"Error getting health stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_recommendations_html(soil_metrics, crop_metrics):
    """Generate HTML for recommendations"""
    recommendations = get_health_recommendations(soil_metrics, crop_metrics)
    
    if not recommendations:
        return '<p class="good">✅ All parameters are within optimal ranges. Continue current practices.</p>'
    
    html = ""
    for rec in recommendations:
        if "🚨" in rec or "Critical" in rec or "Urgent" in rec:
            html += f'<div class="recommendation critical">{rec}</div>'
        elif "⚠️" in rec:
            html += f'<div class="recommendation">{rec}</div>'
        else:
            html += f'<div class="recommendation good">{rec}</div>'
    
    return html

# Keep all the other existing routes from your original code
# ... [All your existing routes remain unchanged] ...


@app.route("/test_bands", methods=["POST"])
def test_bands():
    """Test endpoint to check band availability"""
    if not EE_INITIALIZED or ee is None:
        return jsonify({"error": "Earth Engine is not available on this server"}), 503

    data = request.get_json(silent=True) or {}
    polygon_coords = data.get("polygon")
    if not polygon_coords:
        return jsonify({"error": "Missing required field: polygon"}), 400

    polygon = ee.Geometry.Polygon(polygon_coords)
    
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(polygon)
        .filterDate("2024-01-01", "2024-01-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
    )
    
    if collection.size().getInfo() == 0:
        return jsonify({"error": "No images found"})
    
    image = collection.median().clip(polygon)
    
    # Check band info
    bands = image.bandNames().getInfo()
    band_info = {}
    
    for band in ['B2', 'B3', 'B4', 'B8']:  # Key bands for our indices
        if band in bands:
            try:
                stats = image.select(band).reduceRegion(
                    reducer=ee.Reducer.minMax(),
                    geometry=polygon,
                    scale=10,
                    bestEffort=True
                ).getInfo()
                band_info[band] = stats
            except:
                band_info[band] = "exists but no stats"
        else:
            band_info[band] = "missing"
    
    return jsonify({
        "bands_available": bands,
        "band_info": band_info,
        "collection_size": collection.size().getInfo()
    })

@app.route("/get_latest_geotiff")
def get_latest_geotiff():
    with sqlite3.connect(DB_FILE) as con:
        row = con.execute("""
            SELECT ndvi_tif FROM ndvi_history 
            WHERE ndvi_tif IS NOT NULL 
            ORDER BY id DESC LIMIT 1
        """).fetchone()
    
    if row and row[0]:
        return jsonify({'geotiff_path': row[0]})
    return jsonify({'geotiff_path': None})

@app.route('/download_all_images', methods=['POST'])
def download_all_images():
    """Create a ZIP file with all generated images"""
    try:
        data = request.get_json(silent=True) or {}
        image_paths = data.get('image_paths', {})
        place_name = data.get('place_name', 'analysis')
        
        # Create in-memory ZIP file
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add README file
            readme_content = f"""NDVI Analysis Results
========================
Location: {place_name}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Files included:
- NDVI.png: Normalized Difference Vegetation Index
- RGB.png: True Color Satellite Image
- SAVI.png: Soil Adjusted Vegetation Index
- GNDVI.png: Green Normalized Difference Index
- EVI.png: Enhanced Vegetation Index

Color Interpretation:
- NDVI Crop Health Scale (0.0-1.0):
  • 0.0-0.2: Severe Stress (Dark Red)
  • 0.2-0.3: High Stress (Red)
  • 0.3-0.4: Moderate Stress (Dark Orange)
  • 0.4-0.5: Fair (Gold)
  • 0.5-0.6: Good (Green Yellow)
  • 0.6-0.7: Very Good (Lime Green)
  • 0.7-0.8: Excellent (Forest Green)
  • 0.8-1.0: Optimal (Dark Green)
"""
            zf.writestr("README.txt", readme_content)
            
            # Add each image to the ZIP
            for key, path in image_paths.items():
                resolved_path = resolve_stored_path(path)
                if resolved_path and os.path.exists(resolved_path):
                    # Extract just the filename
                    filename = os.path.basename(resolved_path)
                    # Add file to ZIP
                    zf.write(resolved_path, filename)
                else:
                    print(f"Warning: Image path not found for {key}: {path}")
        
        # Go to beginning of memory file
        memory_file.seek(0)
        
        # Create filename
        safe_place_name = place_name.replace(' ', '_').replace('/', '_')
        zip_filename = f"ndvi_analysis_{safe_place_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        
    except Exception as e:
        print(f"Error creating ZIP: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route("/get_history_data")
def get_history_data():
    """API endpoint to get all history data for the history page"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            rows = con.execute("""
                SELECT id, place_name, datetime, timestamp, ndvi_png, ndvi_tif, 
                       rgb_png, savi_png, gndvi_png, evi_png
                FROM ndvi_history
                ORDER BY datetime DESC, timestamp DESC
            """).fetchall()
        
        # Convert to list of dictionaries
        history_list = []
        for row in rows:
            history_list.append({
                'id': row[0],
                'place_name': row[1],
                'datetime': row[2],
                'timestamp': row[3],
                'ndvi_png': row[4],
                'ndvi_tif': row[5],
                'rgb_png': row[6],
                'savi_png': row[7],
                'gndvi_png': row[8],
                'evi_png': row[9]
            })
        
        return jsonify({
            'success': True,
            'count': len(history_list),
            'history': history_list
        })
        
    except Exception as e:
        print(f"Error getting history data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/delete_history", methods=["POST"])
def delete_history():
    """Delete a specific history entry"""
    try:
        data = request.get_json(silent=True) or {}
        entry_id = data.get('id')
        
        if not entry_id:
            return jsonify({'success': False, 'error': 'No ID provided'}), 400
        
        # First get file paths to delete the actual files
        with sqlite3.connect(DB_FILE) as con:
            row = con.execute("""
                SELECT ndvi_png, ndvi_tif, rgb_png, savi_png, gndvi_png, evi_png
                FROM ndvi_history WHERE id = ?
            """, (entry_id,)).fetchone()
        
        # Delete the files from disk
        if row:
            files_to_delete = row
            for file_path in files_to_delete:
                resolved_path = resolve_stored_path(file_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        os.remove(resolved_path)
                        print(f"Deleted file: {resolved_path}")
                    except Exception as e:
                        print(f"Error deleting file {resolved_path}: {e}")
        
        # Delete from database
        with sqlite3.connect(DB_FILE) as con:
            con.execute("DELETE FROM ndvi_history WHERE id = ?", (entry_id,))
        
        return jsonify({'success': True, 'message': 'Entry deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/export_history_csv")
def export_history_csv():
    """Export all history as CSV file"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            rows = con.execute("""
                SELECT place_name, datetime, ndvi_png, rgb_png, savi_png, gndvi_png, evi_png, ndvi_tif
                FROM ndvi_history
                ORDER BY datetime DESC
            """).fetchall()
        
        # Create CSV content
        csv_data = "Location,Date Time,NDVI Image,RGB Image,SAVI Image,GNDVI Image,EVI Image,GeoTIFF File\n"
        
        for row in rows:
            # Escape commas in data
            escaped_row = []
            for cell in row:
                if cell:
                    escaped_row.append(f'"{cell}"' if ',' in str(cell) else str(cell))
                else:
                    escaped_row.append('')
            
            csv_data += ','.join(escaped_row) + '\n'
        
        # Create response
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=ndvi_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-Type"] = "text/csv"
        
        return response
        
    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/clear_all_history", methods=["POST"])
def clear_all_history():
    """Clear all history (admin function)"""
    try:
        # Get all file paths first
        with sqlite3.connect(DB_FILE) as con:
            rows = con.execute("""
                SELECT ndvi_png, ndvi_tif, rgb_png, savi_png, gndvi_png, evi_png
                FROM ndvi_history
            """).fetchall()
        
        # Delete all files
        file_count = 0
        for row in rows:
            for file_path in row:
                resolved_path = resolve_stored_path(file_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        os.remove(resolved_path)
                        file_count += 1
                    except Exception as e:
                        print(f"Error deleting file {resolved_path}: {e}")
        
        # Clear database
        with sqlite3.connect(DB_FILE) as con:
            con.execute("DELETE FROM ndvi_history")
        
        return jsonify({
            'success': True, 
            'message': f'All history cleared. Deleted {file_count} files.',
            'files_deleted': file_count
        })
        
    except Exception as e:
        print(f"Error clearing all history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/get_recent_analyses")
def get_recent_analyses():
    """Get recent analyses for the home page"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            rows = con.execute("""
                SELECT place_name, datetime, timestamp
                FROM ndvi_history
                ORDER BY datetime DESC, timestamp DESC
                LIMIT 5
            """).fetchall()
        
        history_list = []
        for row in rows:
            history_list.append({
                'place_name': row[0],
                'datetime': row[1],
                'timestamp': row[2]
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
        
    except Exception as e:
        print(f"Error getting recent analyses: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/get_color_palettes")
def get_color_palettes():
    """Get the color palette information for frontend display"""
    return jsonify(COLOR_PALETTES)

# Add after your existing routes, before the if __name__ == "__main__":

@app.route("/get_statistics")
def get_statistics():
    """Get statistics about the analysis history"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            # Get total count
            total = con.execute("SELECT COUNT(*) FROM ndvi_history").fetchone()[0]
            
            # Get today's count
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = con.execute(
                "SELECT COUNT(*) FROM ndvi_history WHERE datetime LIKE ?", 
                (f"{today}%",)
            ).fetchone()[0]
            
            # Get unique locations
            locations = con.execute(
                "SELECT COUNT(DISTINCT place_name) FROM ndvi_history"
            ).fetchone()[0]
            
            # Get most recent analysis
            recent = con.execute(
                "SELECT place_name, datetime FROM ndvi_history ORDER BY datetime DESC LIMIT 1"
            ).fetchone()
            
        return jsonify({
            'success': True,
            'statistics': {
                'total_analyses': total,
                'today_analyses': today_count,
                'unique_locations': locations,
                'most_recent': {
                    'place_name': recent[0] if recent else None,
                    'datetime': recent[1] if recent else None
                }
            }
        })
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/get_analysis_summary/<int:analysis_id>")
def get_analysis_summary(analysis_id):
    """Get detailed summary of a specific analysis"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            row = con.execute("""
                SELECT id, place_name, datetime, timestamp, ndvi_png, ndvi_tif, 
                       rgb_png, savi_png, gndvi_png, evi_png, polygon
                FROM ndvi_history WHERE id = ?
            """, (analysis_id,)).fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Analysis not found'}), 404
        
        # Parse polygon coordinates
        polygon_coords = []
        if row[10]:  # polygon field
            try:
                polygon_coords = parse_polygon_coords(row[10])
            except:
                polygon_coords = []
        
        # Check if files exist
        file_status = {}
        for i, key in enumerate(['ndvi_png', 'rgb_png', 'savi_png', 'gndvi_png', 'evi_png']):
            file_path = row[4 + i]  # ndvi_png is index 4
            if file_path:
                full_path = resolve_stored_path(file_path)
                file_status[key] = {
                    'exists': os.path.exists(full_path),
                    'size': os.path.getsize(full_path) if os.path.exists(full_path) else 0
                }
            else:
                file_status[key] = {'exists': False, 'size': 0}
        
        analysis_data = {
            'id': row[0],
            'place_name': row[1],
            'datetime': row[2],
            'timestamp': row[3],
            'file_status': file_status,
            'polygon_coordinates': polygon_coords,
            'has_geotiff': bool(row[5]) and os.path.exists(resolve_stored_path(row[5])) if row[5] else False
        }
        
        return jsonify({
            'success': True,
            'analysis': analysis_data
        })
        
    except Exception as e:
        print(f"Error getting analysis summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/batch_delete", methods=["POST"])
def batch_delete():
    """Delete multiple analyses at once"""
    try:
        data = request.get_json(silent=True) or {}
        analysis_ids = data.get('analysis_ids', [])
        
        if not analysis_ids:
            return jsonify({'success': False, 'error': 'No analysis IDs provided'}), 400
        
        deleted_count = 0
        file_deleted_count = 0
        
        for analysis_id in analysis_ids:
            # Get file paths for this analysis
            with sqlite3.connect(DB_FILE) as con:
                row = con.execute("""
                    SELECT ndvi_png, ndvi_tif, rgb_png, savi_png, gndvi_png, evi_png
                    FROM ndvi_history WHERE id = ?
                """, (analysis_id,)).fetchone()
            
            # Delete files from disk
            if row:
                files_to_delete = row
                for file_path in files_to_delete:
                    resolved_path = resolve_stored_path(file_path)
                    if resolved_path and os.path.exists(resolved_path):
                        try:
                            os.remove(resolved_path)
                            file_deleted_count += 1
                        except Exception as e:
                            print(f"Error deleting file {resolved_path}: {e}")
            
            # Delete from database
            with sqlite3.connect(DB_FILE) as con:
                con.execute("DELETE FROM ndvi_history WHERE id = ?", (analysis_id,))
            
            deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} analyses and {file_deleted_count} files',
            'analyses_deleted': deleted_count,
            'files_deleted': file_deleted_count
        })
        
    except Exception as e:
        print(f"Error in batch delete: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/health_check")
def health_check():
    """Health check endpoint to verify system status"""
    try:
        status = {
            'app': 'running',
            'database': 'connected' if os.path.exists(DB_FILE) else 'not_found',
            'static_dir': 'exists' if os.path.exists(STATIC_DIR) else 'not_found',
            'earth_engine': 'initialized' if EE_INITIALIZED else 'not_initialized',
            'internet': check_internet(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if we can write to static directory
        try:
            test_file = os.path.join(STATIC_DIR, 'test_write.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            status['write_permission'] = 'ok'
        except Exception as e:
            status['write_permission'] = f'error: {str(e)}'
        
        return jsonify({'success': True, 'status': status})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/reprocess_analysis/<int:analysis_id>", methods=["POST"])
def reprocess_analysis(analysis_id):
    """Reprocess an existing analysis (regenerate images)"""
    try:
        # Get the polygon from the existing analysis
        with sqlite3.connect(DB_FILE) as con:
            row = con.execute("""
                SELECT polygon, place_name FROM ndvi_history WHERE id = ?
            """, (analysis_id,)).fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Analysis not found'}), 404
        
        polygon_coords_str, place_name = row
        
        try:
            polygon_coords = parse_polygon_coords(polygon_coords_str)
        except:
            return jsonify({'success': False, 'error': 'Invalid polygon data'}), 400
        
        if not polygon_coords:
            return jsonify({'success': False, 'error': 'No polygon data available'}), 400
        
        # Call the get_ndvi function with the polygon
        # This is a simplified approach - in production, you might want to refactor
        response_data = get_ndvi_internal(polygon_coords, place_name)
        
        if 'error' in response_data:
            return jsonify({'success': False, 'error': response_data['error']}), 400
        
        # Update the existing database entry
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        display_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Delete old files
        with sqlite3.connect(DB_FILE) as con:
            old_files = con.execute("""
                SELECT ndvi_png, ndvi_tif, rgb_png, savi_png, gndvi_png, evi_png
                FROM ndvi_history WHERE id = ?
            """, (analysis_id,)).fetchone()
            
            # Delete old files
            if old_files:
                for file_path in old_files:
                    resolved_path = resolve_stored_path(file_path)
                    if resolved_path and os.path.exists(resolved_path):
                        try:
                            os.remove(resolved_path)
                        except:
                            pass
        
        # Update with new file names
        new_filenames = {
            'ndvi_png': f"{place_name}_{timestamp}_NDVI.png" if response_data.get('image') else None,
            'rgb_png': f"{place_name}_{timestamp}_RGB.png" if response_data.get('rgb') else None,
            'savi_png': f"{place_name}_{timestamp}_SAVI.png" if response_data.get('savi') else None,
            'gndvi_png': f"{place_name}_{timestamp}_GNDVI.png" if response_data.get('gndvi') else None,
            'evi_png': f"{place_name}_{timestamp}_EVI.png" if response_data.get('evi') else None,
        }
        
        with sqlite3.connect(DB_FILE) as con:
            con.execute("""
                UPDATE ndvi_history 
                SET datetime = ?, timestamp = ?,
                    ndvi_png = ?, rgb_png = ?, savi_png = ?, gndvi_png = ?, evi_png = ?
                WHERE id = ?
            """, (
                display_date, timestamp,
                new_filenames['ndvi_png'],
                new_filenames['rgb_png'],
                new_filenames['savi_png'],
                new_filenames['gndvi_png'],
                new_filenames['evi_png'],
                analysis_id
            ))
        
        return jsonify({
            'success': True,
            'message': 'Analysis reprocessed successfully',
            'analysis_id': analysis_id,
            'new_timestamp': timestamp
        })
        
    except Exception as e:
        print(f"Error reprocessing analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_ndvi_internal(polygon_coords, place_name=None):
    """Internal version of get_ndvi for reprocessing"""
    # This is a simplified version - you would need to refactor your actual get_ndvi function
    # to be callable internally or reuse the logic
    return {"error": "Not implemented in this example"}

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Add a middleware for CORS if needed
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Add a cleanup function to remove old files (optional, run as cron job)
def cleanup_old_files(days_old=30):
    """Remove files older than specified days"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        with sqlite3.connect(DB_FILE) as con:
            # Get files older than cutoff
            old_records = con.execute("""
                SELECT id, ndvi_png, ndvi_tif, rgb_png, savi_png, gndvi_png, evi_png
                FROM ndvi_history 
                WHERE datetime < ?
            """, (cutoff_str,)).fetchall()
        
        deleted_files = 0
        for record in old_records:
            files = record[1:]  # Skip id
            for file_path in files:
                resolved_path = resolve_stored_path(file_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        os.remove(resolved_path)
                        deleted_files += 1
                    except:
                        pass
        
        # Delete from database
        with sqlite3.connect(DB_FILE) as con:
            con.execute("DELETE FROM ndvi_history WHERE datetime < ?", (cutoff_str,))
        
        print(f"Cleanup: Deleted {deleted_files} files and {len(old_records)} database entries older than {days_old} days")
        return deleted_files
        
    except Exception as e:
        print(f"Error in cleanup: {e}")
        return 0
    
@app.route("/api/statistics/dashboard")
def api_statistics_dashboard():
    """Get comprehensive dashboard statistics"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            # Basic counts
            total_analyses = con.execute("SELECT COUNT(*) FROM ndvi_history").fetchone()[0]
            
            # Today's analyses
            today = datetime.now().strftime("%Y-%m-%d")
            today_analyses = con.execute(
                "SELECT COUNT(*) FROM ndvi_history WHERE datetime LIKE ?", 
                (f"{today}%",)
            ).fetchone()[0]
            
            # This week's analyses
            week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            week_analyses = con.execute(
                "SELECT COUNT(*) FROM ndvi_history WHERE datetime >= ?", 
                (week_start,)
            ).fetchone()[0]
            
            # This month's analyses
            month_start = datetime.now().strftime("%Y-%m-01")
            month_analyses = con.execute(
                "SELECT COUNT(*) FROM ndvi_history WHERE datetime >= ?", 
                (month_start,)
            ).fetchone()[0]
            
            # Unique locations
            unique_locations = con.execute(
                "SELECT COUNT(DISTINCT place_name) FROM ndvi_history"
            ).fetchone()[0]
            
            # File storage stats
            file_stats = con.execute("""
                SELECT 
                    SUM(CASE WHEN ndvi_png IS NOT NULL THEN 1 ELSE 0 END) as ndvi_count,
                    SUM(CASE WHEN rgb_png IS NOT NULL THEN 1 ELSE 0 END) as rgb_count,
                    SUM(CASE WHEN savi_png IS NOT NULL THEN 1 ELSE 0 END) as savi_count,
                    SUM(CASE WHEN gndvi_png IS NOT NULL THEN 1 ELSE 0 END) as gndvi_count,
                    SUM(CASE WHEN evi_png IS NOT NULL THEN 1 ELSE 0 END) as evi_count,
                    SUM(CASE WHEN ndvi_tif IS NOT NULL THEN 1 ELSE 0 END) as tif_count
                FROM ndvi_history
            """).fetchone()
            
            # Most active locations
            top_locations = con.execute("""
                SELECT place_name, COUNT(*) as count 
                FROM ndvi_history 
                WHERE place_name IS NOT NULL AND place_name != 'Unknown_Area'
                GROUP BY place_name 
                ORDER BY count DESC 
                LIMIT 5
            """).fetchall()
            
            # Daily trend (last 7 days)
            daily_trend = con.execute("""
                SELECT DATE(datetime) as date, COUNT(*) as count
                FROM ndvi_history 
                WHERE datetime >= date('now', '-7 days')
                GROUP BY DATE(datetime)
                ORDER BY date DESC
            """).fetchall()
            
            # System health info
            system_info = {
                'database_size': os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0,
                'static_dir_size': get_dir_size(STATIC_DIR),
                'total_files': count_files_in_dir(STATIC_DIR),
                'earth_engine_status': EE_INITIALIZED,
                'internet_status': check_internet(),
                'server_time': datetime.now().isoformat(),
                'uptime': get_uptime()
            }
            
        return jsonify({
            'success': True,
            'statistics': {
                'total_analyses': total_analyses,
                'today_analyses': today_analyses,
                'week_analyses': week_analyses,
                'month_analyses': month_analyses,
                'unique_locations': unique_locations,
                'file_stats': {
                    'ndvi_images': file_stats[0] if file_stats else 0,
                    'rgb_images': file_stats[1] if file_stats else 0,
                    'savi_images': file_stats[2] if file_stats else 0,
                    'gndvi_images': file_stats[3] if file_stats else 0,
                    'evi_images': file_stats[4] if file_stats else 0,
                    'geotiff_files': file_stats[5] if file_stats else 0,
                    'total_images': sum([x for x in file_stats[:5] if x]) if file_stats else 0
                },
                'top_locations': [
                    {'name': loc[0], 'count': loc[1]} for loc in top_locations
                ],
                'daily_trend': [
                    {'date': trend[0], 'count': trend[1]} for trend in daily_trend
                ],
                'system_info': system_info
            }
        })
        
    except Exception as e:
        print(f"Error getting dashboard statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_dir_size(path):
    """Calculate total size of directory"""
    total = 0
    if os.path.exists(path):
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def count_files_in_dir(path):
    """Count total files in directory"""
    count = 0
    if os.path.exists(path):
        for entry in os.scandir(path):
            if entry.is_file():
                count += 1
            elif entry.is_dir():
                count += count_files_in_dir(entry.path)
    return count

# Global variable to track server start time
SERVER_START_TIME = datetime.now()

def get_uptime():
    """Calculate server uptime"""
    uptime = datetime.now() - SERVER_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

@app.route("/api/statistics/analyses_by_date")
def api_analyses_by_date():
    """Get analyses grouped by date for charts"""
    try:
        period = request.args.get('period', 'week')  # week, month, year
        
        with sqlite3.connect(DB_FILE) as con:
            if period == 'week':
                query = """
                    SELECT DATE(datetime) as date, COUNT(*) as count
                    FROM ndvi_history 
                    WHERE datetime >= date('now', '-7 days')
                    GROUP BY DATE(datetime)
                    ORDER BY date
                """
            elif period == 'month':
                query = """
                    SELECT DATE(datetime, 'start of month') as month, COUNT(*) as count
                    FROM ndvi_history 
                    WHERE datetime >= date('now', '-365 days')
                    GROUP BY DATE(datetime, 'start of month')
                    ORDER BY month
                    LIMIT 12
                """
            else:  # year
                query = """
                    SELECT strftime('%Y', datetime) as year, COUNT(*) as count
                    FROM ndvi_history 
                    GROUP BY strftime('%Y', datetime)
                    ORDER BY year
                """
            
            results = con.execute(query).fetchall()
            
        data = []
        if period == 'week':
            # Fill in missing days
            for i in range(7):
                date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
                count = next((r[1] for r in results if r[0] == date), 0)
                data.append({'date': date, 'count': count})
        else:
            data = [{'period': r[0], 'count': r[1]} for r in results]
        
        return jsonify({
            'success': True,
            'period': period,
            'data': data
        })
        
    except Exception as e:
        print(f"Error getting analyses by date: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/statistics/location_distribution")
def api_location_distribution():
    """Get location distribution data"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            results = con.execute("""
                SELECT place_name, COUNT(*) as count 
                FROM ndvi_history 
                WHERE place_name IS NOT NULL AND place_name != 'Unknown_Area'
                GROUP BY place_name 
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()
            
            others_count = con.execute("""
                SELECT COUNT(*) FROM ndvi_history 
                WHERE place_name IS NULL OR place_name = 'Unknown_Area' 
                OR place_name NOT IN (
                    SELECT place_name FROM ndvi_history 
                    GROUP BY place_name 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 10
                )
            """).fetchone()[0]
        
        data = [{'name': r[0], 'count': r[1]} for r in results]
        if others_count > 0:
            data.append({'name': 'Other/Unknown', 'count': others_count})
        
        return jsonify({
            'success': True,
            'data': data,
            'total_locations': len(results) + (1 if others_count > 0 else 0)
        })
        
    except Exception as e:
        print(f"Error getting location distribution: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/statistics/system_health")
def api_system_health():
    """Get detailed system health information"""
    try:
        health_info = {
            'application': {
                'status': 'running',
                'version': '1.0.0',
                'start_time': SERVER_START_TIME.isoformat(),
                'uptime': get_uptime(),
                'python_version': sys.version
            },
            'database': {
                'status': 'connected' if os.path.exists(DB_FILE) else 'not_found',
                'size_bytes': os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0,
                'size_human': sizeof_fmt(os.path.getsize(DB_FILE)) if os.path.exists(DB_FILE) else '0 B',
                'record_count': get_record_count()
            },
            'storage': {
                'static_dir': STATIC_DIR,
                'exists': os.path.exists(STATIC_DIR),
                'size_bytes': get_dir_size(STATIC_DIR),
                'size_human': sizeof_fmt(get_dir_size(STATIC_DIR)),
                'file_count': count_files_in_dir(STATIC_DIR),
                'writable': check_writable(STATIC_DIR)
            },
            'services': {
                'earth_engine': {
                    'status': 'initialized' if EE_INITIALIZED else 'not_initialized',
                    'available': check_internet()
                },
                'geolocation': {
                    'status': 'available',
                    'service': 'Nominatim'
                },
                'internet': {
                    'status': 'connected' if check_internet() else 'disconnected'
                }
            },
            'performance': {
                'last_hour_requests': 0,  # You would track this with a counter
                'average_response_time': 'N/A',
                'memory_usage': get_memory_usage(),
                'cpu_usage': get_cpu_usage()
            }
        }
        
        return jsonify({
            'success': True,
            'health_check': health_info,
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy' if all_services_healthy(health_info) else 'degraded'
        })
        
    except Exception as e:
        print(f"Error getting system health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
def sizeof_fmt(num, suffix="B"):
    """Convert bytes to human readable format"""
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def get_record_count():
    """Get total records in database"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            return con.execute("SELECT COUNT(*) FROM ndvi_history").fetchone()[0]
    except:
        return 0

def check_writable(path):
    """Check if directory is writable"""
    try:
        test_file = os.path.join(path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except:
        return False

def get_memory_usage():
    """Get memory usage (platform specific)"""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return "N/A (install psutil)"

def get_cpu_usage():
    """Get CPU usage (platform specific)"""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        return "N/A (install psutil)"

def all_services_healthy(health_info):
    """Check if all services are healthy"""
    return (
        health_info['database']['status'] == 'connected' and
        health_info['storage']['exists'] and
        health_info['storage']['writable'] and
        health_info['services']['earth_engine']['available']
    )

# Add after all routes
@app.route("/debug_db_schema")
def debug_db_schema():
    """Debug endpoint to check database schema"""
    try:
        with sqlite3.connect(DB_FILE) as con:
            cursor = con.execute("PRAGMA table_info(ndvi_history)")
            columns = cursor.fetchall()
            
            # Check a few records
            sample = con.execute("SELECT * FROM ndvi_history ORDER BY id DESC LIMIT 1").fetchone()
            
        return jsonify({
            'success': True,
            'columns': columns,
            'sample_record': sample,
            'column_count': len(columns)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# -------------------------
# SOIL ADVISOR CONFIG
# -------------------------
THRESHOLDS = {
    "N": {"good": 80, "medium": 40},
    "P": {"good": 30, "medium": 15},
    "K": {"good": 150, "medium": 80},
}

BASE_DOSES = {
    "N": 60,
    "P": 30,
    "K": 80,
}

CROP_MULTIPLIERS = {
    "rice": 1.0,
    "wheat": 1.0,
    "maize": 1.15,
    "groundnut": 0.9,
    "soybean": 0.8,
    "cotton": 1.05,
    "sugarcane": 1.2,
    "sunflower": 0.95,
    "pulses": 0.7,
}

SAFETY_CAPS = {
    "N": {"max_per_application": 200, "max_per_year": 250},
    "P": {"max_per_application": 150, "max_per_year": 200},
    "K": {"max_per_application": 250, "max_per_year": 300},
}

CROP_DB = {
    "rice": {"N": (80, 160), "P": (30, 60), "K": (100, 300), "pH": (5.5, 6.5)},
    "wheat": {"N": (80, 140), "P": (30, 60), "K": (80, 200), "pH": (6.0, 7.5)},
    "maize": {"N": (80, 200), "P": (30, 70), "K": (100, 250), "pH": (5.5, 7.0)},
    "groundnut": {"N": (40, 80), "P": (20, 50), "K": (60, 150), "pH": (5.0, 6.5)},
    "soybean": {"N": (20, 60), "P": (20, 50), "K": (50, 150), "pH": (5.5, 7.0)},
    "cotton": {"N": (60, 120), "P": (30, 60), "K": (80, 200), "pH": (5.5, 7.5)},
    "sugarcane": {"N": (100, 250), "P": (30, 80), "K": (200, 400), "pH": (5.5, 7.0)},
    "sunflower": {"N": (40, 100), "P": (30, 60), "K": (80, 160), "pH": (6.0, 7.5)},
    "pulses": {"N": (10, 40), "P": (15, 40), "K": (50, 120), "pH": (6.0, 7.5)},
}

BASE_DIR = APP_ROOT
MODEL_PATH = os.path.join(BASE_DIR, "rf_soil_model.pkl")
MODEL = None

if joblib is None:
    print("⚠️ joblib is not installed - soil model features disabled")
elif os.path.exists(MODEL_PATH):
    try:
        MODEL = joblib.load(MODEL_PATH)
        print(f"✓ Loaded soil model from {MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to load soil model at {MODEL_PATH}: {e}")
else:
    print(f"⚠️ Soil model not found at {MODEL_PATH}")

def ensure_soil_runtime():
    """Lazy-load soil runtime dependencies if they were missing at startup."""
    global pd, joblib, MODEL

    if pd is None:
        try:
            import pandas as _pd
            pd = _pd
        except ImportError:
            pass

    if joblib is None:
        try:
            import joblib as _joblib
            joblib = _joblib
        except ImportError:
            pass

    if MODEL is None and joblib is not None and os.path.exists(MODEL_PATH):
        try:
            MODEL = joblib.load(MODEL_PATH)
            print(f"✓ Loaded soil model from {MODEL_PATH}")
        except Exception as e:
            print(f"⚠️ Failed to load soil model at {MODEL_PATH}: {e}")


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
    span = max(1.0, preferred_max - preferred_min)
    return min(3.0, diff / span)


def recommend_crops_for_soil(row: dict, crop_db: dict = None, top_k: int = 3):
    crop_db = crop_db or CROP_DB
    soil_N = float(row.get("N", float("nan")))
    soil_P = float(row.get("P", float("nan")))
    soil_K = float(row.get("K", float("nan")))
    soil_pH = float(row.get("pH", float("nan")))

    results = []
    for crop, req in crop_db.items():
        dN = _range_distance(soil_N, req["N"][0], req["N"][1])
        dP = _range_distance(soil_P, req["P"][0], req["P"][1])
        dK = _range_distance(soil_K, req["K"][0], req["K"][1])
        dpH = _range_distance(soil_pH, req["pH"][0], req["pH"][1])

        score = (0.35 * dN) + (0.20 * dK) + (0.15 * dP) + (0.15 * dpH)
        reasons = []
        if dN > 0:
            reasons.append(f"N outside preferred ({req['N'][0]}-{req['N'][1]})")
        if dP > 0:
            reasons.append(f"P outside preferred ({req['P'][0]}-{req['P'][1]})")
        if dK > 0:
            reasons.append(f"K outside preferred ({req['K'][0]}-{req['K'][1]})")
        if dpH > 0:
            reasons.append(f"pH outside preferred ({req['pH'][0]}-{req['pH'][1]})")

        results.append(
            {
                "crop": crop,
                "score": float(score),
                "suitability_pct": max(0.0, round(100 * (1 - min(score / 3.0, 1.0)), 1)),
                "reasons": reasons,
            }
        )

    results = sorted(results, key=lambda x: x["score"])
    return results[:top_k]


def simple_recommendation(row: dict, proba=None, crop_multiplier: float = 1.0):
    recs = []
    tgt_N = THRESHOLDS["N"]["good"]
    tgt_P = THRESHOLDS["P"]["good"]
    tgt_K = THRESHOLDS["K"]["good"]

    if row.get("N", 0) < tgt_N:
        deficit_percent = max(0.0, (tgt_N - row["N"]) / tgt_N)
        raw_dose = BASE_DOSES["N"] * (1 + deficit_percent * 1.5)
        dose = min(SAFETY_CAPS["N"]["max_per_application"], int(round(raw_dose * crop_multiplier)))
        recs.append({"nutrient": "N", "fertilizer": "Urea", "dose_kg_per_ha": dose})

    if row.get("P", 0) < tgt_P:
        deficit_percent = max(0.0, (tgt_P - row["P"]) / tgt_P)
        raw_dose = BASE_DOSES["P"] * (1 + deficit_percent * 1.2)
        dose = min(SAFETY_CAPS["P"]["max_per_application"], int(round(raw_dose * crop_multiplier)))
        recs.append({"nutrient": "P", "fertilizer": "DAP/SSP", "dose_kg_per_ha": dose})

    if row.get("K", 0) < tgt_K:
        deficit_percent = max(0.0, (tgt_K - row["K"]) / tgt_K)
        raw_dose = BASE_DOSES["K"] * (1 + deficit_percent * 1.3)
        dose = min(SAFETY_CAPS["K"]["max_per_application"], int(round(raw_dose * crop_multiplier)))
        recs.append({"nutrient": "K", "fertilizer": "MOP", "dose_kg_per_ha": dose})

    confidence = "Unknown"
    if proba:
        tp = max(proba)
        if tp >= 0.8:
            confidence = "High"
        elif tp >= 0.6:
            confidence = "Medium"
        else:
            confidence = "Low"

    return recs, confidence


@app.route("/soil/predict", methods=["POST"])
def soil_predict():
    data = request.get_json(silent=True) or {}
    required = ["N", "P", "K", "pH"]
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        n_val = float(data["N"])
        p_val = float(data["P"])
        k_val = float(data["K"])
        ph_val = float(data["pH"])
    except (TypeError, ValueError):
        return jsonify({"error": "N, P, K and pH must be numeric values"}), 400

    ensure_soil_runtime()

    if pd is None:
        return jsonify({"error": f"pandas is not installed for interpreter: {sys.executable}"}), 500

    if MODEL is None:
        return jsonify({"error": f"Soil model not loaded on server (expected: {MODEL_PATH})"}), 500

    x_row = pd.DataFrame(
        [
            {
                "N": n_val,
                "P": p_val,
                "K": k_val,
                "pH": ph_val,
                "N_P_ratio": n_val / (p_val + 1e-6),
                "N_K_ratio": n_val / (k_val + 1e-6),
                "sum_NPK": n_val + p_val + k_val,
            }
        ]
    )

    try:
        pred = MODEL.predict(x_row)[0]
        proba = MODEL.predict_proba(x_row)[0].tolist()
    except Exception as e:
        return jsonify({"error": "Model inference failed", "details": str(e)}), 500

    crop_input = {"N": n_val, "P": p_val, "K": k_val, "pH": ph_val}
    crop_recs = recommend_crops_for_soil(crop_input, CROP_DB, top_k=3)
    top_crop = crop_recs[0]["crop"] if crop_recs else None
    crop_mult = CROP_MULTIPLIERS.get(top_crop, 1.0)
    fert_recs, fert_conf = simple_recommendation(crop_input, proba=proba, crop_multiplier=crop_mult)

    return jsonify(
        {
            "predicted_label": str(pred),
            "predicted_prob": proba,
            "fertilizer_recs": fert_recs,
            "fertilizer_confidence": fert_conf,
            "crop_recs": crop_recs,
        }
    )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🌱 NDVI Analysis System with Health Metrics")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Database: {DB_FILE}")
    print(f"Static directory: {STATIC_DIR}")
    print(f"Earth Engine initialized: {EE_INITIALIZED}")
    print(f"Internet connection: {check_internet()}")
    print(f"Pandas available: {pd is not None}")
    print(f"Joblib available: {joblib is not None}")
    print(f"Soil model loaded: {MODEL is not None}")
    print("=" * 60)

    try:
        with sqlite3.connect(DB_FILE) as con:
            cursor = con.execute("PRAGMA table_info(ndvi_history)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Database columns ({len(columns)}): {', '.join(columns)}")
    except Exception as e:
        print(f"Database check error: {e}")

    print("Server starting on http://0.0.0.0:5001")
    print("=" * 60 + "\n")
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5001)
