import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.async_queue import job_manager
from app.core.db import db
from app.services.report_generator import report_generator
from app.models.gemini_provider import (
    gemini_provider,
    GeminiAnalysisOutput,
    GeminiObjectDetection,
    GeminiLandCoverClass,
)

@pytest.mark.asyncio
async def test_full_analysis_workflow():
    uid = "test_e2e_user"
    aid = "AN-E2E-TEST"
    
    mock_output = GeminiAnalysisOutput(
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
        mock_call.return_value = mock_output
        # 1. Trigger asynchronous analysis job
        await job_manager.start_analysis_job(
            analysis_id=aid,
            uid=uid,
            mode="single",
            query="Describe the major land-cover types visible in this image.",
            aoi={"bbox": [78.46, 17.41, 78.49, 17.44], "geometry": None}
        )

        # 2. Poll until completed
        max_wait = 120
        status_res = None
        for _ in range(max_wait):
            await asyncio.sleep(0.5)
            status_res = job_manager.get_job_status(aid)
            if status_res and status_res["status"] in ["completed", "failed"]:
                break

    assert status_res is not None
    assert status_res["status"] == "completed", f"Job failed or timed out: {status_res}"

    # 3. Verify record in database
    doc = db.get_analysis(aid)
    assert doc is not None
    assert doc["task"] == "Single-Image VQA"
    assert doc["confidence"] in ["High", "Moderate", "Low", "Uncertain"]
    assert len(doc["answer"]) > 10
    assert len(doc["execution_trace"]) > 0

    # 4. Generate Report and verify PDF
    rep = report_generator.generate_report_artifacts(doc)
    assert rep["report_id"] is not None
    assert rep["pdf_path"] is not None
