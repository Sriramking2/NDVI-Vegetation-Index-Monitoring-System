# NDVI Vegetation Index Monitoring System

An agricultural monitoring and analysis platform built with Flask, Sentinel-2 satellite imagery, and Google Earth Engine for vegetation health assessment, soil analysis, and crop recommendation workflows.

## Overview

This repository contains a geospatial crop-health monitoring system designed to support precision agriculture. The application uses multispectral satellite imagery to generate vegetation indices, visualize field conditions, track historical analyses, and estimate crop and soil health indicators for selected locations.

The project combines remote sensing, geospatial analysis, and web-based reporting into a single workflow. Users can define an area of interest, retrieve satellite imagery, calculate vegetation metrics, and review analytical outputs through an interactive web interface.

## Key Features

- Satellite-based vegetation monitoring using Sentinel-2 imagery
- NDVI, SAVI, GNDVI, and EVI index generation for crop-health assessment
- Soil health estimation and related analytics
- Interactive map-based selection of locations and field boundaries
- Historical analysis tracking and statistics views
- Output generation for visual inspection and downstream reporting
- Supporting crop recommendation workflow using local datasets and models

## Technology Stack

- Backend: Python, Flask
- Remote sensing source: Sentinel-2 imagery
- Geospatial processing: Google Earth Engine
- Frontend: HTML, CSS, JavaScript
- Data storage: SQLite
- Supporting analysis: Python data-processing and model files

## Repository Structure

```text
NDVI-Vegetation-Index-Monitoring-System/
├── Vegetation-Index-VI-Monitoring-System-main/
│   ├── app.py
│   ├── server_flask.py
│   ├── sentinel_ndvi.py
│   ├── templates/
│   ├── static/
│   ├── requirements.txt
│   └── README.md
├── recommend/
│   ├── soil_health_pipeline.py
│   ├── crop_requirements.csv
│   ├── Crop_recommendation.csv
│   └── requirements.txt
├── soil.html
└── README.md
```

## Main Components

### 1. Vegetation Monitoring Application

The primary Flask application lives inside `Vegetation-Index-VI-Monitoring-System-main/`. It is responsible for:

- serving the web interface
- receiving user-selected locations or polygons
- processing satellite imagery requests
- computing vegetation and health metrics
- rendering maps, dashboards, and historical views

### 2. Vegetation Index Processing

The project calculates multiple vegetation indices to support different perspectives on crop condition:

- `NDVI`: a core indicator for vegetation vigor and greenness
- `SAVI`: useful where soil background influence is significant
- `GNDVI`: useful for chlorophyll-related crop condition assessment
- `EVI`: helpful in areas with dense vegetation and atmospheric variability

### 3. Soil and Crop Recommendation Module

The `recommend/` folder contains supporting scripts, datasets, and model artifacts related to soil-health analysis and crop recommendation. This expands the system beyond visualization into practical agricultural decision support.

## Workflow

The typical workflow supported by this project is:

1. Open the web application.
2. Select or draw an area of interest on the map.
3. Retrieve imagery for the chosen location.
4. Generate vegetation-index outputs and health indicators.
5. Review maps, statistics, and historical results.
6. Use the recommendation pipeline for crop-related insights where applicable.

## Setup Instructions

### Prerequisites

- Python 3.8 or later
- A Google Earth Engine account with access enabled
- Internet connectivity for imagery and geospatial service access

### Installation

Clone the repository:

```bash
git clone https://github.com/Sriramking2/NDVI-Vegetation-Index-Monitoring-System.git
cd NDVI-Vegetation-Index-Monitoring-System
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the main application dependencies:

```bash
pip install -r Vegetation-Index-VI-Monitoring-System-main/requirements.txt
```

If you also want to run the recommendation pipeline, install its dependencies as well:

```bash
pip install -r recommend/requirements.txt
```

### Google Earth Engine Authentication

Before running features that depend on Earth Engine, authenticate your local environment:

```bash
earthengine authenticate
```

## Running the Application

From the repository root, run:

```bash
python Vegetation-Index-VI-Monitoring-System-main/app.py
```

If your local setup uses the alternate server entry point, you can also use:

```bash
python Vegetation-Index-VI-Monitoring-System-main/server_flask.py
```

Then open the local server URL shown in the terminal, typically:

```text
http://127.0.0.1:5000
```

## Use Cases

- crop-health monitoring for agricultural fields
- vegetation-condition assessment across different locations
- identifying stress patterns through vegetation indices
- soil-health oriented exploratory analysis
- educational and academic demonstrations in remote sensing and precision agriculture

## Data and Output Notes

This repository includes source code, templates, and supporting datasets. Local runtime artifacts such as generated imagery, databases, caches, and virtual environments are intentionally excluded from version control where appropriate so the repository remains easier to maintain and publish.

## Project Strengths

- practical combination of geospatial analytics and web delivery
- clear agricultural use case with real-world relevance
- support for multiple vegetation metrics instead of a single index
- extensible structure for additional models, views, and reports

## Future Improvements

- deployment configuration for cloud hosting
- automated tests for Flask routes and analysis logic
- clearer environment variable configuration for secrets and credentials
- sample screenshots in the README
- API documentation for backend endpoints
- model and dataset versioning for reproducibility

## Author

Sriram Purushothaman

GitHub: [Sriramking2](https://github.com/Sriramking2)

## License

Add a license file if you plan to make the project openly reusable on GitHub.
