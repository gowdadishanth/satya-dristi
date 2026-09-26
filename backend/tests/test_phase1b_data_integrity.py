import os
import pytest
import numpy as np
from PIL import Image

from app.services.geospatial_processor import geospatial_processor
from app.models.change_specialist import change_specialist


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


# ============================================================================
# CR-ML-01: STRUCTURAL CHANGE SIGNAL TESTS
# ============================================================================

def test_change_specialist_genuine_structural_change(tmp_path):
    """
    Validates that a genuine physical change (new built-up area on vegetation background)
    is successfully detected with change_pct > 0 and built_up_change_pct > 0.
    """
    before_path = tmp_path / "before_genuine.png"
    after_path = tmp_path / "after_genuine.png"

    # Background: green vegetation
    arr_b = np.full((100, 100, 3), [60, 120, 50], dtype=np.uint8)
    Image.fromarray(arr_b).save(before_path)

    # After: 20x20 concrete building block added
    arr_a = arr_b.copy()
    arr_a[30:50, 30:50] = [200, 195, 190]  # high structural contrast (>100 DN difference)
    Image.fromarray(arr_a).save(after_path)

    result = change_specialist.analyze_change(
        before_image_path=str(before_path),
        after_image_path=str(after_path),
        query="Detect new structures",
        analysis_id="test_phase1b_genuine"
    )

    assert result["change_pct"] > 0
    assert result["built_up_change_pct"] > 0
    assert "built-up expansion detected" in result["answer"]
    assert os.path.exists(result["evidence_image_path"])


def test_change_specialist_spectral_only_change(tmp_path):
    """
    Validates that a uniform illumination / atmospheric haze shift (+10 DN across all pixels)
    is filtered out by the structural threshold (struct_diff <= 15), preventing false alarms.
    """
    before_path = tmp_path / "before_haze.png"
    after_path = tmp_path / "after_haze.png"

    # Base image with varied natural texture
    np.random.seed(42)
    base = np.random.randint(60, 140, (100, 100, 3), dtype=np.uint8)
    Image.fromarray(base).save(before_path)

    # After image: uniform +10 DN brightness increase (sun angle / thin haze artifact)
    hazed = np.clip(base.astype(np.int16) + 10, 0, 255).astype(np.uint8)
    Image.fromarray(hazed).save(after_path)

    result = change_specialist.analyze_change(
        before_image_path=str(before_path),
        after_image_path=str(after_path),
        query="Check for construction",
        analysis_id="test_phase1b_haze"
    )

    # Under Phase 1B, the 10 DN shift is below MIN_STRUCT_DIFF (15) and rejected
    assert result["change_pct"] == 0.0
    assert result["built_up_change_pct"] == 0.0
    assert "minor spectral surface variations with no extensive structural change" in result["answer"]


def test_change_specialist_no_change_identical_images(tmp_path):
    """Validates that comparing an image to itself returns exactly 0.0% change."""
    img_path = tmp_path / "identical.png"

    arr = np.full((80, 80, 3), [70, 100, 60], dtype=np.uint8)
    Image.fromarray(arr).save(img_path)

    result = change_specialist.analyze_change(
        before_image_path=str(img_path),
        after_image_path=str(img_path),
        query="Identify differences",
        analysis_id="test_phase1b_identical"
    )

    assert result["change_pct"] == 0.0
    assert result["built_up_change_pct"] == 0.0
    assert result["water_change_pct"] == 0.0
    assert "minor spectral surface variations with no extensive structural change" in result["answer"]


def test_change_specialist_scaling_assumptions(tmp_path):
    """Validates that uint8 0..255 inputs are properly converted and do not overflow."""
    before_path = tmp_path / "scale_b.png"
    after_path = tmp_path / "scale_a.png"

    # Base background: low intensity near 5 DN
    arr_b = np.full((64, 64, 3), 5, dtype=np.uint8)
    arr_a = arr_b.copy()
    # High intensity feature near 250 DN in a 24x24 subregion
    arr_a[20:44, 20:44] = 250

    Image.fromarray(arr_b).save(before_path)
    Image.fromarray(arr_a).save(after_path)

    result = change_specialist.analyze_change(
        before_image_path=str(before_path),
        after_image_path=str(after_path),
        query="Check change at dynamic range extremes",
        analysis_id="test_phase1b_scaling"
    )

    # 245 DN diff is huge -> should detect massive change without arithmetic wrapping
    assert result["change_pct"] > 0
    assert result["built_up_change_pct"] > 0
