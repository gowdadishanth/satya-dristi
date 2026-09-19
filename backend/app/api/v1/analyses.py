import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, File, UploadFile, Query
from fastapi.responses import FileResponse

from app.core.firebase import get_current_user
from app.core.db import db
from app.core.errors import NotFoundError, UnauthorizedError, ForbiddenError
from app.services.async_queue import job_manager
from app.services.image_retrieval import image_retrieval_service
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisStatusResponse,
    AnalysisDetailResponse
)

router = APIRouter(prefix="/analyses", tags=["Analysis Workspace"])

@router.post("", response_model=AnalysisStatusResponse)
async def create_analysis_json(
    req: AnalysisCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submits an asynchronous Earth observation analysis task via JSON payload.
    Supports single image VQA, grounding, bi-temporal change, and optical-SAR fusion.
    """
    analysis_id = f"AN-{uuid.uuid4().hex.upper()}"
    
    await job_manager.start_analysis_job(
        analysis_id=analysis_id,
        uid=current_user["uid"],
        mode=req.mode,
        query=req.query,
        scene_id=req.scene_id,
        aoi=req.aoi,
        before_scene_id=req.before_scene_id,
        after_scene_id=req.after_scene_id,
        optical_scene_id=req.optical_scene_id,
        sar_scene_id=req.sar_scene_id
    )

    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "current_stage": "queued",
        "progress_pct": 5,
        "error": None
    }

@router.post("/upload", response_model=AnalysisStatusResponse)
async def create_analysis_multipart(
    mode: str = Form("single"),
    query: str = Form(...),
    image: Optional[UploadFile] = File(None),
    before: Optional[UploadFile] = File(None),
    after: Optional[UploadFile] = File(None),
    optical: Optional[UploadFile] = File(None),
    sar: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Submits an asynchronous analysis task with direct user-uploaded remote sensing imagery (GeoTIFF/PNG/JPEG).
    """
    analysis_id = f"AN-{uuid.uuid4().hex.upper()}"
    file_paths = {}

    if image:
        content = await image.read()
        file_paths["Image"] = await image_retrieval_service.save_uploaded_file(image.filename, content)
    if before:
        content = await before.read()
        file_paths["Before"] = await image_retrieval_service.save_uploaded_file(before.filename, content)
    if after:
        content = await after.read()
        file_paths["After"] = await image_retrieval_service.save_uploaded_file(after.filename, content)
    if optical:
        content = await optical.read()
        file_paths["Optical"] = await image_retrieval_service.save_uploaded_file(optical.filename, content)
    if sar:
        content = await sar.read()
        file_paths["SAR"] = await image_retrieval_service.save_uploaded_file(sar.filename, content)

    await job_manager.start_analysis_job(
        analysis_id=analysis_id,
        uid=current_user["uid"],
        mode=mode,
        query=query,
        file_paths=file_paths
    )

    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "current_stage": "queued",
        "progress_pct": 5,
        "error": None
    }

@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Polls real-time progress and observable execution stage of an asynchronous analysis.
    """
    owner_uid = job_manager.get_job_owner(analysis_id)
    if not owner_uid:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")
        
    if not current_user.get("is_dev") and owner_uid != current_user["uid"]:
        raise ForbiddenError("You are not authorized to view this analysis status.")

    status_info = job_manager.get_job_status(analysis_id)
    if not status_info:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")
    return status_info

@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis_detail(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves full analysis results, model answer, visual evidence, and execution trace.
    """
    doc = db.get_analysis(analysis_id)
    if not doc:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")
    
    # Check multi-tenancy authorization (allow dev user access)
    if not current_user.get("is_dev") and doc.get("uid") != current_user["uid"]:
        raise ForbiddenError("You are not authorized to view this analysis.")
        
    return doc

@router.get("/{analysis_id}/evidence")
async def get_analysis_evidence_file(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns the visual evidence overlay image generated for the analysis."""
    doc = db.get_analysis(analysis_id)
    if not doc:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")
    
    # Enforce multi-tenancy ownership (allow dev user access)
    if not current_user.get("is_dev") and doc.get("uid") != current_user["uid"]:
        raise ForbiddenError("You are not authorized to access this analysis evidence.")
        
    evidence_path = doc.get("evidence_path")
    if not evidence_path or not os.path.isfile(evidence_path):
        raise NotFoundError("Evidence image not found.")
        
    return FileResponse(evidence_path, media_type="image/png")

@router.get("/{analysis_id}/trace")
async def get_analysis_trace(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns the observable execution trace for an analysis."""
    doc = db.get_analysis(analysis_id)
    if not doc:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")
        
    # Enforce multi-tenancy ownership (allow dev user access)
    if not current_user.get("is_dev") and doc.get("uid") != current_user["uid"]:
        raise ForbiddenError("You are not authorized to view this analysis trace.")
        
    return {
        "analysis_id": analysis_id,
        "task": doc.get("task"),
        "model_used": doc.get("model_used"),
        "total_duration_sec": doc.get("total_duration_sec"),
        "execution_trace": doc.get("execution_trace", [])
    }

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Deletes an analysis record belonging to the authenticated user."""
    success = db.delete_analysis(analysis_id, current_user["uid"])
    if not success:
        raise NotFoundError(f"Analysis '{analysis_id}' not found or unauthorized.")
    return {"deleted": True, "analysis_id": analysis_id}
