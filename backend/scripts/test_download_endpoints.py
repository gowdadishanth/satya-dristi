import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
import pypdf
import json
import io

client = TestClient(app)

cases = ["REP-ACCEPT-01", "REP-2041", "AN-2041", "ana-01"]

for cid in cases:
    print("=" * 60)
    print(f"TESTING CASE: {cid}")
    
    # 1. PDF DOWNLOAD
    res_pdf = client.get(f"/api/v1/reports/{cid}/download", headers={"Authorization": "Bearer dev-token-analyst_01"})
    print(f"  PDF Status: {res_pdf.status_code}")
    print(f"  PDF Content-Type: {res_pdf.headers.get('content-type')}")
    print(f"  PDF Content-Disposition: {res_pdf.headers.get('content-disposition')}")
    print(f"  PDF Length: {len(res_pdf.content)} bytes")
    print(f"  PDF Header: {res_pdf.content[:10]}")
    if res_pdf.status_code == 200:
        try:
            reader = pypdf.PdfReader(io.BytesIO(res_pdf.content))
            print(f"  [PDF OK] Pages: {len(reader.pages)}")
        except Exception as e:
            print(f"  [PDF CORRUPT]: {e}")
            
    # 2. JSON DOWNLOAD
    res_json = client.get(f"/api/v1/reports/{cid}/json", headers={"Authorization": "Bearer dev-token-analyst_01"})
    print(f"  JSON Status: {res_json.status_code}")
    print(f"  JSON Content-Type: {res_json.headers.get('content-type')}")
    print(f"  JSON Content-Disposition: {res_json.headers.get('content-disposition')}")
    print(f"  JSON Length: {len(res_json.content)} bytes")
    if res_json.status_code == 200:
        try:
            parsed = json.loads(res_json.content.decode("utf-8"))
            print(f"  [JSON OK] Keys: {list(parsed.keys())[:5]}")
        except Exception as e:
            print(f"  [JSON CORRUPT]: {e}")
