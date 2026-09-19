import requests
import time
import sys

BASE = 'http://127.0.0.1:8000/api/v1'
headers = {'Authorization': 'Bearer test_user_token'}

print('1. Testing System Health...')
r = requests.get(f'{BASE}/system/health')
print('System Health:', r.status_code, r.json().get('status'))
assert r.status_code == 200

print('\n2. Searching Real Satellite Scenes (Hyderabad bbox)...')
search_payload = {
    'bbox': [78.46, 17.41, 78.49, 17.44],
    'year': 2024,
    'sensor': 'optical',
    'limit': 2
}
r = requests.post(f'{BASE}/earth/scenes/search', json=search_payload, headers=headers)
print('Search Status:', r.status_code)
scenes = r.json()
print(f'Found {len(scenes)} real scenes:')
for s in scenes:
    print(' - Scene:', s['scene_id'], '| Acquired:', s['acquisition_datetime'], '| Cloud:', s['cloud_cover'], '%')
assert len(scenes) > 0
scene_id = scenes[0]['scene_id']

print('\n3. Previewing AOI...')
r = requests.post(f'{BASE}/earth/aoi/preview', json={'bbox': [78.46, 17.41, 78.49, 17.44]}, headers=headers)
aoi = r.json()
print('AOI Area:', aoi['area_sq_km'], 'sq km | Centroid:', aoi['centroid'])
assert r.status_code == 200

print('\n4. Launching Asynchronous Remote-Sensing Analysis...')
ana_payload = {
    'mode': 'single',
    'query': 'Highlight the water body and describe the major land-cover types visible.',
    'scene_id': scene_id,
    'aoi': aoi
}
r = requests.post(f'{BASE}/analyses', json=ana_payload, headers=headers)
print('Job submission status:', r.status_code)
job = r.json()
aid = job['analysis_id']
print('Submitted Analysis ID:', aid, '| Initial stage:', job['current_stage'])

print('\nPolling analysis job status...')
for _ in range(40):
    time.sleep(1.0)
    r = requests.get(f'{BASE}/analyses/{aid}/status', headers=headers)
    st = r.json()
    stage = st.get('current_stage')
    pct = st.get('progress_pct')
    status = st.get('status')
    print(f'   -> Stage: {stage} ({pct}%) | Status: {status}')
    if status in ['completed', 'failed']:
        break

assert status == 'completed', f'Analysis did not complete: {st}'

print('\n5. Fetching Analysis Detail...')
r = requests.get(f'{BASE}/analyses/{aid}', headers=headers)
detail = r.json()
print('Answer:', detail.get('answer'))
print('Confidence:', detail.get('confidence'), f"({detail.get('confidence_score', 'N/A')})")
print('Evidence boxes count:', len(detail.get('boxes', [])))
print('Execution stages count:', len(detail.get('execution_trace', [])))

print('\n6. Downloading Report PDF...')
r = requests.get(f'{BASE}/reports/{aid}/download', headers=headers)
print('PDF response code:', r.status_code, '| Content-Type:', r.headers.get('content-type'))
assert r.status_code == 200
assert 'application/pdf' in r.headers.get('content-type', '')
pdf_bytes = len(r.content)
print(f'PDF size: {pdf_bytes} bytes')
assert pdf_bytes > 1000, 'PDF is empty or too small!'

with open('test_output_report.pdf', 'wb') as f:
    f.write(r.content)
print('Saved test_output_report.pdf successfully!')

# Check PDF header
assert r.content.startswith(b'%PDF'), 'File does not start with PDF magic bytes!'
print('PDF Header confirmed (%PDF)!')
print('\n=== ALL VERIFICATION CHECKS PASSED WITH FLYING COLORS ===')
