from fastapi import APIRouter, Depends
from app.core.firebase import get_current_user
from app.core.db import db

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user profile and saves/updates in Firestore."""
    db.save_user(current_user)
    return current_user
