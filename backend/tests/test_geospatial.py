import pytest
import numpy as np
from app.services.geospatial_processor import geospatial_processor

def test_aoi_validation_bbox():
    # Hyderabad Hussain Sagar bounding box
    bbox = [78.46, 17.41, 78.49, 17.44]
    res = geospatial_processor.validate_and_parse_aoi(bbox=bbox)
    assert res["bbox"] == bbox
    assert len(res["centroid"]) == 2
    assert res["area_sq_km"] > 0
    assert res["geometry"]["type"] == "Polygon"

def test_aoi_validation_polygon():
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [78.46, 17.41],
            [78.49, 17.41],
            [78.49, 17.44],
            [78.46, 17.44],
            [78.46, 17.41]
        ]]
    }
    res = geospatial_processor.validate_and_parse_aoi(geometry=polygon)
    assert len(res["bbox"]) == 4
    assert res["area_sq_km"] > 0

def test_spectral_indices():
    red = np.full((50, 50), 40, dtype=np.uint8)
    green = np.full((50, 50), 120, dtype=np.uint8)
    blue = np.full((50, 50), 40, dtype=np.uint8)
    nir = np.full((50, 50), 180, dtype=np.uint8)

    indices = geospatial_processor.compute_spectral_indices(red, green, blue, nir)
    assert "ndvi" in indices
    assert "ndwi" in indices
    # High NIR compared to red should yield positive NDVI (vegetation)
    assert np.mean(indices["ndvi"]) > 0.4

def test_sar_calibration():
    sar_dn = np.random.randint(20, 220, (64, 64), dtype=np.uint8)
    db, norm = geospatial_processor.calibrate_sar_backscatter(sar_dn)
    assert db.shape == (64, 64)
    assert norm.shape == (64, 64)
    assert norm.dtype == np.uint8
