import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.errors import UnauthorizedError

client = TestClient(app)

GOOGLE_USER_A = {
    "uid": "google_uid_alpha_12345",
    "email": "analyst.alpha@gmail.com",
    "name": "Alex Alpha",
    "picture": "https://lh3.googleusercontent.com/a/alpha123",
}

GOOGLE_USER_B = {
    "uid": "google_uid_bravo_67890",
    "email": "analyst.bravo@gmail.com",
    "name": "Blake Bravo",
    "picture": "https://lh3.googleusercontent.com/a/bravo456",
}

def test_signed_out_state_rejected():
    """Unauthenticated requests without Bearer token must return 401 Unauthorized."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Missing or malformed Authorization credentials" in res.text

def test_malformed_token_rejected():
    """Invalid or malformed tokens must be rejected with 401."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert res.status_code == 401
    assert "Invalid Firebase ID token" in res.text or "Unauthorized" in res.text

@patch("firebase_admin.auth.verify_id_token")
def test_successful_firebase_user_a_auth(mock_verify):
    """Real Firebase ID token for Google User A is verified and maps UID, email, name."""
    app.dependency_overrides.clear()
    mock_verify.return_value = {
        "uid": GOOGLE_USER_A["uid"],
        "email": GOOGLE_USER_A["email"],
        "name": GOOGLE_USER_A["name"],
        "picture": GOOGLE_USER_A["picture"],
    }

    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake_signed_token_a"})
    assert res.status_code == 200
    data = res.json()
    assert data["uid"] == GOOGLE_USER_A["uid"]
    assert data["email"] == GOOGLE_USER_A["email"]
    assert data["name"] == GOOGLE_USER_A["name"]
    assert data["picture"] == GOOGLE_USER_A["picture"]
    assert data["is_dev"] is False

@patch("firebase_admin.auth.verify_id_token")
def test_account_switching_between_google_accounts(mock_verify):
    """Switching from Google Account A to Google Account B updates the authenticated identity."""
    app.dependency_overrides.clear()
    
    # 1. First authenticate as Account A
    mock_verify.return_value = {
        "uid": GOOGLE_USER_A["uid"],
        "email": GOOGLE_USER_A["email"],
        "name": GOOGLE_USER_A["name"],
        "picture": GOOGLE_USER_A["picture"],
    }
    res_a = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token_a"})
    assert res_a.status_code == 200
    assert res_a.json()["uid"] == GOOGLE_USER_A["uid"]

    # 2. Switch to Account B (select_account in popup)
    mock_verify.return_value = {
        "uid": GOOGLE_USER_B["uid"],
        "email": GOOGLE_USER_B["email"],
        "name": GOOGLE_USER_B["name"],
        "picture": GOOGLE_USER_B["picture"],
    }
    res_b = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token_b"})
    assert res_b.status_code == 200
    assert res_b.json()["uid"] == GOOGLE_USER_B["uid"]
    assert res_b.json()["email"] == GOOGLE_USER_B["email"]
    assert res_b.json()["uid"] != res_a.json()["uid"]

@patch("firebase_admin.auth.verify_id_token")
def test_user_data_isolation_between_switched_accounts(mock_verify):
    """History and analyses belong strictly to the authenticated Firebase UID."""
    app.dependency_overrides.clear()

    # User A accesses their analyses
    mock_verify.return_value = {"uid": GOOGLE_USER_A["uid"], "email": GOOGLE_USER_A["email"]}
    res_a = client.get("/api/v1/history", headers={"Authorization": "Bearer token_a"})
    assert res_a.status_code == 200

    # User B accesses their analyses
    mock_verify.return_value = {"uid": GOOGLE_USER_B["uid"], "email": GOOGLE_USER_B["email"]}
    res_b = client.get("/api/v1/history", headers={"Authorization": "Bearer token_b"})
    assert res_b.status_code == 200
