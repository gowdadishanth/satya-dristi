import pytest
import asyncio
from app.services.async_queue import job_manager
from app.core.db import db
from app.services.report_generator import report_generator

@pytest.mark.asyncio
async def test_full_analysis_workflow():
    uid = "test_e2e_user"
    aid = "AN-E2E-TEST"
    
    # 1. Trigger asynchronous analysis job
    await job_manager.start_analysis_job(
        analysis_id=aid,
        uid=uid,
        mode="single",
        query="Describe the major land-cover types visible in this image.",
        aoi={"bbox": [78.46, 17.41, 78.49, 17.44], "geometry": None}
    )

    # 2. Poll until completed
    max_wait = 50
    status_res = None
    for _ in range(max_wait):
        await asyncio.sleep(0.5)
        status_res = job_manager.get_job_status(aid)
        if status_res and status_res["status"] == "completed":
            break

    assert status_res is not None
    assert status_res["status"] == "completed", f"Job failed or timed out: {status_res}"

    # 3. Verify record in database
    doc = db.get_analysis(aid)
    assert doc is not None
    assert doc["task"] == "Single-Image VQA"
    assert doc["confidence"] in ["High", "Moderate", "Low"]
    assert len(doc["answer"]) > 10
    assert len(doc["execution_trace"]) > 0

    # 4. Generate Report and verify PDF
    rep = report_generator.generate_report_artifacts(doc)
    assert rep["report_id"] is not None
    assert rep["pdf_path"] is not None
