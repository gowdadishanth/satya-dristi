import io
import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.db import db
from app.core.errors import (
    AIAuthenticationError,
    AIServiceUnavailableError,
    AIQuotaExceededError,
    AIRequestFailedError,
    AIInputTooLargeError,
    SARUnavailableError,
)
from app.models.base_model import StructuredAIFindings
from app.models.router import model_router
from app.models.gemini_provider import (
    gemini_provider,
    GeminiAnalysisOutput,
    GeminiObjectDetection,
    GeminiLandCoverClass,
    GeminiTemporalChange,
)
from app.services.image_retrieval import image_retrieval_service
from app.services.async_queue import job_manager
from app.services.report_generator import report_generator

client = TestClient(app)

def create_test_image(color=(120, 150, 180), size=(64, 64)) -> Path:
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = settings.CACHE_DIR / f"test_img_{size[0]}x{size[1]}.png"
    img = Image.new("RGB", size, color=color)
    img.save(p, format="PNG")
    return p

# --------------------------------------------------------------------------
# TEST 1: Gemini success -> Gemini result returned
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_1_gemini_success_returns_gemini_result():
    img_path = create_test_image()

    mock_gemini_output = GeminiAnalysisOutput(
        summary="Dominant open water body surrounded by dense agricultural canopy.",
        executive_narrative="Detailed spectral and spatial analysis of the target AOI reveals high surface water clarity.",
        observations=[
            "Low SWIR reflectance indicates clear open reservoir boundary.",
            "Elevated NDVI signatures along riparian fringes."
        ],
        objects=[
            GeminiObjectDetection(
                label="Water Reservoir",
                box_2d=[100, 150, 600, 850],
                confidence=0.96,
                description="Primary hydrological storage structure"
            )
        ],
        land_cover=[
            GeminiLandCoverClass(class_name="Surface Water", coverage_pct=62.5, confidence=0.95),
            GeminiLandCoverClass(class_name="Agricultural Canopy", coverage_pct=37.5, confidence=0.90)
        ],
        changes=[],
        spatial_findings=["Linear dam boundary running east-west."],
        uncertainties=["Minimal atmospheric haze observed in northwest sector."],
        confidence_score=0.94,
        confidence_rating="High"
    )

    with patch.object(gemini_provider, "_execute_gemini_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_gemini_output
        result = await model_router.route_and_execute_async(
            task="single",
            primary_image_path=str(img_path),
            query="Identify land cover features in this scene",
            aoi={"bbox": [78.4, 17.4, 78.5, 17.5]},
            analysis_id="AN-TEST-GEMINI-SUCCESS"
        )

        assert isinstance(result, StructuredAIFindings)
        assert result.summary == mock_gemini_output.summary
        assert result.confidence_score == 0.94
        assert result.confidence_rating == "High"
        assert len(result.observations) == 2
        assert result.observations[0] == "Low SWIR reflectance indicates clear open reservoir boundary."
        assert len(result.objects) == 1
        assert result.objects[0].label == "Water Reservoir"
        assert "gemini" in result.model_used.lower()

# --------------------------------------------------------------------------
# TEST 2: Gemini authentication failure -> analysis fails, no local fallback
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_2_gemini_auth_failure_fails_without_local_fallback():
    img_path = create_test_image()

    with patch.object(gemini_provider, "analyze_image", side_effect=AIAuthenticationError("Invalid API key")):
        with pytest.raises(AIAuthenticationError) as exc_info:
            await model_router.route_and_execute_async(
                task="single",
                primary_image_path=str(img_path),
                query="Locate built-up structures",
                analysis_id="AN-TEST-GEMINI-AUTH-FAIL"
            )
        
        assert "AI_AUTHENTICATION_ERROR" in str(exc_info.value.detail) or "Invalid API key" in str(exc_info.value)

# --------------------------------------------------------------------------
# TEST 3: Gemini API unavailable -> analysis fails, no local fallback
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_gemini_service_unavailable_fails_without_local_fallback():
    img_path = create_test_image()

    with patch.object(gemini_provider, "analyze_image", side_effect=AIServiceUnavailableError("503 Model Overloaded")):
        with pytest.raises(AIServiceUnavailableError) as exc_info:
            await model_router.route_and_execute_async(
                task="single",
                primary_image_path=str(img_path),
                query="Verify cloud cover",
                analysis_id="AN-TEST-GEMINI-UNAVAILABLE"
            )
        
        assert "AI_SERVICE_UNAVAILABLE" in str(exc_info.value.detail)

# --------------------------------------------------------------------------
# TEST 4: Gemini quota failure -> analysis fails, no local fallback
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_4_gemini_quota_failure_fails_without_local_fallback():
    img_path = create_test_image()

    with patch.object(gemini_provider, "analyze_temporal_pair", side_effect=AIQuotaExceededError("429 Resource exhausted")):
        with pytest.raises(AIQuotaExceededError) as exc_info:
            await model_router.route_and_execute_async(
                task="temporal",
                primary_image_path=str(img_path),
                before_image_path=str(img_path),
                query="Detect changes across seasons",
                analysis_id="AN-TEST-GEMINI-QUOTA"
            )
        
        assert "AI_QUOTA_EXCEEDED" in str(exc_info.value.detail)

# --------------------------------------------------------------------------
# TEST 5: SAR unavailable -> Optical + SAR returns SAR_UNAVAILABLE (no synthetic SAR)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_sar_unavailable_returns_sar_unavailable_no_synthesis():
    optical_path = create_test_image()
    
    # 1. Direct retrieval test: asking for SAR when scene is not genuine SAR raises SARUnavailableError
    with pytest.raises(SARUnavailableError) as exc_info:
        await image_retrieval_service.retrieve_scene_image(
            scene={"scene_id": "S2A_MSIL2A_TEST", "collection": "sentinel-2"},
            aoi_bbox=[78.4, 17.4, 78.5, 17.5],
            treatment="sar"
        )
    assert "SAR_UNAVAILABLE" in str(exc_info.value.detail)

    # 2. Async job test: optical+sar fusion job without genuine SAR scene fails with SAR_UNAVAILABLE
    await job_manager.start_analysis_job(
        analysis_id="AN-TEST-SAR-UNAVAIL-JOB",
        uid="analyst_test_user",
        mode="optical_sar",
        query="Analyze radar backscatter against optical canopy",
        file_paths={"Optical": str(optical_path)},
        optical_scene_id="S2A_MSIL2A_TEST",
        sar_scene_id=None  # No genuine SAR scene provided!
    )
    
    status_info = None
    for _ in range(40):
        await asyncio.sleep(0.05)
        status_info = job_manager.get_job_status("AN-TEST-SAR-UNAVAIL-JOB")
        if status_info and status_info["status"] in ["completed", "failed"]:
            break

    assert status_info is not None
    assert status_info["status"] == "failed"
    assert "SAR_UNAVAILABLE" in status_info.get("error", "") or "SAR" in status_info.get("error", "")

# --------------------------------------------------------------------------
# TEST 6: Frontend api.ts verification (mockService is NOT imported or called)
# --------------------------------------------------------------------------
def test_6_frontend_api_has_no_mock_fallback():
    api_ts_path = settings.BASE_DIR.parent / "src" / "lib" / "api.ts"
    assert api_ts_path.is_file(), f"api.ts must exist at {api_ts_path}"
    content = api_ts_path.read_text(encoding="utf-8")

    # Assert mockService is not imported
    assert "mockService" not in content, "api.ts must not reference or import mockService!"

    # Assert no auto-provisioning guest analyst token
    assert "signInAsGuest()" not in content, "api.ts must not auto-provision guest analyst tokens!"

# --------------------------------------------------------------------------
# TEST 7: No Firebase ID token -> 401 Unauthorized
# --------------------------------------------------------------------------
def test_7_no_firebase_token_returns_401():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Missing or malformed Authorization credentials" in res.text

    # Also on analysis endpoint
    res_analysis = client.post("/api/v1/analyses", json={"mode": "single", "query": "Test without token"})
    assert res_analysis.status_code == 401

# --------------------------------------------------------------------------
# TEST 8: Fake guest/dev token -> 401 Unauthorized
# --------------------------------------------------------------------------
def test_8_fake_guest_dev_tokens_rejected_401():
    fake_tokens = [
        "Bearer dev-token-guest_user",
        "Bearer dev-token-analyst_alpha",
        "Bearer test-token-123",
        "Bearer sd-jwt-1711234567-abcde",
        "Bearer guest-analyst-fake",
        "Bearer sd-token-fake"
    ]
    for auth_hdr in fake_tokens:
        res = client.get("/api/v1/auth/me", headers={"Authorization": auth_hdr})
        assert res.status_code == 401, f"Token '{auth_hdr}' must return 401 Unauthorized, got {res.status_code}"

# --------------------------------------------------------------------------
# TEST 9: Valid Firebase ID token -> authenticated request succeeds
# --------------------------------------------------------------------------
@patch("firebase_admin.auth.verify_id_token")
def test_9_valid_firebase_id_token_succeeds(mock_verify):
    mock_verify.return_value = {
        "uid": "google_uid_verified_12345",
        "email": "genuine.analyst@isro.gov.in",
        "name": "Dr. Genuine Analyst",
        "picture": "https://example.com/avatar.jpg"
    }

    # Standard 3-part valid JWT format
    valid_jwt = "header.eyJ1aWQiOiAiZ29vZ2xlX3VpZF92ZXJpZmllZF8xMjM0NSJ9.signature"
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {valid_jwt}"})
    assert res.status_code == 200
    data = res.json()
    assert data["uid"] == "google_uid_verified_12345"
    assert data["email"] == "genuine.analyst@isro.gov.in"
    assert data["name"] == "Dr. Genuine Analyst"

# --------------------------------------------------------------------------
# TEST 10: Successful Gemini analysis -> report contains actual Gemini findings
# --------------------------------------------------------------------------
def test_10_report_contains_actual_gemini_findings():
    gemini_summary = "High-precision Gemini satellite assessment: major reservoir volume stable at 84% capacity."
    gemini_observations = [
        "Primary embankment structure intact without deformation.",
        "Riparian zone demonstrates healthy chlorophyll absorption curves."
    ]

    analysis_doc = {
        "analysis_id": "AN-TEST-REPORT-GEMINI",
        "uid": "google_uid_verified_12345",
        "query": "Assess water level and structural integrity of the reservoir.",
        "task": "Single-Image VQA",
        "input": "Sentinel-2 MSI Level-2A",
        "date": "2026-09-30",
        "time": "14:30",
        "confidence": "High",
        "confidence_score": 0.95,
        "confidence_basis": "Gemini Multimodal Remote-Sensing Analysis",
        "agreements": [{"label": "Radiometric", "state": "agree"}],
        "answer": gemini_summary,
        "observed_evidence": "\n".join(f"• {obs}" for obs in gemini_observations),
        "model_interpretation": "Full multi-band spectrum analyzed via Google Gemini API.",
        "model_used": "Google Gemini API",
        "device_used": "Cloud TPU/GPU",
        "aoi": {"bbox": [78.46, 17.41, 78.49, 17.44], "area_sq_km": 12.34},
        "execution_trace": [
            {"name": "Scene Ingestion", "detail": "Level-2A BOA Surface Reflectance", "duration": "0.12s"},
            {"name": "Gemini Inference", "detail": "Structured Multimodal Vision Processing", "duration": "1.42s"}
        ]
    }

    rep = report_generator.generate_report_artifacts(analysis_doc)
    assert rep["report_id"] is not None
    assert rep["pdf_path"] is not None
    assert rep["json_path"] is not None

    # Verify JSON artifact contains the authentic Gemini findings
    with open(rep["json_path"], "r", encoding="utf-8") as f:
        json_data = json.load(f)
        assert json_data["answer"] == gemini_summary
        assert "Primary embankment structure intact" in json_data["observed_evidence"]
        assert json_data["confidence"]["level"] == "High"
        assert json_data["confidence"]["score"] == 0.95
        assert json_data["model_information"]["model_name"] == "Google Gemini API"

    # Verify PDF artifact contains the authentic Gemini findings
    import pypdf
    reader = pypdf.PdfReader(rep["pdf_path"])
    full_pdf_text = " ".join(page.extract_text() for page in reader.pages)
    assert "Satya Dristi" in full_pdf_text
    assert "major reservoir volume stable" in full_pdf_text
    assert "Google Gemini API" in full_pdf_text
