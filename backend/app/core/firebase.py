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
        cred_json = settings.FIREBASE_CREDENTIALS_JSON or os.getenv("FIREBASE_CREDENTIALS_JSON", "")
        cred_path = settings.FIREBASE_CREDENTIALS_PATH or settings.GOOGLE_APPLICATION_CREDENTIALS
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized with certificate: %s", cred_path)
        elif cred_json and cred_json.strip().startswith("{"):
            import json
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized with credentials JSON from environment.")
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

    if not raw_token or raw_token.lower() in ("null", "undefined", "none", "[object promise]"):
        raise UnauthorizedError("Missing or malformed Authorization credentials.")

    # Strict rejection of synthetic, mock, or malformed tokens (prohibited in production)
    if (
        raw_token.startswith("dev-token-") or
        raw_token.startswith("test-token-") or
        raw_token.startswith("guest-") or
        raw_token.startswith("sd-") or
        raw_token.count(".") != 2
    ):
        raise UnauthorizedError("Invalid Firebase ID token: synthetic or unverified tokens are prohibited.")

    try:
        decoded_token = fb_auth.verify_id_token(raw_token)
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
        err_msg = str(e)
        logger.warning("Firebase token verification failed: %s", err_msg)
        raise UnauthorizedError(f"Invalid Firebase ID token: {err_msg}")
