import ee
import json

def polygon_to_gee(polygon_json):
    """
    Convert Leaflet polygon JSON to Earth Engine geometry
    """
    polygon = json.loads(polygon_json)
    coords = []

    for point in polygon[0]:
        coords.append([point["lng"], point["lat"]])

    return ee.Geometry.Polygon([coords])

def get_ndvi_image(aoi):
    """
    Fetch Sentinel-2 image and calculate NDVI
    """
    image = (
        ee.ImageCollection("COPERNICUS/S2_SR")
        .filterBounds(aoi)
        .filterDate("2024-01-01", "2024-12-31")
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
    )

    ndvi = image.normalizedDifference(["B08", "B04"]).rename("NDVI")
    return ndvi
