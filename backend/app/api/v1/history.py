import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.core.firebase import get_current_user
from app.core.db import db
from app.schemas.analysis import AnalysisDetailResponse

router = APIRouter(prefix="/history", tags=["Analysis History"])

def get_user_scoped_aid(base_aid: str, uid: str) -> str:
    user_tag = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:8].upper()
    return f"AN-{user_tag}-{base_aid.replace('AN-', '')}"

@router.get("", response_model=List[AnalysisDetailResponse])
async def get_history(
    task: Optional[str] = Query("All", description="Filter by task or 'All'"),
    q: Optional[str] = Query(None, description="Search query string"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns authentic persistent analysis history for the authenticated user.
    Supports filtering by task type and query search.
    """
    uid = current_user["uid"]
    analyses = db.list_analyses(uid=uid, task=task, limit=limit)
    
    if q and analyses:
        q_lower = q.lower()
        analyses = [a for a in analyses if q_lower in a.get("query", "").lower() or q_lower in a.get("answer", "").lower()]

    return analyses
