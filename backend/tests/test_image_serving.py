import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import db
from app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_firebase_verify():
    with patch("firebase_admin.auth.verify_id_token") as mock:
        def _verify(token, *args, **kwargs):
            if token and token.startswith("valid.jwt."):
                uid = token.replace("valid.jwt.", "")
                return {"uid": uid, "email": f"{uid}@test.gov.in", "name": uid}
            raise ValueError("Invalid Firebase ID token")
        mock.side_effect = _verify
        yield mock

def test_analysis_image_serving_endpoint(tmp_path):
    # Setup test analysis with a dummy cached image
    test_user = "test_user_img"
    other_user = "other_user_img"
    test_analysis_id = "AN-TESTIMG01"
    
    img_dir = settings.DATA_DIR / "cache"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"{test_analysis_id}_primary.png"
    
    # Create simple 10x10 PNG
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(img_path, format="PNG")
    
    rec = {
        "analysis_id": test_analysis_id,
        "uid": test_user,
        "task": "Single-Image VQA",
        "mode": "single",
        "status": "completed",
        "query": "Test image serving",
        "primary_image_path": str(img_path),
        "primary_image_url": "http://example.com/test.jpg",
    }
    db.save_analysis(rec)
    
    try:
        # 1. Access with owner user header
        headers = {"Authorization": f"Bearer valid.jwt.{test_user}"}
        res = client.get(f"/api/v1/analyses/{test_analysis_id}/image/primary", headers=headers)
        assert res.status_code == 200
        assert res.headers["content-type"] in ["image/png", "image/jpeg"]
        assert len(res.content) > 0
        
        # 2. Access with token in query param
        res_token = client.get(f"/api/v1/analyses/{test_analysis_id}/image/primary?token=valid.jwt.{test_user}")
        assert res_token.status_code == 200
        assert len(res_token.content) == len(res.content)
        
        # 3. Access with unauthorized user -> 403
        other_headers = {"Authorization": f"Bearer valid.jwt.{other_user}"}
        res_unauth = client.get(f"/api/v1/analyses/{test_analysis_id}/image/primary", headers=other_headers)
        assert res_unauth.status_code == 403
        
        # 4. Invalid image type -> 404 (because path_map doesn't have it)
        res_bad_type = client.get(f"/api/v1/analyses/{test_analysis_id}/image/unknown", headers=headers)
        assert res_bad_type.status_code == 404
        
        # 5. Non-existent analysis -> 404
        res_not_found = client.get("/api/v1/analyses/AN-DOESNOTEXIST/image/primary", headers=headers)
        assert res_not_found.status_code == 404
        
    finally:
        # Cleanup
        if img_path.exists():
            img_path.unlink()
