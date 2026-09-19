import requests
import time
import sys

BASE = 'http://127.0.0.1:8000/api/v1'
headers = {'Authorization': 'Bearer test_user_token'}

print('=== 1. TESTING BI-TEMPORAL CHANGE DETECTION ===')
# Hyderabad / Krishna River corridor
aoi_box = [80.60, 16.50, 80.64, 16.54]

# Search before scene (2022)
r_before = requests.post(f'{BASE}/earth/scenes/search', json={'bbox': aoi_box, 'year': 2022, 'sensor': 'optical', 'limit': 1}, headers=headers)
before_scenes = r_before.json()
print(f'Before scenes (2022): {len(before_scenes)} found')
before_id = before_scenes[0]['scene_id'] if before_scenes else None

# Search after scene (2024)
r_after = requests.post(f'{BASE}/earth/scenes/search', json={'bbox': aoi_box, 'year': 2024, 'sensor': 'optical', 'limit': 1}, headers=headers)
after_scenes = r_after.json()
print(f'After scenes (2024): {len(after_scenes)} found')
after_id = after_scenes[0]['scene_id'] if after_scenes else None

temporal_payload = {
    'mode': 'temporal',
    'query': 'What changed between these two dates along the river corridor?',
    'scene_id': after_id,
    'before_scene_id': before_id,
    'aoi': {'bbox': aoi_box, 'geometry': None}
}

r = requests.post(f'{BASE}/analyses', json=temporal_payload, headers=headers)
assert r.status_code == 200
t_aid = r.json()['analysis_id']
print('Temporal Job Submitted:', t_aid)

for _ in range(40):
    time.sleep(1.0)
    st = requests.get(f'{BASE}/analyses/{t_aid}/status', headers=headers).json()
    if st.get('status') in ['completed', 'failed']:
        break

assert st.get('status') == 'completed', f'Temporal analysis failed: {st}'
t_detail = requests.get(f'{BASE}/analyses/{t_aid}', headers=headers).json()
print('Temporal Answer:', t_detail.get('answer'))
print('Temporal Model Used:', t_detail.get('model_used'))
print('Temporal Evidence Path:', t_detail.get('evidence_path'))
assert t_detail.get('evidence_path') is not None, 'Evidence path missing for temporal analysis'

# Download Temporal Report PDF
r_pdf = requests.get(f'{BASE}/reports/{t_aid}/download', headers=headers)
assert r_pdf.status_code == 200 and len(r_pdf.content) > 1000
print(f'Temporal Report PDF Downloaded ({len(r_pdf.content)} bytes)')

print('\n=== 2. TESTING OPTICAL + SAR MULTIMODAL FUSION ===')
# Search SAR scene
r_sar = requests.post(f'{BASE}/earth/scenes/search', json={'bbox': aoi_box, 'year': 2024, 'sensor': 'sar', 'limit': 1}, headers=headers)
sar_scenes = r_sar.json()
print(f'SAR scenes (2024): {len(sar_scenes)} found')
sar_id = sar_scenes[0]['scene_id'] if sar_scenes else None

fusion_payload = {
    'mode': 'fusion',
    'query': 'Use the optical and SAR images together to identify built-up and water-covered regions.',
    'scene_id': after_id,
    'sar_scene_id': sar_id,
    'aoi': {'bbox': aoi_box, 'geometry': None}
}

r = requests.post(f'{BASE}/analyses', json=fusion_payload, headers=headers)
assert r.status_code == 200
f_aid = r.json()['analysis_id']
print('Fusion Job Submitted:', f_aid)

for _ in range(40):
    time.sleep(1.0)
    st = requests.get(f'{BASE}/analyses/{f_aid}/status', headers=headers).json()
    if st.get('status') in ['completed', 'failed']:
        break

assert st.get('status') == 'completed', f'Fusion analysis failed: {st}'
f_detail = requests.get(f'{BASE}/analyses/{f_aid}', headers=headers).json()
print('Fusion Answer:', f_detail.get('answer'))
print('Fusion Confidence:', f_detail.get('confidence'), f"({f_detail.get('confidence_score')})")
print('Fusion Evidence Path:', f_detail.get('evidence_path'))
assert f_detail.get('evidence_path') is not None

# Download Fusion Report PDF
r_pdf_f = requests.get(f'{BASE}/reports/{f_aid}/download', headers=headers)
assert r_pdf_f.status_code == 200 and len(r_pdf_f.content) > 1000
print(f'Fusion Report PDF Downloaded ({len(r_pdf_f.content)} bytes)')

print('\n=== ALL MULTIMODAL & TEMPORAL TESTS PASSED PERFECTLY ===')
