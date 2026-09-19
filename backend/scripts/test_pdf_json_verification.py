import requests
import io
import json
import pypdf

headers = {'Authorization': 'Bearer dev-token-analyst_01'}
base_url = 'http://127.0.0.1:8000/api/v1'

# 1. List reports
r = requests.get(f'{base_url}/reports', headers=headers)
print('GET /reports status:', r.status_code)
reports = r.json()
print('Total reports returned:', len(reports))

# 2. Test download PDF for ana-01, AN-2041, and first listed report
test_ids = ['ana-01', 'AN-2041', reports[0]['report_id']]
for tid in test_ids:
    r_pdf = requests.get(f'{base_url}/reports/{tid}/download', headers=headers)
    ct = r_pdf.headers.get("content-type")
    cd = r_pdf.headers.get("content-disposition")
    print(f'PDF {tid}: status={r_pdf.status_code}, ct={ct}, cd={cd}, bytes={len(r_pdf.content)}')
    assert r_pdf.status_code == 200, f"Expected 200 for {tid}"
    assert "application/pdf" in ct, f"Expected application/pdf for {tid}"
    assert r_pdf.content.startswith(b"%PDF-"), f"Expected %PDF- header for {tid}"
    
    # Parse with pypdf
    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    print(f' -> Valid PDF verified! Pages: {len(reader.pages)}')
    assert len(reader.pages) > 0
    
    # Test JSON download
    r_json = requests.get(f'{base_url}/reports/{tid}/json', headers=headers)
    ct_json = r_json.headers.get("content-type")
    cd_json = r_json.headers.get("content-disposition")
    print(f'JSON {tid}: status={r_json.status_code}, ct={ct_json}, cd={cd_json}, bytes={len(r_json.content)}')
    assert r_json.status_code == 200, f"Expected 200 for {tid}"
    assert "application/json" in ct_json, f"Expected application/json for {tid}"
    
    data = json.loads(r_json.content.decode('utf-8'))
    print(f' -> Valid JSON verified! Keys: {list(data.keys())[:4]}')
    assert data.get("product") == "Satya Dristi"

print("ALL SERVER TESTS PASSED SUCCESSFULLY!")
