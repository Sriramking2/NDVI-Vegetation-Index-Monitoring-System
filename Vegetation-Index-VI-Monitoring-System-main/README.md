# A Vegetation Index (VI) Monitoring System

A Flask-based web application for monitoring crop health and vegetation indices using Sentinel-2 satellite imagery from Google Earth Engine. This system provides agricultural professionals with real-time satellite-based crop health assessments and detailed soil quality analysis.

## Overview

The  Crop Health Monitoring System leverages advanced remote sensing technology to deliver accurate, actionable insights for precision agriculture. By analyzing multispectral satellite imagery from the Copernicus Sentinel-2 mission, the system calculates multiple vegetation indices and derives comprehensive health metrics for crops and soil.

### Key Capabilities
- Real-time analysis of crop and soil health
- Multiple vegetation indices for comprehensive assessment
- Historical data tracking and trend analysis
- Interactive visualization with custom area selection
- Export capabilities for GIS integration and reporting

## Features in Detail

### 🌾 Vegetation Indices Calculation

The system calculates four complementary vegetation indices, each providing unique insights:

#### NDVI (Normalized Difference Vegetation Index)
- **Formula**: (NIR - RED) / (NIR + RED)
- **Band Usage**: B08 (NIR), B04 (Red)
- **Value Range**: -1 to 1
- **Interpretation**:
  - < 0.2: Non-vegetated areas (water, urban, bare soil)
  - 0.2-0.4: Low vegetation density
  - 0.4-0.6: Moderate vegetation
  - 0.6-0.8: High vegetation (healthy crops)
  - > 0.8: Very dense vegetation (forests, wetlands)
- **Use Case**: Primary indicator of vegetation health and density

#### SAVI (Soil-Adjusted Vegetation Index)
- **Formula**: 1.5 * (NIR - RED) / (NIR + RED + 0.5)
- **Band Usage**: B08 (NIR), B04 (Red)
- **Advantage**: Reduces soil background noise, better for arid/semi-arid regions
- **Use Case**: More accurate NDVI alternative in areas with exposed soil

#### GNDVI (Green Normalized Difference Vegetation Index)
- **Formula**: (NIR - GREEN) / (NIR + GREEN)
- **Band Usage**: B08 (NIR), B03 (Green)
- **Sensitivity**: Highly sensitive to chlorophyll concentration
- **Use Case**: Early detection of nutrient deficiencies and crop stress

#### EVI (Enhanced Vegetation Index)
- **Formula**: 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
- **Band Usage**: B08 (NIR), B04 (Red), B02 (Blue)
- **Advantage**: Better in dense vegetation, accounts for atmospheric effects
- **Use Case**: Crop yield prediction and advanced vegetation monitoring

### 📊 Health Analysis System

#### Soil Health Assessment
Comprehensive soil quality evaluation based on spectral analysis:
- **Soil Health Score** (0-100): Overall soil quality metric
- **Moisture Index**: Relative soil water content estimation
  - Calculated from NIR and SWIR bands
  - Indicates irrigation needs and drought stress
- **Organic Matter Score**: Estimated organic carbon content
  - Based on spectral reflectance patterns
  - Indicates soil fertility and structure
- **Texture Score**: Assessment of soil composition
  - Influences water retention and nutrient availability
- **pH Level**: Estimated soil acidity/alkalinity
  - Critical for nutrient availability to crops

#### Crop Health Evaluation
Detailed crop vitality and productivity assessment:
- **Crop Health Score** (0-100): Composite health indicator
- **Vigor Index**: Overall plant growth rate and biomass
- **Stress Level** (0-100): Detection of water, nutrient, or disease stress
  - >70: High stress requiring immediate intervention
  - 30-70: Moderate stress with management options
  - <30: Low stress, good health
- **Yield Potential** (%): Estimated productivity relative to optimal conditions
- **Chlorophyll Content**: Leaf pigment concentration proxy
  - Essential for photosynthesis and yield

#### Real-time Visualizations
- Heatmaps showing spatial distribution of health metrics
- False-color composites for pattern recognition
- Historical trend charts and graphs
- Side-by-side comparisons of different indices

### 📈 Data Management Features

#### History Tracking
- **Persistent Storage**: SQLite database stores all analyses
- **Timestamp Logging**: Records analysis date, time, and Sentinel-2 acquisition date
- **Metadata Preservation**: Stores polygon boundaries, location names, and coordinates
- **Version Control**: Track changes in crop health over growing season

#### Statistical Reports
- **Trend Analysis**: Identify patterns in crop health over time
- **Comparative Analysis**: Compare multiple locations or time periods
- **Summary Statistics**: Mean, median, standard deviation of health metrics
- **Anomaly Detection**: Identify unusual values warranting further investigation

#### Export Options
- **PNG Exports**: Publication-quality visualizations for reports
- **GeoTIFF Export**: Geospatially referenced raster data for GIS analysis
- **CSV Data**: Raw metric values for custom analysis
- **Zip Archives**: Batch download multiple results

#### Data Processing
- **Cloud-free Image Selection**: Automatic selection of least cloudy Sentinel-2 scenes
- **Temporal Filtering**: Configurable date ranges for analysis
- **Spatial Subsetting**: Focus analysis on specific field boundaries
- **Batch Processing**: Analyze multiple locations in single request

### 🗺️ Interactive Mapping

#### Leaflet.js Integration
- **Polygon Drawing Tools**: Create, edit, and delete area boundaries
- **Base Maps**: Multiple map styles (OpenStreetMap, satellite, terrain)
- **Layer Management**: Toggle between different visualization layers
- **Zoom and Pan**: Responsive map navigation

#### Geolocation Features
- **Address Search**: Location lookup using Nominatim geocoding
- **Reverse Geocoding**: Convert coordinates to place names
- **Coordinate Display**: Real-time latitude/longitude feedback
- **Map Markers**: Visualize analysis locations

#### Interactive Features
- **Hover Information**: Preview metrics on layer hover
- **Click Analysis**: Analyze specific areas with single click
- **Custom Styling**: Color-coded health indicators
- **Responsive Design**: Works on desktop and tablet devices

## Requirements

See [requirements.txt](requirements.txt) for Python dependencies.

### System Requirements
- Python 3.8+
- Internet connection (for Earth Engine API access)
- Google Earth Engine account with authenticated credentials
- Minimum 4GB RAM recommended for processing
- Modern web browser with JavaScript enabled

### Python Dependencies
- **Flask**: Web framework for routing and templating
- **earthengine-api**: Google Earth Engine Python client library
- **geopy**: Geocoding and geolocation services
- **requests**: HTTP library for API calls
- **Werkzeug**: WSGI utilities and security middleware

## Installation

### Prerequisites
1. Ensure Python 3.8+ is installed on your system
2. Create a Google account and register for Google Earth Engine at https://earthengine.google.com/
3. Get approved for Earth Engine access (usually takes a few hours)

### Step-by-Step Setup

1. **Clone or download the project**
   ```bash
   https://github.com/Kaviarasuzedx/Vegetation-Index-VI-Monitoring-System
   ```

2. **Create a Python virtual environment** (Recommended)
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - **Windows (PowerShell)**:
     ```powershell
     venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Authenticate with Google Earth Engine**
   ```bash
   python -c "import ee; ee.Authenticate()"
   ```
   This command will:
   - Open your default web browser
   - Redirect you to Google's authentication page
   - Ask for permission to access Earth Engine
   - Display an authentication code to copy
   - Paste the code back in the terminal
   - Store credentials locally for future use

6. **Verify Earth Engine authentication**
   ```bash
   python -c "import ee; ee.Initialize(project='ndvi-project-XXXXXX'); print('✓ Earth Engine ready')"
   ```

7. **Run the Flask application**
   ```bash
   python app.py
   ```

8. **Access the web interface**
   - Open your web browser and navigate to: `http://localhost:5000`
   - The application will display a menu with available pages

### Configuration

The main configuration is in `app.py`:
- **Earth Engine Project**: `ndvi-project-XXXXX` (update with your project ID)
- **Database File**: `ndvi.db` (created automatically)
- **Static Assets Directory**: `static/ndvi`
- **Flask Debug Mode**: Can be enabled for development

To change the Earth Engine project ID:
1. Edit `app.py`
2. Find the line: `ee.Initialize(project='ndvi-project-482615')`
3. Replace with your project ID from Google Cloud Console

## Project Structure

```
project_correct/
├── app.py                      # Main Flask application (2100+ lines)
│   ├── Earth Engine initialization
│   ├── Database management
│   ├── Flask routes and endpoints
│   └── Health metrics calculation
│
├── sentinel_ndvi.py            # Sentinel-2 data processing module
│   ├── polygon_to_gee(): Convert map polygon to GEE geometry
│   └── get_ndvi_image(): Fetch and calculate NDVI
│
├── requirements.txt            # Python package dependencies
├── README.md                   # This documentation file
│
├── templates/                  # HTML templates
│   ├── map.html               # Interactive map interface
│   │   └── Leaflet map with polygon tools
│   ├── health_analysis.html   # Health metrics dashboard
│   │   └── Soil and crop health visualizations
│   ├── history.html           # Historical data viewer
│   │   └── Past analyses and trends
│   └── statistics.html        # Statistics and reports
│       └── Comparative analysis and summaries
│
├── static/                     # Frontend assets
│   ├── ndvi/                  # Generated NDVI visualization storage
│   │   └── [Generated PNG and TIFF files]
│   │
│   ├── script/                # JavaScript modules
│   │   ├── map.js             # Leaflet map initialization and controls
│   │   ├── health_analysis.js # Health metric visualization
│   │   ├── history.js         # Historical data management
│   │   └── statistics.js      # Statistical analysis functions
│   │
│   └── style/                 # CSS stylesheets
│       ├── map.css            # Map interface styling
│       ├── health_analysis.css # Dashboard styling
│       ├── history.css        # History page styling
│       └── statistics.css     # Statistics page styling
│
└── ndvi.db                    # SQLite database (created at runtime)
    └── Tables: ndvi_history
```

### File Descriptions

**app.py** (2100+ lines)
- Flask application with 20+ routes
- Earth Engine API integration
- Database schema and initialization
- Health metric calculations
- Image processing and export
- Error handling and offline mode support

**sentinel_ndvi.py**
- Geospatial data processing
- Polygon coordinate conversion
- Sentinel-2 image retrieval and filtering
- NDVI calculation from multispectral bands

**Database Schema (ndvi.db)**
```
ndvi_history table:
├── id (Primary Key)
├── place_name (TEXT)
├── datetime (TEXT) - Analysis timestamp
├── timestamp (TEXT) - Sentinel-2 acquisition date
├── Image Exports:
│   ├── ndvi_png, ndvi_tif
│   ├── rgb_png, savi_png, gndvi_png, evi_png
│   └── soil_health_png, crop_health_png
├── polygon (JSON)
├── Soil Health Metrics:
│   ├── soil_health_score, moisture_index
│   ├── organic_matter, texture_score, ph_level
└── Crop Health Metrics:
    ├── crop_health_score, vigor_index
    ├── stress_level, yield_potential, chlorophyll_content
```

## Usage Guide

### Getting Started with the Web Interface

#### 1. Home Page Navigation
- **Map**: Draw polygons and analyze crop health
- **Health Analysis**: View detailed health metrics
- **History**: Browse past analyses
- **Statistics**: Generate reports and trends

#### 2. Analyzing a Specific Location

**Step-by-Step Process:**

1. **Navigate to Map page**
   - Click "Map" from the main menu
   - Wait for Leaflet map to load with OpenStreetMap base layer

2. **Search for location** (Optional)
   - Use search bar to find a place (e.g., "Iowa Farmland")
   - Map will auto-zoom to location
   - Geolocation lookup uses Nominatim (OSM reverse geocoding)

3. **Define area of interest**
   - Click "Draw Polygon" button in toolbar
   - Click on map to create polygon vertices
   - Double-click or press Enter to complete polygon
   - Polygon coordinates stored in GeoJSON format

4. **Run analysis**
   - Click "Analyze" button
   - Flask backend:
     - Retrieves latest Sentinel-2 imagery
     - Filters for minimum cloud cover
     - Calculates vegetation indices
     - Derives health metrics
     - Generates visualizations
   - Processing typically takes 30-60 seconds

5. **Review results**
   - View generated maps (NDVI, SAVI, GNDVI, EVI)
   - Examine health scores and metrics
   - Check historical trends

6. **Export data** (Optional)
   - Download PNG for presentations
   - Export GeoTIFF for GIS analysis
   - Save results to history

#### Understanding Health Scores

**Soil Health Score (0-100)**
- **90-100**: Excellent (ideal moisture, high organic matter)
- **70-89**: Good (minor improvements possible)
- **50-69**: Moderate (intervention recommended)
- **30-49**: Poor (multiple issues detected)
- **0-29**: Critical (immediate action needed)

**Crop Health Score (0-100)**
- **90-100**: Excellent crop condition
- **70-89**: Good growth, minor stress
- **50-69**: Moderate growth, manageable stress
- **30-49**: Significant stress, yield impact expected
- **0-29**: Critical stress, crop in danger

**Stress Level (0-100)**
- Calculated from NDVI and EVI anomalies
- High values indicate water stress, disease, or nutrient deficiency
- Compare against seasonal baseline for context

**Yield Potential (%)**
- 100%: Optimal growing conditions
- 80-99%: Good yield expected
- 60-79%: Moderate yield, management opportunities
- <60%: Yield concerns, intervention needed

#### 3. Viewing Historical Data

1. **Navigate to History page**
   - View all past analyses in reverse chronological order
   - Displays: Location, analysis date, health scores

2. **Select analysis to review**
   - Click on entry to view detailed results
   - Compare with previous analyses
   - Identify trends

3. **Generate comparison**
   - Select multiple entries
   - View side-by-side metrics
   - Track seasonal changes

#### 4. Analyzing Statistics and Reports

1. **Navigate to Statistics page**
   - Select date range for analysis
   - Choose metrics to compare

2. **View aggregated data**
   - Average health scores across all analyses
   - Trend charts showing changes over time
   - Standard deviation and variability analysis

3. **Export report**
   - Download summary as CSV
   - Generate PDF report (if enabled)

### Advanced Usage Scenarios

#### Precision Agriculture Application
1. Divide large field into 10-20 hectare polygons
2. Analyze each polygon separately
3. Create composite stress map
4. Plan targeted intervention (irrigation, fertilizer)
5. Monitor recovery over 2-4 weeks

#### Disease Management
1. Identify areas with anomalous GNDVI values
2. Cross-reference with crop health scores
3. Correlate with weather data
4. Schedule scouting missions
5. Document treatment effectiveness

#### Yield Prediction
1. Analyze crop health at V6-V8 growth stage
2. Compare vigor index with historical baseline
3. Adjust yield forecasts based on stress level
4. Plan harvest logistics
5. Validate actual vs. predicted at harvest

#### Water Management
1. Monitor moisture index spatially
2. Identify over-irrigated and under-irrigated zones
3. Adjust irrigation scheduling
4. Reduce water waste
5. Optimize yield per unit water

## API Endpoints Reference

### Web Pages (GET Routes)

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/` | Home page | HTML homepage with menu |
| `/map` | Interactive map interface | Map page with Leaflet |
| `/health_analysis` | Health metrics dashboard | Dashboard HTML |
| `/history` | Historical data viewer | Past analyses list |
| `/statistics` | Statistical reports | Analysis trends and summaries |

### Data Endpoints (POST/GET)

#### POST /analyze
**Purpose**: Execute satellite analysis for a polygon area

**Request Format**:
```json
{
  "polygon": [[{"lat": 40.123, "lng": -93.456}, ...]],
  "place_name": "Farm Name",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Response Format**:
```json
{
  "success": true,
  "ndvi_url": "static/ndvi/ndvi_20240123.png",
  "health_analysis": {
    "soil_health_score": 78.5,
    "moisture_index": 0.62,
    "organic_matter": 0.45,
    "texture_score": 75.0,
    "ph_level": 6.8,
    "crop_health_score": 82.3,
    "vigor_index": 0.71,
    "stress_level": 15.2,
    "yield_potential": 94.5,
    "chlorophyll_content": 0.68
  },
  "metadata": {
    "image_date": "2024-01-15",
    "cloud_coverage": "12%"
  }
}
```

#### GET /api/history
**Purpose**: Retrieve all past analyses

**Response**: JSON array of analysis records with timestamps and metrics

#### GET /api/stats
**Purpose**: Get aggregated statistics

**Query Parameters**:
- `start_date`: Begin date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response**: JSON with mean, median, std deviation of metrics

#### GET /download
**Purpose**: Download analysis results

**Query Parameters**:
- `id`: Analysis ID from database
- `format`: "png", "tiff", or "zip"

**Response**: File download in requested format

### Earth Engine Integration

The application uses these Sentinel-2 datasets:

**Dataset**: `COPERNICUS/S2_SR`
- **Bands Used**: 
  - B02 (Blue): 10m
  - B03 (Green): 10m
  - B04 (Red): 10m
  - B08 (NIR): 10m
  - B11 (SWIR): 20m (resampled to 10m)
- **Temporal Coverage**: 2015-present
- **Revisit Frequency**: 5 days (global coverage)
- **Processing**: L2A (Bottom of Atmosphere reflectance)

## Database Schema Details

### SQLite Database: ndvi.db

**Table: ndvi_history**

```sql
CREATE TABLE ndvi_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_name TEXT,                   -- Location name
    datetime TEXT,                     -- Analysis timestamp
    timestamp TEXT,                    -- Sentinel-2 scene date
    
    -- Generated Visualizations
    ndvi_png TEXT,                     -- NDVI PNG file path
    ndvi_tif TEXT,                     -- NDVI GeoTIFF file path
    rgb_png TEXT,                      -- RGB composite PNG
    savi_png TEXT,                     -- SAVI visualization
    gndvi_png TEXT,                    -- GNDVI visualization
    evi_png TEXT,                      -- EVI visualization
    soil_health_png TEXT,              -- Soil health map
    crop_health_png TEXT,              -- Crop health map
    
    -- GeoSpatial Data
    polygon TEXT,                      -- Area boundary (GeoJSON)
    
    -- Soil Health Metrics (0-100 or actual values)
    soil_health_score REAL,            -- Composite soil quality
    moisture_index REAL,               -- Relative water content
    organic_matter REAL,               -- Carbon content percentage
    texture_score REAL,                -- Soil structure rating
    ph_level REAL,                     -- Acidity/alkalinity (0-14)
    
    -- Crop Health Metrics
    crop_health_score REAL,            -- Overall crop vitality
    vigor_index REAL,                  -- Growth and biomass rate
    stress_level REAL,                 -- Stress percentage (0-100)
    yield_potential REAL,              -- Potential yield percentage
    chlorophyll_content REAL           -- Leaf pigment concentration
)
```

### Data Retention and Cleanup

- All analyses stored permanently in ndvi.db
- Generated PNG/TIFF files in static/ndvi/
- Recommend regular backups for production use
- Old files can be manually deleted if storage is limited

### Query Examples

**Get latest analysis for a location:**
```sql
SELECT * FROM ndvi_history 
WHERE place_name = 'Farm Name' 
ORDER BY datetime DESC 
LIMIT 1;
```

**Find analyses with high crop stress:**
```sql
SELECT place_name, datetime, crop_health_score, stress_level 
FROM ndvi_history 
WHERE stress_level > 50 
ORDER BY datetime DESC;
```

**Calculate average health over time:**
```sql
SELECT 
  DATE(datetime) as analysis_date,
  AVG(crop_health_score) as avg_health,
  AVG(soil_health_score) as avg_soil
FROM ndvi_history 
GROUP BY DATE(datetime) 
ORDER BY analysis_date;
```

## Troubleshooting Guide

### Earth Engine Issues

#### 1. Earth Engine Not Initializing
**Symptom**: "⚠️ Need to authenticate Earth Engine" message

**Solutions**:
- Run authentication: `python -c "import ee; ee.Authenticate()"`
- Ensure you see the browser popup for authorization
- Copy the entire verification code (including dashes)
- Wait 10 seconds after pasting code before restarting app

**Verify**: 
```bash
python -c "import ee; ee.Initialize(project='ndvi-project-482615'); print('✓ Earth Engine initialized')"
```

#### 2. Connection Timeout to Earth Engine
**Symptom**: Application hangs when analyzing a location

**Solutions**:
- Check internet connection: `ping oauth2.googleapis.com`
- Verify Google Cloud project is active
- Check if quota has been exceeded in Google Cloud Console
- Try analyzing smaller polygon (fewer pixels)
- Wait 5-10 minutes and retry (may be temporary API issue)

#### 3. Invalid Project ID
**Symptom**: "Invalid project: ..." error

**Solutions**:
- Get your project ID from Google Cloud Console
- Edit app.py and update: `ee.Initialize(project='YOUR-PROJECT-ID')`
- Ensure project has Earth Engine API enabled
- Restart the application

### Network and Connectivity

#### 1. No Internet Connection
**Symptom**: Application starts but "⚠️ Warning: No internet connection detected"

**Impact**:
- Earth Engine features disabled
- Can still browse historical data locally
- Map and UI still functional with cached data
- Search/geocoding features unavailable

**Solution**: Restore internet connection or enable cellular backup

#### 2. Firewall Blocking Connection
**Symptom**: Timeouts when accessing Earth Engine

**Solutions**:
- Add exceptions for: `oauth2.googleapis.com:443`
- Allow Python.exe network access in Windows Firewall
- Contact IT if on corporate network
- Use VPN if accessing from restricted network

### Database Issues

#### 1. Database Locked Error
**Symptom**: "database is locked" error during analysis

**Causes**: Multiple concurrent requests or incomplete writes

**Solutions**:
- Restart Flask application
- Delete `ndvi.db` and restart (loses history)
- Ensure only one browser tab is accessing the app
- Check for other Python processes: `tasklist | find "python"`

#### 2. Missing or Corrupted Database
**Symptom**: Application crashes on startup with database error

**Solutions**:
- Backup current database: `copy ndvi.db ndvi.db.backup`
- Delete database: `del ndvi.db`
- Restart application (will recreate with schema)
- Restore from backup if needed

### Frontend Issues

#### 1. Map Not Loading
**Symptom**: Blank white map area

**Solutions**:
- Check browser console for errors (F12 → Console)
- Clear browser cache: Ctrl+Shift+Delete
- Refresh page: Ctrl+R or Ctrl+F5
- Try different browser (Chrome, Firefox, Edge)
- Verify internet connection to CDN (Leaflet libraries)

#### 2. Polygon Drawing Not Working
**Symptom**: Cannot draw on map

**Solutions**:
- Ensure "Draw Polygon" button is active
- Click once for each vertex, double-click to finish
- Click "Cancel" to reset if stuck
- Try refreshing the page

#### 3. Statistics Page Slow or Unresponsive
**Symptom**: Statistics page takes long time to load

**Solutions**:
- Close other applications to free RAM
- Reduce date range in analysis filter
- Clear database of old entries (keep last 100)
- Check if Flask is processing: look at terminal output

### Performance Optimization

#### Improving Analysis Speed
1. **Reduce polygon size**: Smaller areas = faster processing
2. **Narrow date range**: Fewer Sentinel-2 scenes to search
3. **Use cloud filter**: Set cloud coverage threshold < 20%
4. **Increase RAM**: 8GB+ recommended for complex analyses
5. **Batch process**: Analyze same area weekly instead of daily

#### Reducing Database Size
1. Archive old records: `sqlite3 ndvi.db "DELETE FROM ndvi_history WHERE datetime < '2023-01-01'"`
2. Compress images: Export as JPEG instead of PNG
3. Delete unused TIFF files: TIFF files are 10-50MB each
4. Regular cleanup: Monthly delete of test analyses

### Debug Mode

**Enable detailed logging:**

Edit `app.py` and add before `if __name__`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Then restart: `python app.py`

Check terminal for detailed error messages and API calls.

### Getting Help

If issue persists:

1. **Check logs**: Look at Flask terminal output for error messages
2. **Enable debug**: Add `app.run(debug=True)` in app.py
3. **Test components**: 
   - Test Earth Engine: `python -c "import ee; print(ee.String('hello').getInfo())"`
   - Test Geopy: `python -c "from geopy.geocoders import Nominatim; print(Nominatim(user_agent='test').geocode('Iowa'))"`
4. **Document issue**: Note the error message, steps to reproduce, and system info
5. **Report**: Include:
   - Error message verbatim
   - Python version: `python --version`
   - Flask version: `pip show flask | findstr Version`
   - Operating system
   - Steps to reproduce

## Technical Details and Architecture

### System Architecture

```
┌─────────────────────────────────────────────────┐
│         Web Browser (Client)                    │
│  ├─ Leaflet Map (map.js)                       │
│  ├─ Health Dashboard (health_analysis.js)      │
│  ├─ History Viewer (history.js)                │
│  └─ Statistics (statistics.js)                 │
└──────────────────┬──────────────────────────────┘
                   │ HTTP/JSON
┌──────────────────▼──────────────────────────────┐
│     Flask Web Application (app.py)              │
│  ├─ Route handlers                              │
│  ├─ Request validation                          │
│  ├─ Business logic                              │
│  └─ Response formatting                         │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼──────┐  │  ┌───────▼──────┐
│   Earth      │  │  │  SQLite      │
│   Engine API │  │  │  Database    │
│   Google     │  │  │ (ndvi.db)    │
│   Cloud      │  │  └──────────────┘
└──────────────┘  │
        │         │
        │    ┌────▼─────────┐
        │    │ Sentinel_ndvi │
        │    │ Module        │
        │    └───────────────┘
        │
   ┌────▼──────────────────────┐
   │  Sentinel-2 Imagery       │
   │  (COPERNICUS/S2_SR)       │
   │  Multispectral Bands      │
   └───────────────────────────┘
```

### Data Flow for Analysis

1. **User Input** → Draw polygon, click Analyze
2. **Browser** → POST request with GeoJSON polygon
3. **Flask** → Receive request, validate polygon
4. **Conversion** → Convert Leaflet coords to GEE geometry
5. **Earth Engine** → Query Sentinel-2 scenes (cloud-filtered)
6. **Processing** → Calculate NDVI, SAVI, GNDVI, EVI
7. **Metrics** → Derive soil and crop health scores
8. **Visualization** → Generate PNG/TIFF files
9. **Storage** → Save to SQLite with metadata
10. **Response** → Return results to browser
11. **Display** → Render maps and metrics on dashboard

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Flask 3.0.0 | Web framework, routing |
| **GIS** | Earth Engine API | Satellite imagery, analysis |
| **Database** | SQLite 3 | Local persistent storage |
| **Geocoding** | Geopy + Nominatim | Address ↔ coordinates |
| **HTTP** | Requests library | API calls |
| **Frontend** | Leaflet.js | Interactive mapping |
| **Styling** | CSS3 | User interface design |
| **Scripting** | JavaScript | Client-side interactivity |

### Sentinel-2 Spectral Bands Used

| Band | Name | Resolution | Wavelength | Purpose |
|------|------|------------|-----------|---------|
| B02 | Blue | 10m | 490 nm | Water, aerosol |
| B03 | Green | 10m | 560 nm | Vegetation (green chlorophyll) |
| B04 | Red | 10m | 665 nm | Vegetation boundaries |
| B08 | NIR | 10m | 842 nm | Vegetation density |
| B11 | SWIR | 20m | 1610 nm | Moisture, soil type |

### Computational Complexity

- **Per-analysis Processing**:
  - Sentinel-2 image retrieval: 5-15 seconds
  - Index calculation: 5-10 seconds
  - Visualization generation: 10-20 seconds
  - Total typical time: 30-60 seconds

- **Database Operations**:
  - Insert record: ~100ms
  - Query history: ~50ms (per 1000 records)
  - Statistics calculation: depends on dataset size

### Security Considerations

1. **Earth Engine API Keys**
   - Stored in user's Google account
   - Never transmitted through Flask
   - OAuth 2.0 authentication flow

2. **Database Access**
   - SQLite stored locally (not remote)
   - No authentication required for local access
   - Input validation on polygon coordinates

3. **File System**
   - Generated images stored in `static/ndvi/`
   - Accessible via web server
   - File paths sanitized to prevent directory traversal

4. **Data Privacy**
   - No user data transmitted to third parties
   - All analysis local to your computer
   - History stored on your machine only

## Frequently Asked Questions (FAQ)

### Satellite Imagery and Data

**Q: Why is the satellite image from a different date than my analysis?**
A: Sentinel-2 revisits each location every 5 days. The system automatically selects the most recent cloud-free image. The acquisition date is shown in results.

**Q: What if my area is always cloudy?**
A: The system filters for <90% cloud coverage. In persistent cloud, try:
- Analyzing a larger area (clouds may not cover entire region)
- Analyzing different season (typically drier/clearer)
- Using annual composites instead of single dates

**Q: How accurate are the NDVI values?**
A: Sentinel-2 NDVI typically has ±0.02-0.05 accuracy. For field validation:
- Collect ground truthing at 5-10 representative points
- Compare with handheld NDVI meters
- Account for time difference (satellite vs. ground measurement)

**Q: What's the spatial resolution?**
A: Sentinel-2 standard bands (B02-B04, B08) are 10m pixels. This means:
- Each pixel = 100 m² (0.01 hectare)
- Minimum practical polygon: ~10 hectares (100 pixels)
- Smaller areas have higher per-pixel noise

### Analysis and Health Scores

**Q: How often should I analyze my field?**
A: Recommendations by purpose:
- **Monitoring**: Weekly or bi-weekly
- **Problem diagnosis**: As soon as issue suspected
- **Yield prediction**: V6-V8 growth stage
- **Stress detection**: During critical growth periods
- **Routine**: Monthly for seasonal trends

**Q: Can I compare NDVI across different crops?**
A: Yes, but with caveats:
- Baseline differs: maize NDVI > soybean > wheat
- Phenology differs: timing of maximum NDVI varies
- Consider crop type when interpreting values
- Use stress level (relative to crop type) for comparison

### Data Export and Analysis

**Q: What format should I use for GIS analysis?**
A: GeoTIFF is recommended:
- Preserves geospatial information
- Compatible with ArcGIS, QGIS, etc.
- Larger file size (~20-50MB) but lossless
- PNG better for presentations and reports

## Support and References

For issues with Sentinel-2 data or Earth Engine, visit:
- [Google Earth Engine Documentation](https://developers.google.com/earth-engine)
- [Copernicus Open Access Hub](https://scihub.copernicus.eu/)
- [USGS Remote Sensing Fundamentals](https://www.usgs.gov/faqs/what-normalized-difference-vegetation-index-ndvi)

## License

This project is for agricultural monitoring and crop health analysis.

## Acknowledgments

This application leverages:
- **Google Earth Engine**: Satellite imagery and processing
- **Sentinel-2/Copernicus**: Free global multispectral data
- **Flask & Leaflet**: Web application framework and mapping



