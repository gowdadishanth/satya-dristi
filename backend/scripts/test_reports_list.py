import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

res = client.get("/api/v1/reports", headers={"Authorization": "Bearer dev-token-analyst_01"})
print(f"Status: {res.status_code}")
data = res.json()
print("Reports list length:", len(data))
for r in data[:3]:
    print(json.dumps(r, indent=2))
