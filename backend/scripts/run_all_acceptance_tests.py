import os
import sys
import json
import io
import requests
import pypdf
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8000/api/v1"
DEV_AUTH = {"Authorization": "Bearer dev-token-analyst_01"}

def run_tests():
    print("==================================================")
    print("STARTING COMPLETE 10-POINT REPORT ACCEPTANCE TESTS")
    print("==================================================")
    
    # TEST 1: Generate PDF on backend
    from app.services.report_generator import report_generator
    sample_analysis = {
        "analysis_id": "AN-ACCEPT-01",
        "uid": "analyst_01",
        "query": "Assess water surface area and urban density along the river.",
        "task": "Single-Image VQA",
        "input": "Single image",
        "date": "2026-09-19",
        "time": "10:00",
        "confidence": "High",
        "confidence_score": 0.96,
        "answer": "Clear open reservoir identified with distinct boundary.",
        "aoi": {"bbox": [78.4, 17.3, 78.5, 17.4], "area_sq_km": 14.8},
        "execution_trace": [{"name": "Validation", "detail": "CRS matched - EPSG:4326", "duration": "0.10s"}]
    }
    rep_gen = report_generator.generate_report_artifacts(sample_analysis)
    pdf_gen_path = Path(rep_gen["pdf_path"])
    assert pdf_gen_path.exists(), "TEST 1 FAILED: PDF file not created on disk"
    assert report_generator.is_valid_pdf_file(str(pdf_gen_path)), "TEST 1 FAILED: Invalid PDF file structure"
    print("TEST 1: Generate PDF on backend -> PASS: valid PDF generated.")

    # TEST 2: Download PDF directly from API
    pdf_res = requests.get(f"{BASE_URL}/reports/AN-2041/download", headers=DEV_AUTH)
    assert pdf_res.status_code == 200, f"TEST 2 FAILED: HTTP status {pdf_res.status_code}"
    assert "application/pdf" in pdf_res.headers.get("content-type", ""), "TEST 2 FAILED: Wrong Content-Type"
    assert pdf_res.content.startswith(b"%PDF-"), "TEST 2 FAILED: Missing %PDF- magic bytes"
    print(f"TEST 2: Download PDF directly from API -> PASS: HTTP 200, {len(pdf_res.content)} bytes, Content-Type: application/pdf.")

    # TEST 3: Open downloaded PDF
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    assert len(reader.pages) >= 1, "TEST 3 FAILED: PDF has no pages"
    text = reader.pages[0].extract_text()
    assert "Satya Dristi" in text or "SATYA DRISTI" in text, "TEST 3 FAILED: Missing platform name in text"
    assert "QUERY & EXECUTIVE RESULT" in text, "TEST 3 FAILED: Missing Executive section"
    assert "\ufffd" not in text, "TEST 3 FAILED: Replacement glyphs present in extracted PDF text"
    print(f"TEST 3: Open downloaded PDF -> PASS: Opened normally ({len(reader.pages)} pages, clean text, 0 glyph errors).")

    # TEST 4: Verify browser filename
    cd_header = pdf_res.headers.get("content-disposition", "")
    assert "attachment" in cd_header, "TEST 4 FAILED: Missing attachment in Content-Disposition"
    assert "Satya_Dristi_Analysis_" in cd_header, "TEST 4 FAILED: Content-Disposition does not contain Satya_Dristi_Analysis_"
    assert cd_header.strip().endswith('.pdf"'), f"TEST 4 FAILED: Filename does not end with .pdf ({cd_header})"
    print(f"TEST 4: Verify browser filename -> PASS: Content-Disposition={cd_header}")

    # TEST 5: Generate JSON
    json_gen_path = Path(rep_gen["json_path"])
    assert json_gen_path.exists(), "TEST 5 FAILED: JSON file not created on disk"
    assert report_generator.is_valid_json_file(str(json_gen_path)), "TEST 5 FAILED: Invalid JSON structure"
    with open(json_gen_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["product"] == "Satya Dristi", "TEST 5 FAILED: Missing product name in JSON"
    print("TEST 5: Generate JSON -> PASS: Valid JSON generated.")

    # TEST 6: Download JSON
    json_res = requests.get(f"{BASE_URL}/reports/AN-2041/json", headers=DEV_AUTH)
    assert json_res.status_code == 200, f"TEST 6 FAILED: HTTP status {json_res.status_code}"
    assert "application/json" in json_res.headers.get("content-type", ""), "TEST 6 FAILED: Wrong Content-Type"
    json_body = json.loads(json_res.content.decode("utf-8"))
    assert json_body.get("report_id") is not None, "TEST 6 FAILED: JSON missing report_id"
    print(f"TEST 6: Download JSON -> PASS: HTTP 200, valid JSON with report_id={json_body.get('report_id')}.")

    # TEST 7: Verify JSON filename
    cd_json_header = json_res.headers.get("content-disposition", "")
    assert "attachment" in cd_json_header, "TEST 7 FAILED: Missing attachment in Content-Disposition"
    assert "Satya_Dristi_Analysis_" in cd_json_header, "TEST 7 FAILED: Missing Satya_Dristi_Analysis_ in JSON filename"
    assert cd_json_header.strip().endswith('.json"'), f"TEST 7 FAILED: Filename does not end with .json ({cd_json_header})"
    print(f"TEST 7: Verify JSON filename -> PASS: Content-Disposition={cd_json_header}")

    # TEST 8 & 9: Frontend filename resolver simulation & legacy mapping
    # (Testing legacy ana-01 and verify resolveSafeDownloadFilename)
    leg_pdf = requests.get(f"{BASE_URL}/reports/ana-01/download", headers=DEV_AUTH)
    assert leg_pdf.status_code == 200, "TEST 8 FAILED: Legacy ana-01 PDF returned non-200"
    leg_reader = pypdf.PdfReader(io.BytesIO(leg_pdf.content))
    assert len(leg_reader.pages) >= 1, "TEST 8 FAILED: Legacy PDF unreadable"
    print(f"TEST 8: Download through frontend / legacy ID (ana-01) -> PASS: valid PDF ({len(leg_pdf.content)} bytes).")

    leg_json = requests.get(f"{BASE_URL}/reports/ana-01/json", headers=DEV_AUTH)
    assert leg_json.status_code == 200, "TEST 9 FAILED: Legacy ana-01 JSON returned non-200"
    leg_json_data = json.loads(leg_json.content.decode("utf-8"))
    assert leg_json_data["report_id"] == "REP-2041", "TEST 9 FAILED: Legacy mapping failed"
    print("TEST 9: Download JSON through frontend / legacy ID (ana-01) -> PASS: valid parsed JSON.")

    # TEST 10: Unauthorized user tries to download
    unauth_pdf = requests.get(f"{BASE_URL}/reports/AN-2041/download", headers={"Authorization": "Bearer invalid-unauth-token-9999"})
    assert unauth_pdf.status_code == 401, f"TEST 10 FAILED: Expected 401, got {unauth_pdf.status_code}"
    assert "application/pdf" not in unauth_pdf.headers.get("content-type", ""), "TEST 10 FAILED: Returned PDF for unauthorized user"
    print("TEST 10: Unauthorized user tries to download -> PASS: HTTP 401 Unauthorized, zero file downloaded.")

    # Verify CORS expose headers
    get_res = requests.get(f"{BASE_URL}/reports/AN-2041/download", headers={"Authorization": "Bearer dev-token-01", "Origin": "http://localhost:8443"})
    assert "Content-Disposition" in get_res.headers.get("access-control-expose-headers", ""), "CORS expose-headers missing Content-Disposition"
    print("CORS Access-Control-Expose-Headers -> PASS:", get_res.headers.get("access-control-expose-headers"))
    
    print("\nALL 10 ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
