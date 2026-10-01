import os
import pytest
import numpy as np
from PIL import Image

from app.services.geospatial_processor import geospatial_processor


# ============================================================================
# CR-GEO-03: NDWI / SPECTRAL INDEX CORRECTNESS TESTS
# ============================================================================

def test_visible_ndwi_formula_uses_green_and_blue():
    """
    Validates that in 3-band RGB imagery (no NIR), NDWI is computed using:
    (green - blue) / (green + blue + eps)
    and does NOT duplicate NDVI (green - red).
    """
    # Scenario: Water body where green reflectance is 120, blue is 60, red is 40
    red = np.full((32, 32), 40, dtype=np.uint8)
    green = np.full((32, 32), 120, dtype=np.uint8)
    blue = np.full((32, 32), 60, dtype=np.uint8)

    indices = geospatial_processor.compute_spectral_indices(red, green, blue, nir=None)

    assert "ndvi" in indices
    assert "ndwi" in indices

    # Expected visible NDVI: (120 - 40) / (120 + 40 + 1e-6) = 80 / 160 = 0.50
    expected_ndvi = (120.0 - 40.0) / (120.0 + 40.0 + 1e-6)
    # Expected visible NDWI: (120 - 60) / (120 + 60 + 1e-6) = 60 / 180 = 0.3333
    expected_ndwi = (120.0 - 60.0) / (120.0 + 60.0 + 1e-6)

    np.testing.assert_allclose(indices["ndvi"], expected_ndvi, atol=1e-4)
    np.testing.assert_allclose(indices["ndwi"], expected_ndwi, atol=1e-4)

    # CR-GEO-03 check: NDWI must NOT equal NDVI when blue != red
    assert not np.allclose(indices["ndwi"], indices["ndvi"])


def test_visible_ndwi_deep_clear_water():
    """Clear deep water where blue > green: NDWI should be negative with (green - blue)."""
    red = np.full((16, 16), 20, dtype=np.uint8)
    green = np.full((16, 16), 50, dtype=np.uint8)
    blue = np.full((16, 16), 110, dtype=np.uint8)

    indices = geospatial_processor.compute_spectral_indices(red, green, blue, nir=None)
    # (50 - 110) / (50 + 110) = -60 / 160 = -0.375
    assert np.all(indices["ndwi"] < 0)
    expected_ndwi = (50.0 - 110.0) / (50.0 + 110.0 + 1e-6)
    np.testing.assert_allclose(indices["ndwi"], expected_ndwi, atol=1e-4)


def test_nir_ndwi_remains_exact():
    """Validates that 4-band imagery with NIR uses standard McFeeters (green - nir)."""
    red = np.full((16, 16), 30, dtype=np.uint8)
    green = np.full((16, 16), 100, dtype=np.uint8)
    blue = np.full((16, 16), 40, dtype=np.uint8)
    nir = np.full((16, 16), 20, dtype=np.uint8)

    indices = geospatial_processor.compute_spectral_indices(red, green, blue, nir=nir)
    # (green - nir) / (green + nir) = (100 - 20) / (100 + 20) = 80 / 120 = 0.6667
    expected_ndwi = (100.0 - 20.0) / (100.0 + 20.0 + 1e-6)
    np.testing.assert_allclose(indices["ndwi"], expected_ndwi, atol=1e-4)
