import os
import json
import pytest
import numpy as np
from PIL import Image
from pathlib import Path
import pypdf

from app.services.report_generator import report_generator
from app.models.gemini_provider import gemini_provider, GeminiObjectDetection
from app.services.stac_service import stac_service
from app.services.image_retrieval import image_retrieval_service
from app.core.config import settings


@pytest.fixture
def high_res_scenes(tmp_path):
    """Generates high-resolution test scenes for PDF structural validation."""
    opt_path = tmp_path / "high_res_optical.png"
    before_path = tmp_path / "high_res_before.png"
    after_path = tmp_path / "high_res_after.png"
    sar_path = tmp_path / "high_res_sar.png"
    ev_path = tmp_path / "high_res_evidence.png"

    # High-resolution 800x600 RGB optical scene
    np.random.seed(42)
    opt_arr = np.full((600, 800, 3), [60, 110, 45], dtype=np.uint8)
    opt_arr[150:350, 200:500] = [30, 80, 150]  # water body
    opt_arr[400:550, 450:700] = [190, 185, 180] # urban sector
    Image.fromarray(opt_arr).save(opt_path)

    # Before & After pair (800x600)
    before_arr = opt_arr.copy()
    before_arr[400:550, 450:700] = [60, 110, 45]  # was vegetation before
    Image.fromarray(before_arr).save(before_path)

    after_arr = opt_arr.copy() # now has urban development
    Image.fromarray(after_arr).save(after_path)

    # High-resolution SAR (800x600 grayscale)
    sar_arr = np.full((600, 800), 100, dtype=np.uint8)
    sar_arr[150:350, 200:500] = 30   # specular low backscatter on water
    sar_arr[400:550, 450:700] = 215  # double bounce on structures
    Image.fromarray(sar_arr).save(sar_path)

    # High-resolution evidence layer (800x600)
    ev_arr = opt_arr.copy()
    ev_arr[150:350, 200:500] = [225, 170, 45] # annotated highlighting
    Image.fromarray(ev_arr).save(ev_path)

    return {
        "optical": str(opt_path),
        "before": str(before_path),
        "after": str(after_path),
        "sar": str(sar_path),
        "evidence": str(ev_path)
    }


def test_pdf_single_image_and_grounding_embedding(high_res_scenes):
    """
    Validates that a Grounding report embeds:
    1. The high-resolution observation scene
    2. The annotated grounding evidence layer
    Asserts both are >= 400px (not thumbnails) and effective DPI >= 180 DPI.
    """
    analysis_doc = {
        "analysis_id": "AN-TEST-P2-GRD",
        "uid": "test-analyst-p2",
        "task": "Grounding",
        "query": "Locate the central water reservoir",
        "input": "Single image",
        "answer": "Identified contiguous surface water reservoir in central region.",
        "confidence": "High",
        "confidence_score": 0.94,
        "primary_image_path": high_res_scenes["optical"],
        "evidence_path": high_res_scenes["evidence"],
        "model_used": "Gemini 2.5 Flash",
        "date": "2026-09-19",
        "time": "14:30",
        "aoi": {"bbox": [78.46, 17.41, 78.49, 17.44], "area_sq_km": 10.5},
        "execution_trace": [
            {"name": "Input validation", "detail": "CRS verified", "duration": "0.02s"},
            {"name": "Model inference", "detail": "Grounding feature segmented via Gemini 2.5 Flash", "duration": "0.15s"}
        ]
    }

    report = report_generator.generate_report_artifacts(analysis_doc)
    pdf_path = Path(report["pdf_path"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 5000

    # Structural verification with pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1

    page = reader.pages[0]
    text = page.extract_text()
    assert "SATYA DRISTI" in text
    assert "Locate the central water reservoir" in text
    assert "Grounded Feature Localization" in text

    # Extract embedded images and verify pixel fidelity
    embedded_images = page.images
    assert len(embedded_images) == 2, f"Expected 2 images, got {len(embedded_images)}"

    for img_obj in embedded_images:
        pil_img = img_obj.image
        w, h = pil_img.size
        # Must be full resolution source, not tiny thumbnail
        assert w >= 400, f"Embedded image width {w}px is too small (thumbnail detected!)"
        assert h >= 300, f"Embedded image height {h}px is too small (thumbnail detected!)"

        # Column width in ReportLab is 265 pt = 3.68 inches
        effective_dpi = w / (265.0 / 72.0)
        assert effective_dpi >= 180.0, f"Effective DPI {effective_dpi:.1f} is below 180 DPI target"


def test_pdf_before_after_temporal_layout(high_res_scenes):
    """
    Validates that a Bi-Temporal Change report embeds 3 images side-by-side:
    1. Pre-Observation (Before)
    2. Post-Observation (After)
    3. Bi-Temporal Change Detection Map
    """
    analysis_doc = {
        "analysis_id": "AN-TEST-P2-CHG",
        "uid": "test-analyst-p2",
        "task": "Bi-Temporal Change",
        "query": "Detect urban expansion",
        "input": "Before + After",
        "answer": "Detected notable urban expansion along the eastern sector.",
        "confidence": "High",
        "confidence_score": 0.91,
        "before_image_path": high_res_scenes["before"],
        "primary_image_path": high_res_scenes["after"],
        "evidence_path": high_res_scenes["evidence"],
        "model_used": "Gemini 2.5 Flash",
        "date": "2026-09-19",
        "time": "14:32"
    }

    report = report_generator.generate_report_artifacts(analysis_doc)
    pdf_path = Path(report["pdf_path"])
    reader = pypdf.PdfReader(str(pdf_path))
    page = reader.pages[0]
    text = page.extract_text()

    assert "Pre-Observation" in text
    assert "Post-Observation" in text
    assert "Bi-Temporal Change Map" in text

    # Verify all 3 images are embedded side-by-side
    assert len(page.images) == 3
    for img_obj in page.images:
        pil_img = img_obj.image
        assert pil_img.width >= 400
        assert pil_img.height >= 300


def test_pdf_optical_sar_fusion_layout(high_res_scenes):
    """
    Validates that an Optical + SAR report embeds 3 images side-by-side:
    1. Sentinel-2 Optical
    2. Sentinel-1 SAR Backscatter
    3. Cross-Modal Radiometric Fusion
    """
    analysis_doc = {
        "analysis_id": "AN-TEST-P2-FUS",
        "uid": "test-analyst-p2",
        "task": "Optical + SAR Fusion",
        "query": "Cross-modal verification",
        "input": "Optical + SAR",
        "answer": "Cross-modal verification confirmed high dielectric consensus.",
        "confidence": "High",
        "confidence_score": 0.92,
        "primary_image_path": high_res_scenes["optical"],
        "sar_image_path": high_res_scenes["sar"],
        "evidence_path": high_res_scenes["evidence"],
        "model_used": "Gemini 2.5 Flash",
        "date": "2026-09-19",
        "time": "14:35"
    }

    report = report_generator.generate_report_artifacts(analysis_doc)
    pdf_path = Path(report["pdf_path"])
    reader = pypdf.PdfReader(str(pdf_path))
    page = reader.pages[0]
    text = page.extract_text()

    assert "Sentinel-2 Optical" in text
    assert "Sentinel-1 SAR" in text
    assert "Cross-Modal Radiometric Fusion" in text
    assert len(page.images) == 3


def test_pdf_no_distortion_aspect_ratio(tmp_path):
    """
    Validates that non-square aspect ratios (e.g. 16:9 panoramic and 4:3)
    are embedded without distortion or aspect ratio deformation.
    """
    wide_img_path = tmp_path / "panoramic_16_9.png"
    wide_arr = np.full((450, 800, 3), [80, 120, 90], dtype=np.uint8)  # 16:9
    Image.fromarray(wide_arr).save(wide_img_path)

    analysis_doc = {
        "analysis_id": "AN-TEST-P2-WIDE",
        "uid": "test-analyst-p2",
        "task": "Single-Image VQA",
        "query": "Inspect panoramic corridor",
        "input": "Single image",
        "answer": "Wide corridor terrain verified.",
        "confidence": "High",
        "primary_image_path": str(wide_img_path),
        "date": "2026-09-19"
    }

    report = report_generator.generate_report_artifacts(analysis_doc)
    pdf_path = Path(report["pdf_path"])
    reader = pypdf.PdfReader(str(pdf_path))
    page = reader.pages[0]

    assert len(page.images) >= 1
    embedded = page.images[0].image
    # Verify the embedded image preserves original 16:9 aspect ratio
    src_aspect = 800.0 / 450.0
    embedded_aspect = embedded.width / embedded.height
    assert abs(src_aspect - embedded_aspect) < 0.02


def test_grounding_evidence_overlay_annotated(high_res_scenes):
    """
    Validates that gemini_provider writes an annotated RGB evidence image
    containing bounding box highlights and observation badges.
    """
    from app.models.base_model import GroundedObject
    with Image.open(high_res_scenes["optical"]) as base_img:
        dummy_obj = GroundedObject(
            label="Water Body",
            confidence=0.95,
            bbox_norm=[25.0, 25.0, 50.0, 50.0]
        )
        ev_path = gemini_provider._render_evidence_overlay(
            base_img=base_img,
            objects=[dummy_obj],
            analysis_id="test_p2_grounding_ann",
            title="Grounding Overlay Test"
        )
        assert Path(ev_path).exists()
        assert Path(ev_path).suffix == ".png"

        with Image.open(ev_path) as img:
            assert img.mode == "RGB"
            assert img.size == (800, 600)
            arr = np.array(img)
            assert np.count_nonzero(arr) > 0


def test_sar_asset_resolution_in_stac():
    """Validates that stac_service resolves VV/VH polarizations for Sentinel-1 scenes."""
    sample_s1_feature = {
        "id": "S1A_IW_GRDH_1SDV_20260915_HYD",
        "properties": {
            "platform": "Sentinel-1A",
            "instruments": ["C-SAR"],
            "datetime": "2026-09-15T12:00:00Z",
            "sar:polarizations": ["VV", "VH"]
        },
        "bbox": [78.4, 17.3, 78.6, 17.5],
        "geometry": {"type": "Polygon", "coordinates": [[[78.4, 17.3], [78.6, 17.3], [78.6, 17.5], [78.4, 17.5], [78.4, 17.3]]]},
        "assets": {
            "vv": {
                "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/s1_vv.tif",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized"
            },
            "vh": {
                "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/s1_vh.tif",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized"
            }
        }
    }

    norm = stac_service._normalize_s1_feature(sample_s1_feature, provider="EarthSearch")
    assert norm["visual_url"] == "https://sentinel-cogs.s3.us-west-2.amazonaws.com/s1_vv.tif"
    assert "VV" in norm["available_bands"]
    assert "VH" in norm["available_bands"]


@pytest.mark.asyncio
async def test_sar_retrieval_does_not_call_optical_export(monkeypatch):
    """
    Validates that when treatment is 'sar', optical ArcGIS World Imagery export
    is NOT called, preventing optical imagery from being styled as fake SAR.
    """
    arcgis_called = False

    async def fake_arcgis(bbox, size):
        nonlocal arcgis_called
        arcgis_called = True
        return Image.new("RGB", size, (100, 100, 100))

    monkeypatch.setattr(image_retrieval_service, "_fetch_arcgis_high_res_export", fake_arcgis)

    sar_scene = {
        "scene_id": "S1_TEST_NO_ARCGIS",
        "bbox": [78.46, 17.41, 78.49, 17.44],
        "visual_url": None,
        "preview_url": None,
        "assets": {}
    }

    path, meta = await image_retrieval_service.retrieve_scene_image(
        scene=sar_scene,
        aoi_bbox=[78.46, 17.41, 78.49, 17.44],
        treatment="sar"
    )

    assert not arcgis_called, "ArcGIS Optical Export was illegally called for SAR treatment!"
    assert meta["treatment"] == "sar"
