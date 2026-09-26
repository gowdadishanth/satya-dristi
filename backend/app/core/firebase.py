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

    if not raw_token or raw_token.lower() in ("null", "undefined", "none", "[object promise]"):
        raise UnauthorizedError("Missing or malformed Authorization credentials.")

    token = raw_token
    
    # Handle dev/test tokens in development environment
    if settings.ENVIRONMENT == "development" and (
        token.startswith("dev-token-")
        or token.startswith("test-token-")
        or token.startswith("test_")
        or token.startswith("sd-token-")
    ):
        uid = token
        for prefix in ("dev-token-", "test-token-", "sd-token-", "test_"):
            if uid.startswith(prefix):
                uid = uid[len(prefix):]
                break
        is_dev = "admin" in token.lower()
        return {
            "uid": uid or "dev_user_earth_analyst_01",
            "email": f"{uid}@satyadristi.org",
            "name": "Remote Sensing Analyst",
            "picture": "",
            "is_dev": is_dev
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
        err_msg = str(e)
        logger.warning("Firebase token verification failed: %s", err_msg)
        # In development mode, gracefully accept expired real Firebase tokens by extracting claims
        # so local testing, demonstrations, and development workflows are not disrupted.
        if settings.ENVIRONMENT == "development" and "expired" in err_msg.lower():
            try:
                import json
                import base64
                parts = token.split(".")
                if len(parts) >= 2:
                    payload_part = parts[1]
                    payload_part += "=" * (-len(payload_part) % 4)
                    claims = json.loads(base64.urlsafe_b64decode(payload_part.encode("utf-8")))
                    uid = claims.get("user_id") or claims.get("sub") or claims.get("uid")
                    if uid:
                        logger.info("Development mode: Gracefully accepting expired session token for user %s", uid)
                        return {
                            "uid": uid,
                            "email": claims.get("email", f"{uid}@satyadristi.org"),
                            "name": claims.get("name", "User"),
                            "picture": claims.get("picture", ""),
                            "is_dev": True
                        }
            except Exception as decode_err:
                logger.debug("Failed to extract claims from expired token: %s", decode_err)

        raise UnauthorizedError(f"Invalid Firebase ID token: {err_msg}")
