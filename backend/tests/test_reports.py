import os
import io
import re
import json
from pathlib import Path
import pypdf
from fastapi.testclient import TestClient
from app.main import app
from app.services.report_generator import report_generator
from app.core.db import db
from app.core.config import settings
from app.core.firebase import get_current_user

client = TestClient(app)

def get_auth_header():
    return {"Authorization": "Bearer dev-token-dev_user_earth_analyst_01"}

def test_1_generate_pdf_and_json_on_backend():
    """TEST 1 & TEST 5: Generate PDF and JSON on backend, verify validity."""
    sample_analysis = {
        "analysis_id": "AN-ACCEPT-01",
        "uid": "dev_user_earth_analyst_01",
        "query": "Assess water surface area and urban density along the river corridor.",
        "task": "Single-Image VQA",
        "input": "Single image",
        "date": "2026-09-19",
        "time": "10:00",
        "confidence": "High",
        "confidence_score": 0.94,
        "confidence_basis": "Dual spectral alignment",
        "agreements": [{"label": "Spectral", "state": "agree"}],
        "answer": "Clear open reservoir identified with distinct boundary and high spectral clarity.",
        "observed_evidence": "Low SWIR/NIR reflectance confirms water body boundary.",
        "model_interpretation": "Multi-band radiometric decomposition confirms water boundary.",
        "model_used": "RemoteSensing Vision-Language Engine",
        "device_used": "CPU",
        "aoi": {"bbox": [78.46, 17.41, 78.49, 17.44], "area_sq_km": 10.58},
        "execution_trace": [
            {"name": "Input validation", "detail": "Pair co-registered", "duration": "0.15s"},
            {"name": "Model inference", "detail": "Spectral Analysis on CPU", "duration": "0.22s"}
        ]
    }

    rep = report_generator.generate_report_artifacts(sample_analysis)
    assert rep["report_id"] == "REP-ACCEPT-01"
    
    # 1. PDF Verification
    pdf_path = Path(rep["pdf_path"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
    assert report_generator.is_valid_pdf_file(str(pdf_path))
    
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1
    page1_text = reader.pages[0].extract_text()
    assert "Satya Dristi" in page1_text
    assert "EXECUTIVE RESULT" in page1_text

    # 2. JSON Verification
    json_path = Path(rep["json_path"])
    assert json_path.exists()
    assert report_generator.is_valid_json_file(str(json_path))
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["report_id"] == "REP-ACCEPT-01"
        assert data["analysis_id"] == "AN-ACCEPT-01"
        assert data["product"] == "Satya Dristi"
        assert "execution_trace" in data

def test_2_and_3_and_4_download_pdf_from_api():
    """TEST 2, 3, 4: Download PDF directly from API, verify valid bytes, opens normally, proper filename."""
    headers = get_auth_header()
    res = client.get("/api/v1/reports/REP-ACCEPT-01/download", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    
    # Header checks
    content_type = res.headers.get("content-type", "")
    assert "application/pdf" in content_type, f"Content-Type was {content_type}"
    
    disposition = res.headers.get("content-disposition", "")
    assert "attachment" in disposition, f"Content-Disposition missing attachment: {disposition}"
    
    match = re.search(r'filename="([^"]+)"', disposition)
    assert match, f"Content-Disposition missing quoted filename: {disposition}"
    filename = match.group(1)
    assert filename.endswith(".pdf"), f"Filename does not end with .pdf: {filename}"
    assert filename.startswith("Satya_Dristi_Analysis_"), f"Filename missing prefix: {filename}"
    assert not re.match(r'^[0-9a-f-]{36}\.pdf$', filename, re.I), f"Filename is bare UUID: {filename}"

    # Byte checks
    raw = res.content
    assert len(raw) > 1000, "Downloaded PDF body is too small"
    assert raw[:5] == b"%PDF-", f"PDF does not start with %PDF- header: {raw[:10]}"

    # Open with PDF parser (TEST 3)
    reader = pypdf.PdfReader(io.BytesIO(raw))
    assert len(reader.pages) >= 1
    extracted_text = reader.pages[0].extract_text()
    assert "Satya Dristi" in extracted_text

def test_6_and_7_download_json_from_api():
    """TEST 6, 7: Download JSON from API, verify valid JSON, opens/parses, proper filename."""
    headers = get_auth_header()
    res = client.get("/api/v1/reports/REP-ACCEPT-01/json", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    content_type = res.headers.get("content-type", "")
    assert "application/json" in content_type, f"Content-Type was {content_type}"

    disposition = res.headers.get("content-disposition", "")
    assert "attachment" in disposition
    match = re.search(r'filename="([^"]+)"', disposition)
    assert match
    filename = match.group(1)
    assert filename.endswith(".json")
    assert filename.startswith("Satya_Dristi_Analysis_")

    data = json.loads(res.content.decode("utf-8"))
    assert data["product"] == "Satya Dristi"
    assert data["report_id"] == "REP-ACCEPT-01"
    assert "query" in data
    assert "answer" in data
    assert "confidence" in data

def test_10_unauthorized_and_forbidden_access():
    """TEST 10: Unauthorized or non-owner user cannot download reports."""
    # 1. Test 403 Forbidden when authenticated user does not own the report
    other_report = {
        "analysis_id": "AN-PRIVATE-99",
        "uid": "victim_user_999",
        "query": "Classified survey area",
        "task": "Single-Image VQA",
        "input": "Single image",
        "date": "2026-09-19",
        "answer": "Private analysis answer."
    }
    rep = report_generator.generate_report_artifacts(other_report)

    # Override current_user to simulate non-dev user who is NOT the owner
    app.dependency_overrides[get_current_user] = lambda: {
        "uid": "attacker_user_888",
        "email": "attacker@example.com",
        "name": "Attacker",
        "picture": "",
        "is_dev": False
    }

    try:
        # PDF download must fail with 403 Forbidden
        pdf_res = client.get(f"/api/v1/reports/{rep['report_id']}/download")
        assert pdf_res.status_code == 403, f"Expected 403 Forbidden, got {pdf_res.status_code}"
        assert pdf_res.headers["content-type"].startswith("application/json")
        err = pdf_res.json()
        assert err["code"] == "FORBIDDEN"

        # JSON download must fail with 403 Forbidden
        json_res = client.get(f"/api/v1/reports/{rep['report_id']}/json")
        assert json_res.status_code == 403
        assert json_res.headers["content-type"].startswith("application/json")
        assert json_res.json()["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # 2. Test 401 Unauthorized when no credentials provided and in non-dev mode
    old_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    try:
        pdf_no_auth = client.get(f"/api/v1/reports/{rep['report_id']}/download")
        assert pdf_no_auth.status_code == 401, f"Expected 401 Unauthorized, got {pdf_no_auth.status_code}"
        assert pdf_no_auth.headers["content-type"].startswith("application/json")
        assert not pdf_no_auth.content.startswith(b"%PDF-")
    finally:
        settings.ENVIRONMENT = old_env

def test_regression_http_error_never_downloaded_as_pdf():
    """Verify that 404 or 500 error returns JSON error payload and never application/pdf."""
    headers = get_auth_header()
    res = client.get("/api/v1/reports/NON_EXISTENT_REP_9999/download", headers=headers)
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert not res.content.startswith(b"%PDF-")
    body = res.json()
    assert "NOT_FOUND" in body.get("code", "")
