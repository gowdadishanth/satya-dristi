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

_google_certs_cache: tuple[float, dict[str, str]] | None = None

def _get_google_certs() -> dict[str, str]:
    global _google_certs_cache
    import time
    now = time.monotonic()
    if _google_certs_cache and (now - _google_certs_cache[0]) < 3600:
        return _google_certs_cache[1]
    import httpx
    try:
        resp = httpx.get(
            "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
            timeout=5.0
        )
        if resp.is_success:
            certs = resp.json()
            _google_certs_cache = (now, certs)
            return certs
    except Exception as e:
        logger.warning("Failed to refresh Google public certificates: %s", e)
    return _google_certs_cache[1] if _google_certs_cache else {}

def _verify_jwt_against_google_certs(raw_token: str) -> dict:
    import jwt
    from cryptography.x509 import load_pem_x509_certificate
    headers = jwt.get_unverified_header(raw_token)
    kid = headers.get("kid")
    certs = _get_google_certs()
    cert_pem = certs.get(kid)
    if not cert_pem:
        raise ValueError(f"No matching Google certificate for key ID {kid}")
    cert_obj = load_pem_x509_certificate(cert_pem.encode("utf-8"))
    public_key = cert_obj.public_key()
    return jwt.decode(
        raw_token,
        public_key,
        algorithms=["RS256"],
        audience=settings.FIREBASE_PROJECT_ID,
        issuer=f"https://securetoken.google.com/{settings.FIREBASE_PROJECT_ID}"
    )

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

    decoded_token = None
    try:
        decoded_token = fb_auth.verify_id_token(raw_token)
    except Exception as primary_err:
        logger.info("Firebase Admin verification deferred (%s), using Google public certs fallback", primary_err)
        try:
            decoded_token = _verify_jwt_against_google_certs(raw_token)
        except Exception as fallback_err:
            logger.warning("Google certs verification failed: %s", fallback_err)
            raise UnauthorizedError(f"Invalid Firebase ID token: {primary_err}")

    uid = decoded_token.get("uid") or decoded_token.get("sub") or decoded_token.get("user_id")
    if not uid:
        raise UnauthorizedError("Token does not contain a valid user ID.")
    return {
        "uid": uid,
        "email": decoded_token.get("email", ""),
        "name": decoded_token.get("name", "User"),
        "picture": decoded_token.get("picture", ""),
        "is_dev": False
    }

async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Optional[dict]:
    try:
        return await get_current_user(authorization, token)
    except Exception:
        return None
