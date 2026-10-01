import os
import json
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.core.errors import (
    AIAuthenticationError,
    AIServiceUnavailableError,
    AIQuotaExceededError,
    SARUnavailableError,
    PayloadTooLargeError,
)
from app.models.base_model import StructuredAIFindings, GroundedObject
from app.models.gemini_provider import (
    GeminiProvider,
    GeminiAnalysisOutput,
    GeminiObjectDetection,
    GeminiTemporalChange,
    GeminiLandCoverClass,
    gemini_provider,
)
from app.models.router import model_router

@pytest.fixture
def mock_gemini_response_data():
    return {
        "summary": "High-resolution satellite observation reveals a prominent water reservoir surrounded by urban development.",
        "executive_narrative": "Multispectral analysis indicates stable hydrological surface area with significant surrounding urban density. Chlorophyll reflectance suggests healthy littoral vegetation.",
        "observations": [
            "Centrally located freshwater reservoir exhibiting deep spectral absorption.",
            "High spatial concentration of geometric built-up structures along eastern perimeter.",
            "Healthy vegetation canopy corridors identified along northern edge."
        ],
        "objects": [
            {
                "label": "Water Reservoir",
                "box_2d": [200, 300, 600, 700],
                "confidence": 0.96,
                "description": "Primary water body with distinct boundary"
            },
            {
                "label": "Urban Cluster",
                "box_2d": [100, 100, 350, 400],
                "confidence": 0.89,
                "description": "High-density residential structures"
            }
        ],
        "land_cover": [
            {"class_name": "Surface Water", "coverage_pct": 34.5, "confidence": 0.98},
            {"class_name": "Urban Built-up", "coverage_pct": 42.1, "confidence": 0.92},
            {"class_name": "Vegetation", "coverage_pct": 23.4, "confidence": 0.90}
        ],
        "changes": [
            {
                "change_type": "Urban Expansion",
                "description": "New construction and concrete surfaces detected in northwestern sector",
                "box_2d": [50, 50, 200, 250],
                "confidence": 0.91
            }
        ],
        "spatial_findings": [
            "Linear infrastructure buffer along southeastern shoreline",
            "Radial road network converging toward urban core"
        ],
        "uncertainties": [
            "Atmospheric haze partially attenuates blue band reflectance in southern quadrant",
            "Spatial resolution limits individual cadastral boundary delineation"
        ],
        "confidence_score": 0.94,
        "confidence_rating": "High"
    }

@pytest.fixture
def test_images(tmp_path):
    opt_path = tmp_path / "opt.png"
    before_path = tmp_path / "before.png"
    sar_path = tmp_path / "sar.png"

    # Create dummy images
    Image.new("RGB", (256, 256), color=(40, 120, 60)).save(str(opt_path))
    Image.new("RGB", (256, 256), color=(80, 140, 70)).save(str(before_path))
    Image.new("RGB", (256, 256), color=(110, 110, 110)).save(str(sar_path))

    return {
        "optical": str(opt_path),
        "before": str(before_path),
        "sar": str(sar_path),
        "geo_bbox": [78.46, 17.41, 78.49, 17.44]
    }

@pytest.mark.asyncio
async def test_gemini_missing_api_key(test_images, monkeypatch):
    """Verifies that attempting inference without GEMINI_API_KEY raises AIAuthenticationError."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = GeminiProvider()
    with pytest.raises(AIAuthenticationError) as excinfo:
        await provider.analyze_image(
            image_path=test_images["optical"],
            query="Analyze water body",
            aoi_metadata={"bbox": test_images["geo_bbox"]}
        )
    assert "GEMINI_API_KEY" in str(excinfo.value)

@pytest.mark.asyncio
async def test_gemini_single_image_vqa_and_grounding(test_images, mock_gemini_response_data, monkeypatch):
    """Verifies single image VQA, scene reasoning, and bounding-box reprojection."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-key-12345")

    provider = GeminiProvider()

    # Mock client and generate_content
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_response_data)
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    findings = await provider.analyze_image(
        image_path=test_images["optical"],
        query="Identify the water reservoir and urban areas.",
        aoi_metadata={"bbox": test_images["geo_bbox"]},
        analysis_id="TEST-GEMINI-01"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Single-Image VQA & Scene Understanding"
    assert "water reservoir" in findings.summary.lower()
    assert len(findings.observations) == 3
    assert len(findings.land_cover) == 3
    assert len(findings.objects) == 2

    # Verify bounding box coordinate translation:
    # First object: box_2d = [200, 300, 600, 700]
    obj1 = findings.objects[0]
    assert obj1.label == "Water Reservoir"
    # UI normalized scale: x=30.0, y=20.0, w=40.0, h=40.0
    assert obj1.bbox_norm == [30.0, 20.0, 40.0, 40.0]
    # WGS84 geographic bbox: [min_lon, min_lat, max_lon, max_lat]
    assert obj1.bbox_geo is not None
    assert len(obj1.bbox_geo) == 4
    assert obj1.bbox_geo[0] >= test_images["geo_bbox"][0]
    assert obj1.bbox_geo[2] <= test_images["geo_bbox"][2]
    # Calculated physical area in sq km > 0
    assert obj1.area_sq_km is not None
    assert obj1.area_sq_km > 0.0

    # Verify visual evidence overlay generated
    assert findings.evidence_path is not None
    assert os.path.exists(findings.evidence_path)

@pytest.mark.asyncio
async def test_gemini_bi_temporal_change(test_images, mock_gemini_response_data, monkeypatch):
    """Verifies bi-temporal change reasoning with before and after rasters."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-key-12345")

    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_response_data)
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    findings = await provider.analyze_temporal_pair(
        before_image_path=test_images["before"],
        after_image_path=test_images["optical"],
        query="What changed between baseline and target rasters?",
        aoi_metadata={"bbox": test_images["geo_bbox"]},
        analysis_id="TEST-GEMINI-CHG"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Bi-Temporal Change Analysis"
    assert len(findings.changes) == 1
    assert findings.changes[0].change_type == "Urban Expansion"
    assert os.path.exists(findings.evidence_path)

@pytest.mark.asyncio
async def test_gemini_optical_sar_fusion(test_images, mock_gemini_response_data, monkeypatch):
    """Verifies multimodal optical+SAR cross-sensor analysis."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-key-12345")

    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_response_data)
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    findings = await provider.analyze_multimodal_optical_sar(
        optical_image_path=test_images["optical"],
        sar_image_path=test_images["sar"],
        query="Cross-examine water boundary with SAR backscatter.",
        aoi_metadata={"bbox": test_images["geo_bbox"]},
        analysis_id="TEST-GEMINI-FUS"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Optical + SAR Cross-Modal Reasoning"
    assert "Cross-modal verification" in findings.observed_evidence

@pytest.mark.asyncio
async def test_gemini_sar_unavailable_enforcement(test_images, monkeypatch):
    """Verifies that attempting multimodal optical+SAR without genuine SAR raises SARUnavailableError."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-key-12345")
    provider = GeminiProvider()

    with pytest.raises(SARUnavailableError) as excinfo:
        await provider.analyze_multimodal_optical_sar(
            optical_image_path=test_images["optical"],
            sar_image_path=None,  # Missing genuine SAR
            query="Analyze optical and SAR"
        )
    assert "SAR_UNAVAILABLE" in str(excinfo.value)

@pytest.mark.asyncio
async def test_gemini_quota_error_handling(test_images, monkeypatch):
    """Verifies rate limit / quota error translates to AIQuotaExceededError."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-key-12345")
    provider = GeminiProvider()

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("ResourceExhausted: 429 Quota exceeded")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises((AIQuotaExceededError, AIServiceUnavailableError)) as excinfo:
        await provider.analyze_image(
            image_path=test_images["optical"],
            query="Analyze water body"
        )
    assert "AI_QUOTA_EXCEEDED" in str(excinfo.value) or "AI_SERVICE_UNAVAILABLE" in str(excinfo.value)
