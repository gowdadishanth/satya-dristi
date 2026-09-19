import os
import sys
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
import pypdf
import io

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.report_generator import report_generator
from app.core.config import settings

print("=" * 70)
print("SATYA DRISTI - REPORT DOWNLOAD PIPELINE VERIFICATION")
print("=" * 70)

# -------------------------------------------------------------
# TEST 1: Generate PDF on backend
# -------------------------------------------------------------
print("\n[TEST 1] Generating PDF on backend...")
sample = {
    "analysis_id": "AN-VERIFY-01",
    "uid": "dev_user_earth_analyst_01",
    "query": "Identify industrial encroachment and water surface shifts.",
    "task": "Bi-Temporal Change",
    "input": "Before + After",
    "date": "2026-09-19",
    "time": "14:45",
    "confidence": "High",
    "confidence_score": 0.95,
    "confidence_basis": "Dual-sensor cross agreement",
    "agreements": [{"label": "Spectral", "state": "agree"}],
    "answer": "Significant industrial footprint expansion identified in eastern sector.",
    "observed_evidence": "NDVI drop correlated with backscatter rise in eastern quadrant.",
    "model_interpretation": "Bi-Temporal Siamese Spectral-Structural Change Detector verified.",
    "model_used": "Bi-Temporal Siamese Spectral-Structural Change Detector",
    "device_used": "CPU",
    "aoi": {"bbox": [78.46, 17.41, 78.49, 17.44], "area_sq_km": 10.58},
    "execution_trace": [
        {"name": "Input Co-Registration", "detail": "CRS EPSG:4326 verified", "duration": "0.14s"},
        {"name": "Change Matrix Inference", "detail": "CVA on CPU", "duration": "0.22s"}
    ]
}

rep = report_generator.generate_report_artifacts(sample)
pdf_path = Path(rep["pdf_path"])
assert pdf_path.exists(), "TEST 1 FAILED: PDF file does not exist on disk"
assert pdf_path.stat().st_size > 1000, "TEST 1 FAILED: PDF file too small"
assert report_generator.is_valid_pdf_file(str(pdf_path)), "TEST 1 FAILED: Invalid PDF signature"
print(f"PASS: Generated valid PDF at {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

# -------------------------------------------------------------
# TEST 2 & TEST 3 & TEST 4: Download PDF directly from API & open it
# -------------------------------------------------------------
print("\n[TEST 2, 3, 4] Direct PDF API Download and Verification...")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
pdf_resp = client.get(
    f"/api/v1/reports/{rep['report_id']}/download",
    headers={"Authorization": "Bearer dev-token-dev_user_earth_analyst_01"}
)

assert pdf_resp.status_code == 200, f"TEST 2 FAILED: Status {pdf_resp.status_code}"
assert "application/pdf" in pdf_resp.headers.get("content-type", ""), "TEST 2 FAILED: Wrong content-type"
raw_pdf = pdf_resp.content
assert raw_pdf.startswith(b"%PDF-"), "TEST 2 FAILED: Does not start with %PDF-"
print("PASS: Downloaded valid binary PDF from API")

# TEST 3: Open downloaded PDF
reader = pypdf.PdfReader(io.BytesIO(raw_pdf))
assert len(reader.pages) >= 1, "TEST 3 FAILED: PDF has no pages"
text = reader.pages[0].extract_text()
assert "SATYA DRISTI" in text, "TEST 3 FAILED: Expected branding text not found"
assert "EXECUTIVE RESULT" in text, "TEST 3 FAILED: Expected executive text not found"
print(f"PASS: Opened downloaded PDF successfully. Page count: {len(reader.pages)}. Extracted {len(text)} characters.")

# TEST 4: Verify filename
disposition = pdf_resp.headers.get("content-disposition", "")
match = re.search(r'filename="([^"]+)"', disposition)
assert match, "TEST 4 FAILED: Missing filename in Content-Disposition"
pdf_filename = match.group(1)
assert pdf_filename.endswith(".pdf"), f"TEST 4 FAILED: Filename missing .pdf ({pdf_filename})"
assert pdf_filename.startswith("Satya_Dristi_Analysis_"), f"TEST 4 FAILED: Filename missing prefix ({pdf_filename})"
assert not re.match(r'^[0-9a-f-]{36}\.pdf$', pdf_filename, re.I), f"TEST 4 FAILED: Bare UUID filename ({pdf_filename})"
print(f"PASS: Verified PDF filename: '{pdf_filename}'")

# -------------------------------------------------------------
# TEST 5: Generate JSON on backend
# -------------------------------------------------------------
print("\n[TEST 5] Generating JSON on backend...")
json_path = Path(rep["json_path"])
assert json_path.exists(), "TEST 5 FAILED: JSON file does not exist on disk"
assert report_generator.is_valid_json_file(str(json_path)), "TEST 5 FAILED: Invalid JSON schema"
with open(json_path, "r", encoding="utf-8") as fp:
    json_data = json.load(fp)
assert json_data["product"] == "Satya Dristi"
print(f"PASS: Generated valid JSON at {json_path.name} ({json_path.stat().st_size} bytes)")

# -------------------------------------------------------------
# TEST 6 & TEST 7: Download JSON directly from API & verify
# -------------------------------------------------------------
print("\n[TEST 6, 7] Direct JSON API Download and Verification...")
json_resp = client.get(
    f"/api/v1/reports/{rep['report_id']}/json",
    headers={"Authorization": "Bearer dev-token-dev_user_earth_analyst_01"}
)
assert json_resp.status_code == 200, f"TEST 6 FAILED: Status {json_resp.status_code}"
assert "application/json" in json_resp.headers.get("content-type", ""), "TEST 6 FAILED: Wrong content-type"
parsed_json = json.loads(json_resp.content.decode("utf-8"))
assert parsed_json["product"] == "Satya Dristi"
assert parsed_json["report_id"] == rep["report_id"]
print("PASS: Downloaded valid JSON from API")

# TEST 7: Verify JSON filename
disposition_json = json_resp.headers.get("content-disposition", "")
match_json = re.search(r'filename="([^"]+)"', disposition_json)
assert match_json, "TEST 7 FAILED: Missing filename in Content-Disposition"
json_filename = match_json.group(1)
assert json_filename.endswith(".json"), f"TEST 7 FAILED: Filename missing .json ({json_filename})"
assert json_filename.startswith("Satya_Dristi_Analysis_"), f"TEST 7 FAILED: Filename missing prefix ({json_filename})"
print(f"PASS: Verified JSON filename: '{json_filename}'")

# -------------------------------------------------------------
# TEST 10: Unauthorized user tries to download
# -------------------------------------------------------------
print("\n[TEST 10] Testing Unauthorized and Forbidden Access...")
from app.core.firebase import get_current_user
app.dependency_overrides[get_current_user] = lambda: {
    "uid": "unauthorized_intruder",
    "email": "intruder@bad.com",
    "name": "Intruder",
    "picture": "",
    "is_dev": False
}

try:
    unauth_pdf = client.get(f"/api/v1/reports/{rep['report_id']}/download")
    assert unauth_pdf.status_code == 403, f"TEST 10 FAILED: Expected 403, got {unauth_pdf.status_code}"
    assert unauth_pdf.headers["content-type"].startswith("application/json")
    assert not unauth_pdf.content.startswith(b"%PDF-")
    print("PASS: Unauthorized access blocked with 403 Forbidden; no PDF downloaded.")

    unauth_json = client.get(f"/api/v1/reports/{rep['report_id']}/json")
    assert unauth_json.status_code == 403
    assert unauth_json.headers["content-type"].startswith("application/json")
    print("PASS: Unauthorized JSON access blocked with 403 Forbidden; no file downloaded.")
finally:
    app.dependency_overrides.pop(get_current_user, None)

print("\n" + "=" * 70)
print("ALL ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")
print("=" * 70)
