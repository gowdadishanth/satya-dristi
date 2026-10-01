import os
import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, AsyncMock

from app.core.config import settings
from app.core.errors import SARUnavailableError
from app.models.base_model import StructuredAIFindings, LandCoverItem, TemporalChangeItem
from app.models.router import model_router
from app.models.gemini_provider import gemini_provider
from app.services.report_generator import report_generator


@pytest.fixture
def sample_rasters(tmp_path):
    """Creates temporary real RGB and SAR rasters for testing."""
    opt_path = tmp_path / "test_optical.png"
    before_path = tmp_path / "test_before.png"
    sar_path = tmp_path / "test_sar.png"

    # Create realistic test terrain image (256x256)
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:128, :, 1] = 160  # Green canopy
    arr[128:, :128, 0] = 180  # Built-up texture
    arr[128:, :128, 1] = 180
    arr[128:, :128, 2] = 180
    arr[128:, 128:, 2] = 190  # Water body
    arr[128:, 128:, 1] = 100
    Image.fromarray(arr).save(str(opt_path))

    # Create baseline image
    arr_b = arr.copy()
    arr_b[128:, :128, :] = [80, 140, 60]
    Image.fromarray(arr_b).save(str(before_path))

    # Create SAR grayscale image
    sar_arr = np.full((256, 256), 110, dtype=np.uint8)
    sar_arr[128:, :128] = 220
    sar_arr[128:, 128:] = 25
    Image.fromarray(sar_arr).save(str(sar_path))

    return {
        "optical": str(opt_path),
        "before": str(before_path),
        "sar": str(sar_path),
        "geo_bbox": [77.54, 13.00, 77.55, 13.01]
    }


def _dummy_gemini_findings(task: str, raster_path: str) -> StructuredAIFindings:
    return StructuredAIFindings(
        task=task,
        model_used="Gemini 2.5 Flash",
        device_used="Cloud TPU / Google AI API",
        summary="Observation summary registered.",
        confidence_score=0.94,
        confidence_rating="High",
        primary_image_path=raster_path,
        evidence_path=raster_path,
        observations=["Vegetation canopy dominant in northern sector."],
        spatial_findings=["Water reservoir localized in southeast."],
        uncertainties=["Minimal atmospheric attenuation."],
        land_cover=[
            LandCoverItem(class_name="Canopy", coverage_pct=50.0, confidence=0.95),
            LandCoverItem(class_name="Water", coverage_pct=25.0, confidence=0.92),
            LandCoverItem(class_name="Built-up", coverage_pct=25.0, confidence=0.90)
        ],
        changes=[
            TemporalChangeItem(change_type="Built-up Expansion", description="New structures detected.", confidence=0.92)
        ],
        raw_model_metrics={"cloud_cover": 0.05}
    )


def test_model_router_rejects_non_gemini_provider(sample_rasters):
    """Enforces that AI_PROVIDER='local' or any non-gemini provider is rejected with ValueError."""
    orig = settings.AI_PROVIDER
    try:
        settings.AI_PROVIDER = "local"
        with pytest.raises(ValueError, match="Unsupported AI_PROVIDER 'local'"):
            model_router.route_and_execute(
                task="Single-Image VQA",
                primary_image_path=sample_rasters["optical"],
                query="Test query",
                aoi={"bbox": sample_rasters["geo_bbox"]}
            )
    finally:
        settings.AI_PROVIDER = orig


@pytest.mark.asyncio
async def test_model_router_dispatches_single_vqa_and_grounding(sample_rasters):
    """Verifies that single-image VQA and Grounding dispatch cleanly to gemini_provider."""
    findings_dummy = _dummy_gemini_findings("Single-Image VQA", sample_rasters["optical"])

    with patch.object(gemini_provider, "analyze_image", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = findings_dummy

        # 1. Single-Image VQA
        f_vqa = await model_router.route_and_execute_async(
            task="Single-Image VQA",
            primary_image_path=sample_rasters["optical"],
            query="Describe the land cover",
            aoi={"bbox": sample_rasters["geo_bbox"]},
            analysis_id="TEST-VQA-DISPATCH"
        )
        assert f_vqa.task == "Single-Image VQA"
        mock_gemini.assert_called_once()

        # 2. Grounding
        mock_gemini.reset_mock()
        f_grd = await model_router.route_and_execute_async(
            task="Grounding",
            primary_image_path=sample_rasters["optical"],
            query="Locate the reservoir",
            aoi={"bbox": sample_rasters["geo_bbox"]},
            analysis_id="TEST-GRD-DISPATCH"
        )
        assert f_grd.task == "Grounding"
        mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_model_router_dispatches_temporal_change(sample_rasters):
    """Verifies that Bi-Temporal Change dispatches cleanly to gemini_provider.analyze_temporal_pair."""
    findings_dummy = _dummy_gemini_findings("Bi-Temporal Change", sample_rasters["optical"])

    with patch.object(gemini_provider, "analyze_temporal_pair", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = findings_dummy

        f_change = await model_router.route_and_execute_async(
            task="Bi-Temporal Change",
            primary_image_path=sample_rasters["optical"],
            before_image_path=sample_rasters["before"],
            query="Detect changes between seasons",
            aoi={"bbox": sample_rasters["geo_bbox"]},
            analysis_id="TEST-CHG-DISPATCH"
        )
        assert f_change.task == "Bi-Temporal Change"
        mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_model_router_dispatches_optical_sar(sample_rasters):
    """Verifies that Optical + SAR Fusion dispatches cleanly to gemini_provider.analyze_multimodal_optical_sar."""
    findings_dummy = _dummy_gemini_findings("Optical-SAR Fusion", sample_rasters["optical"])

    with patch.object(gemini_provider, "analyze_multimodal_optical_sar", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = findings_dummy

        f_sar = await model_router.route_and_execute_async(
            task="Optical + SAR Fusion",
            primary_image_path=sample_rasters["optical"],
            sar_image_path=sample_rasters["sar"],
            query="Correlate radar backscatter with optical reflectance",
            aoi={"bbox": sample_rasters["geo_bbox"]},
            analysis_id="TEST-SAR-DISPATCH"
        )
        assert f_sar.task == "Optical-SAR Fusion"
        mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_model_router_temporal_requires_before_image(sample_rasters):
    """Verifies that Bi-Temporal Change requires before_image_path."""
    with pytest.raises(ValueError, match="Bi-temporal change analysis requires both baseline"):
        await model_router.route_and_execute_async(
            task="Bi-Temporal Change",
            primary_image_path=sample_rasters["optical"],
            before_image_path=None,
            query="Detect changes",
            analysis_id="TEST-CHG-FAIL"
        )


@pytest.mark.asyncio
async def test_model_router_sar_requires_sar_image(sample_rasters):
    """Verifies that Optical + SAR Fusion requires genuine sar_image_path."""
    with pytest.raises(SARUnavailableError, match="Optical \\+ SAR fusion analysis requires both optical and genuine SAR"):
        await model_router.route_and_execute_async(
            task="Optical + SAR Fusion",
            primary_image_path=sample_rasters["optical"],
            sar_image_path=None,
            query="Verify radar consensus",
            analysis_id="TEST-SAR-FAIL"
        )


def test_pdf_report_with_ai_findings(sample_rasters):
    """Verifies that ReportLab generates a valid, publication-grade PDF from AI findings."""
    analysis_dict = {
        "analysis_id": "AN-AI-REPORT-TEST",
        "task": "Single-Image VQA",
        "input": "Single image",
        "query": "Identify major terrain features and surface water bodies.",
        "answer": "Deep visual embeddings confirm predominant agricultural canopy with distinct open water reservoirs in the south-east quadrant.",
        "date": "2026-09-20",
        "time": "19:45",
        "confidence": "High",
        "confidence_score": 0.89,
        "model_used": "Gemini 2.5 Flash",
        "device_used": "Cloud TPU / Google AI API",
        "primary_image_path": sample_rasters["optical"],
        "evidence_path": sample_rasters["optical"],
        "observations": [
            "Dominant canopy signature detected across 48.5% of visual extent.",
            "Water absorption boundary clearly delineated in south-east sector."
        ],
        "uncertainties": [
            "Minor cloud shadow at northern perimeter may affect local spectral contrast."
        ],
        "aoi": {
            "bbox": sample_rasters["geo_bbox"],
            "area_sq_km": 1.25
        },
        "execution_trace": [
            {"name": "Input validation", "detail": "CRS verified", "duration": "0.10s"},
            {"name": "AI Model Inference", "detail": "Gemini 2.5 Flash multispectral reasoning", "duration": "0.45s"},
            {"name": "Evidence generation", "detail": "Visual evidence map generated", "duration": "0.05s"}
        ]
    }

    report = report_generator.generate_report_artifacts(analysis_dict)
    assert report is not None
    pdf_path = report.get("pdf_path")
    assert pdf_path and os.path.exists(pdf_path)
    assert report_generator.is_valid_pdf_file(pdf_path)
    assert os.path.getsize(pdf_path) > 5000
