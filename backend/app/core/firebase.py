import os
import logging
from typing import Optional
from fastapi import Header, Query
import firebase_admin
from firebase_admin import auth as fb_auth, credentials

from app.core.config import settings
from app.core.errors import UnauthorizedError

logger = logging.getLogger(__name__)

_firebase_initialized = False

def init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        cred_path = settings.FIREBASE_CREDENTIALS_PATH or settings.GOOGLE_APPLICATION_CREDENTIALS
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized with certificate: %s", cred_path)
        else:
            # Initialize with default credentials or project ID
            firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID})
            logger.info("Firebase Admin initialized with default project: %s", settings.FIREBASE_PROJECT_ID)
        _firebase_initialized = True
    except Exception as e:
        logger.warning("Firebase Admin initialization deferred/failed: %s", e)

# Call on import
init_firebase()

async def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> dict:
    """
    Extract and verify Firebase ID token from Authorization header or ?token= query parameter.
    Returns authenticated user claims: uid, email, name, picture.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ")[1].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise UnauthorizedError("Missing or malformed Authorization credentials.")

    token = raw_token
    
    # Handle dev/test tokens in development environment
    if settings.ENVIRONMENT == "development" and (
        token.startswith("dev-token-") or token.startswith("test-token-") or token.startswith("test_")
    ):
        uid = token.replace("dev-token-", "").replace("test-token-", "")
        return {
            "uid": uid or "dev_user_earth_analyst_01",
            "email": f"{uid}@satyadristi.org",
            "name": "Remote Sensing Analyst",
            "picture": "",
            "is_dev": True
        }

    try:
        decoded_token = fb_auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not uid:
            raise UnauthorizedError("Token does not contain a valid user ID.")
        return {
            "uid": uid,
            "email": decoded_token.get("email", ""),
            "name": decoded_token.get("name", "User"),
            "picture": decoded_token.get("picture", ""),
            "is_dev": False
        }
    except Exception as e:
        logger.error("Firebase token verification failed: %s", e)
        raise UnauthorizedError(f"Invalid Firebase ID token: {str(e)}")
