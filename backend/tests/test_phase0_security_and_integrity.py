import os
import uuid
import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.firebase import get_current_user
from app.core.db import db
from app.models.optical_sar_specialist import optical_sar_specialist
from app.services.report_generator import report_generator
from app.core.config import settings

client = TestClient(app)

USER_A = {"uid": "user_alpha_111", "email": "alpha@example.com", "name": "User Alpha", "is_dev": False}
USER_B = {"uid": "user_bravo_222", "email": "bravo@example.com", "name": "User Bravo", "is_dev": False}

def test_p0_logged_out_cannot_access_protected_endpoints():
    """Requirement: Logged-out user cannot access protected reports/evidence."""
    app.dependency_overrides.clear()
    
    # 1. Reports listing
    res = client.get("/api/v1/reports")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # 2. Evidence
    res = client.get("/api/v1/analyses/AN-SOMEID/evidence")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # 3. Trace
    res = client.get("/api/v1/analyses/AN-SOMEID/trace")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # 4. History
    res = client.get("/api/v1/history")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

def test_p0_unauthenticated_static_mounts_removed():
    """Requirement: Remove unauthenticated static access to /evidence and /reports."""
    res = client.get("/static/evidence/test.png")
    assert res.status_code == 404, f"Expected 404 for removed static mount, got {res.status_code}"

    res = client.get("/static/reports/test.pdf")
    assert res.status_code == 404, f"Expected 404 for removed static mount, got {res.status_code}"

def test_p0_user_a_cannot_access_user_b_analysis():
    """Requirement: User A cannot access User B's analysis, evidence, or trace."""
    b_aid = f"AN-{uuid.uuid4().hex.upper()}"
    test_img = settings.EVIDENCE_DIR / f"test_ev_{b_aid}.png"
    Image.new("RGB", (64, 64), color="blue").save(test_img)
    
    doc = {
        "analysis_id": b_aid,
        "uid": USER_B["uid"],
        "task": "Single-Image VQA",
        "input": "Single image",
        "date": "2026-09-19",
        "time": "12:00",
        "confidence": "High",
        "status": "Complete",
        "answer": "Classified area answer.",
        "created_at": "2026-09-19T12:00:00Z",
        "query": "Classified area",
        "evidence_path": str(test_img),
        "execution_trace": [{"name": "Step 1", "duration": "0.1s"}]
    }
    db.save_analysis(doc)

    app.dependency_overrides[get_current_user] = lambda: USER_A
    try:
        # Analysis metadata
        res = client.get(f"/api/v1/analyses/{b_aid}")
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

        # Analysis status
        res_st = client.get(f"/api/v1/analyses/{b_aid}/status")
        assert res_st.status_code == 403, f"Expected 403 Forbidden, got {res_st.status_code}"

        # Analysis visual evidence
        res_ev = client.get(f"/api/v1/analyses/{b_aid}/evidence")
        assert res_ev.status_code == 403, f"Expected 403 Forbidden, got {res_ev.status_code}"

        # Analysis trace
        res_tr = client.get(f"/api/v1/analyses/{b_aid}/trace")
        assert res_tr.status_code == 403, f"Expected 403 Forbidden, got {res_tr.status_code}"
    finally:
        app.dependency_overrides.clear()
        db.delete_analysis(b_aid, USER_B["uid"])
        if test_img.exists():
            test_img.unlink()

def test_p0_user_a_cannot_access_user_b_report():
    """Requirement: User A cannot access User B's report."""
    b_aid = f"AN-{uuid.uuid4().hex.upper()}"
    b_analysis = {
        "analysis_id": b_aid,
        "uid": USER_B["uid"],
        "query": "Confidential boundary scan",
        "task": "Single-Image VQA",
        "input": "Single image",
        "date": "2026-09-19",
        "time": "12:00",
        "confidence": "High",
        "status": "Complete",
        "answer": "Confidential answer.",
        "created_at": "2026-09-19T12:00:00Z"
    }
    rep = report_generator.generate_report_artifacts(b_analysis)
    rep["uid"] = USER_B["uid"]
    db.save_report(rep)

    app.dependency_overrides[get_current_user] = lambda: USER_A
    try:
        # Report detail
        res_det = client.get(f"/api/v1/reports/{rep['report_id']}")
        assert res_det.status_code == 403, f"Expected 403 Forbidden, got {res_det.status_code}"

        # Report PDF
        res_pdf = client.get(f"/api/v1/reports/{rep['report_id']}/download")
        assert res_pdf.status_code == 403, f"Expected 403 Forbidden, got {res_pdf.status_code}"

        # Report JSON
        res_json = client.get(f"/api/v1/reports/{rep['report_id']}/json")
        assert res_json.status_code == 403, f"Expected 403 Forbidden, got {res_json.status_code}"
    finally:
        app.dependency_overrides.clear()
        db.delete_analysis(b_aid, USER_B["uid"])

def test_p0_collision_resistant_analysis_ids():
    """Requirement: Replace truncated 8-character analysis IDs with collision-resistant IDs."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    try:
        res = client.post("/api/v1/analyses", json={
            "mode": "single",
            "query": "Test collision resistant ID",
            "aoi": {"bbox": [78.46, 17.41, 78.49, 17.44]}
        })
        assert res.status_code == 200
        aid = res.json()["analysis_id"]
        assert aid.startswith("AN-")
        raw_uuid = aid.replace("AN-", "")
        assert len(raw_uuid) == 32, f"Expected 32 hex chars, got {len(raw_uuid)}: {aid}"
    finally:
        app.dependency_overrides.clear()

def test_p0_invalid_aoi_produces_real_error():
    """Requirement: Invalid AOI produces a real error, no fabricated coords or area."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    try:
        # 1. Inverted bbox coordinates (min_lon > max_lon)
        res = client.post("/api/v1/earth/aoi/preview", json={
            "bbox": [80.0, 17.0, 70.0, 18.0]
        })
        assert res.status_code == 400
        err = res.json()
        assert err["code"] == "INVALID_AOI" or "invalid" in str(err).lower()

        # 2. Out of geographic range latitude (> 90 deg)
        res2 = client.post("/api/v1/earth/aoi/preview", json={
            "bbox": [78.0, 95.0, 79.0, 96.0]
        })
        assert res2.status_code == 400
    finally:
        app.dependency_overrides.clear()

def test_p0_optical_sar_confidence_dynamic(tmp_path):
    """Requirement: Optical/SAR confidence is not hardcoded and reflects actual computed evidence."""
    opt_path = tmp_path / "opt.png"
    sar_path = tmp_path / "sar.png"
    
    # 1. Matching pair: water reservoir in optical, matching specular low backscatter in SAR
    opt_arr = np.full((100, 100, 3), [60, 110, 40], dtype=np.uint8)
    opt_arr[30:70, 30:70] = [20, 60, 160] # water (blue dominant)
    Image.fromarray(opt_arr).save(opt_path)

    sar_arr = np.full((100, 100), 120, dtype=np.uint8)
    sar_arr[30:70, 30:70] = 30 # water specular reflection
    Image.fromarray(sar_arr).save(sar_path)

    res_matching = optical_sar_specialist.fuse_and_analyze(
        optical_path=str(opt_path),
        sar_path=str(sar_path),
        query="Verify water extent"
    )
    assert res_matching["confidence"] in ["High", "Moderate"]
    assert res_matching["agreements"][0]["state"] == "agree"

    # 2. Complete conflict: optical shows clear open water, but SAR exhibits intense double-bounce scatter
    opt_conflict = tmp_path / "opt_conflict.png"
    sar_conflict = tmp_path / "sar_conflict.png"
    opt_conflict_arr = np.full((100, 100, 3), [20, 60, 160], dtype=np.uint8) # 100% water in optical
    sar_conflict_arr = np.full((100, 100), 230, dtype=np.uint8) # 100% urban double bounce in SAR
    Image.fromarray(opt_conflict_arr).save(opt_conflict)
    Image.fromarray(sar_conflict_arr).save(sar_conflict)

    res_conflict = optical_sar_specialist.fuse_and_analyze(
        optical_path=str(opt_conflict),
        sar_path=str(sar_conflict),
        query="Verify water extent"
    )
    assert res_conflict["confidence"] == "Low"
    assert res_conflict["agreements"][2]["state"] == "conflict"
    assert res_conflict["confidence_score"] < res_matching["confidence_score"]

def test_p0_sample_records_isolated_per_user():
    """Requirement: Ensure demonstration/sample records cannot overwrite or leak across users."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    try:
        res_a = client.get("/api/v1/history")
        assert res_a.status_code == 200
        history_a = res_a.json()
        assert len(history_a) > 0
        aids_a = {item["analysis_id"] for item in history_a}
        for item in history_a:
            assert item["uid"] == USER_A["uid"]
    finally:
        app.dependency_overrides.clear()

    app.dependency_overrides[get_current_user] = lambda: USER_B
    try:
        res_b = client.get("/api/v1/history")
        assert res_b.status_code == 200
        history_b = res_b.json()
        assert len(history_b) > 0
        aids_b = {item["analysis_id"] for item in history_b}
        for item in history_b:
            assert item["uid"] == USER_B["uid"]
        
        # User A and User B must NOT share the same analysis IDs (no overwriting or collision)
        assert aids_a.isdisjoint(aids_b), "User A and User B sample records collided!"
    finally:
        app.dependency_overrides.clear()
