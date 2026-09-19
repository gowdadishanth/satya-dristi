import requests

headers = {'Authorization': 'Bearer dev-token-analyst_01'}
for rep_id in ['REP-6DDE0A74', 'AN-6DDE0A74', 'ana-01', 'ana-02']:
    try:
        r_pdf = requests.get(f'http://127.0.0.1:8000/api/v1/reports/{rep_id}/download', headers=headers, timeout=5)
        print(f'PDF {rep_id}: status={r_pdf.status_code}, ct={r_pdf.headers.get("content-type")}, len={len(r_pdf.content)}, starts={r_pdf.content[:15]}')
    except Exception as e:
        print(f'PDF {rep_id} err: {e}')
    
    try:
        r_json = requests.get(f'http://127.0.0.1:8000/api/v1/reports/{rep_id}/json', headers=headers, timeout=5)
        print(f'JSON {rep_id}: status={r_json.status_code}, ct={r_json.headers.get("content-type")}, len={len(r_json.content)}, starts={r_json.content[:30]}')
    except Exception as e:
        print(f'JSON {rep_id} err: {e}')
