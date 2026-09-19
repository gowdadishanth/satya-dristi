import os
import io
import asyncio
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.db import db
from app.services.async_queue import job_manager
from app.models.grounding_specialist import grounding_specialist
from app.models.change_specialist import change_specialist
from app.models.optical_sar_specialist import optical_sar_specialist

client = TestClient(app)

DEV_HEADER_A = {"Authorization": "Bearer dev-token-analyst_alpha"}
DEV_HEADER_B = {"Authorization": "Bearer dev-token-analyst_beta"}

def create_dummy_png(color=(100, 150, 200), size=(128, 128)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_p1a_evidence_artifacts_unique_per_analysis():
    """
    CR-SEC-01: Two analyses using the same source image stem must produce
    different, isolated evidence directories and never overwrite each other.
    """
    stem_img = settings.CACHE_DIR / "identical_stem.png"
    stem_img.write_bytes(create_dummy_png((50, 100, 150)))

    aid_1 = "AN-TEST-EVIDENCE-001"
    aid_2 = "AN-TEST-EVIDENCE-002"

    res_1 = grounding_specialist.ground_feature(
        image_path=str(stem_img),
        query="locate water body",
        analysis_id=aid_1
    )
    res_2 = grounding_specialist.ground_feature(
        image_path=str(stem_img),
        query="locate water body",
        analysis_id=aid_2
    )

    path_1 = Path(res_1["mask_path"])
    path_2 = Path(res_2["mask_path"])

    assert path_1 != path_2, "Evidence paths must not collide!"
    assert aid_1 in str(path_1), f"Expected analysis ID '{aid_1}' in evidence path: {path_1}"
    assert aid_2 in str(path_2), f"Expected analysis ID '{aid_2}' in evidence path: {path_2}"
    assert path_1.is_file(), "Analysis 1 evidence file must exist"
    assert path_2.is_file(), "Analysis 2 evidence file must exist"

    # Cleanup
    if path_1.is_file():
        path_1.unlink()
    if path_2.is_file():
        path_2.unlink()
    if path_1.parent.is_dir():
        path_1.parent.rmdir()
    if path_2.parent.is_dir():
        path_2.parent.rmdir()

def test_p1a_evidence_endpoint_authorization_and_traversal_protection():
    """
    CR-SEC-01: User A cannot retrieve User B's evidence, and path traversal
    attacks (e.g. attempting to read outside EVIDENCE_DIR) are blocked.
    """
    test_aid = "AN-TEST-AUTH-EVID-01"
    evid_dir = settings.EVIDENCE_DIR / test_aid
    evid_dir.mkdir(parents=True, exist_ok=True)
    evid_file = evid_dir / "grounding.png"
    evid_file.write_bytes(create_dummy_png((80, 120, 160)))

    db.save_analysis({
        "analysis_id": test_aid,
        "uid": "analyst_alpha",
        "query": "Grounding verification",
        "task": "Grounding",
        "status": "Complete",
        "evidence_path": str(evid_file)
    })

    try:
        # Owner access succeeds
        res_a = client.get(f"/api/v1/analyses/{test_aid}/evidence", headers=DEV_HEADER_A)
        assert res_a.status_code == 200, f"Owner should be able to retrieve evidence, got {res_a.status_code}"
        assert res_a.headers["content-type"] == "image/png"

        # Non-owner access is forbidden (403)
        res_b = client.get(f"/api/v1/analyses/{test_aid}/evidence", headers=DEV_HEADER_B)
        assert res_b.status_code == 403, f"Non-owner should get 403 Forbidden, got {res_b.status_code}"

        # Unauthenticated access is rejected (401)
        res_unauth = client.get(f"/api/v1/analyses/{test_aid}/evidence")
        assert res_unauth.status_code == 401

        # Tampered traversal path must be blocked
        db.save_analysis({
            "analysis_id": test_aid,
            "uid": "analyst_alpha",
            "query": "Path traversal attempt",
            "task": "Grounding",
            "status": "Complete",
            "evidence_path": str(settings.BASE_DIR / "README.md")
        })
        res_trav = client.get(f"/api/v1/analyses/{test_aid}/evidence", headers=DEV_HEADER_A)
        assert res_trav.status_code == 403, f"Path outside EVIDENCE_DIR must return 403 Forbidden, got {res_trav.status_code}"

    finally:
        db.delete_analysis(test_aid, "analyst_alpha")
        if evid_file.is_file():
            evid_file.unlink()
        if evid_dir.is_dir():
            evid_dir.rmdir()

def test_p1a_streamed_upload_valid_single_image():
    """
    CR-STAB-01: Valid single remote sensing image upload succeeds through streamed ingestion.
    """
    img_bytes = create_dummy_png((120, 180, 240), size=(64, 64))
    files = {"image": ("test_scene.png", img_bytes, "image/png")}
    data = {"mode": "single", "query": "Analyze water features"}

    res = client.post("/api/v1/analyses/upload", data=data, files=files, headers=DEV_HEADER_A)
    assert res.status_code == 200, f"Upload should succeed with 200, got {res.status_code}: {res.text}"
    json_data = res.json()
    assert "analysis_id" in json_data
    aid = json_data["analysis_id"]

    # Verify upload was scoped to an analysis-specific upload directory
    upload_dir = settings.UPLOADS_DIR / aid
    assert upload_dir.is_dir(), f"Expected scoped upload directory for {aid}"
    uploaded_files = list(upload_dir.iterdir())
    assert len(uploaded_files) == 1
    assert "image_test_scene" in uploaded_files[0].name

    # Cleanup
    db.delete_analysis(aid, "analyst_alpha")

def test_p1a_streamed_upload_rejects_oversized_file():
    """
    CR-STAB-01: File exceeding MAX_UPLOAD_BYTES is rejected with HTTP 413 (Payload Too Large).
    """
    # Temporarily set max upload bytes to 10 KB to test limit enforcement cleanly
    orig_max = settings.MAX_UPLOAD_BYTES
    settings.MAX_UPLOAD_BYTES = 10 * 1024  # 10 KB
    try:
        oversized_bytes = b"X" * (15 * 1024)  # 15 KB
        files = {"image": ("huge_raster.png", oversized_bytes, "image/png")}
        data = {"mode": "single", "query": "Process huge raster"}

        res = client.post("/api/v1/analyses/upload", data=data, files=files, headers=DEV_HEADER_A)
        assert res.status_code == 413, f"Expected 413 Payload Too Large, got {res.status_code}: {res.text}"
        assert "PAYLOAD_TOO_LARGE" in res.text
    finally:
        settings.MAX_UPLOAD_BYTES = orig_max

def test_p1a_streamed_upload_rejects_unsupported_extension():
    """
    CR-STAB-01: Files with unsupported formats (e.g. .exe, .sh, .pdf) are rejected with HTTP 422.
    """
    fake_script = b"echo 'malicious payload'"
    files = {"image": ("script.sh", fake_script, "application/x-sh")}
    data = {"mode": "single", "query": "Test invalid upload"}

    res = client.post("/api/v1/analyses/upload", data=data, files=files, headers=DEV_HEADER_A)
    assert res.status_code == 422, f"Expected 422 for unsupported file type, got {res.status_code}"
    assert "Unsupported file format" in res.text

def test_p1a_streamed_upload_cleanup_on_total_limit_failure():
    """
    CR-STAB-01: When multi-file upload exceeds cumulative MAX_TOTAL_UPLOAD_BYTES,
    HTTP 413 is raised and partially written files are cleaned up.
    """
    orig_total_max = settings.MAX_TOTAL_UPLOAD_BYTES
    settings.MAX_TOTAL_UPLOAD_BYTES = 25 * 1024  # 25 KB total
    try:
        file1 = create_dummy_png((10, 20, 30), size=(64, 64))  # ~2 KB
        file2 = b"Y" * (30 * 1024)  # 30 KB
        files = [
            ("before", ("before.png", file1, "image/png")),
            ("after", ("after.png", file2, "image/png"))
        ]
        data = {"mode": "temporal", "query": "Detect change"}

        res = client.post("/api/v1/analyses/upload", data=data, files=files, headers=DEV_HEADER_A)
        assert res.status_code == 413, f"Expected 413 for total upload exceeding limit, got {res.status_code}"
    finally:
        settings.MAX_TOTAL_UPLOAD_BYTES = orig_total_max

def test_p1a_background_task_strong_reference_tracking():
    """
    CR-STAB-02: AnalysisJobManager must store strong reference in self._tasks
    while task is running and discard it upon completion.
    """
    aid = "AN-TEST-TASK-REF-01"
    assert hasattr(job_manager, "_tasks"), "AnalysisJobManager must have _tasks set"
    initial_tasks_count = len(job_manager._tasks)

    # Use dummy image
    dummy_img = settings.CACHE_DIR / "dummy_task_ref.png"
    dummy_img.write_bytes(create_dummy_png((200, 210, 220)))

    # Run async job
    async def run_test():
        await job_manager.start_analysis_job(
            analysis_id=aid,
            uid="analyst_alpha",
            mode="single",
            query="Count structures",
            file_paths={"Image": str(dummy_img)}
        )
        # Verify task was registered
        assert len(job_manager._tasks) >= initial_tasks_count + 1, "Task must be added to _tasks"

        # Wait for completion (small local task runs quickly)
        for _ in range(30):
            await asyncio.sleep(0.1)
            status_info = job_manager.get_job_status(aid)
            if status_info and status_info["status"] in ["completed", "failed"]:
                break

        # Give done callbacks time to fire
        await asyncio.sleep(0.05)
        # Task should have been discarded from _tasks
        return len(job_manager._tasks)

    final_count = asyncio.run(run_test())

    # Task should have finished and discarded itself from _tasks
    assert final_count == initial_tasks_count, f"Expected task to be discarded, count was {final_count}"

    # Cleanup
    db.delete_analysis(aid, "analyst_alpha")
