import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, File, UploadFile, Query
from fastapi.responses import FileResponse

from app.core.config import settings
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
    total_bytes = 0

    uploads_to_process = [
        ("Image", image),
        ("Before", before),
        ("After", after),
        ("Optical", optical),
        ("SAR", sar),
    ]

    try:
        for tag, upload_file in uploads_to_process:
            if upload_file:
                saved_path, written = await image_retrieval_service.stream_and_save_upload(
                    upload=upload_file,
                    analysis_id=analysis_id,
                    tag=tag,
                    current_total_bytes=total_bytes,
                )
                file_paths[tag] = saved_path
                total_bytes += written
    except Exception:
        analysis_upload_dir = settings.UPLOADS_DIR / analysis_id
        if analysis_upload_dir.is_dir():
            shutil.rmtree(analysis_upload_dir, ignore_errors=True)
        raise

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
    if not evidence_path:
        raise NotFoundError("Evidence image not found.")

    resolved_path = Path(evidence_path).resolve()
    base_evidence_dir = settings.EVIDENCE_DIR.resolve()
    try:
        resolved_path.relative_to(base_evidence_dir)
    except ValueError:
        raise ForbiddenError("Invalid evidence path.")

    if not resolved_path.is_file():
        raise NotFoundError("Evidence image not found.")
        
    return FileResponse(str(resolved_path), media_type="image/png")

@router.get("/{analysis_id}/image/{image_type}")
async def get_analysis_image_file(
    analysis_id: str,
    image_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns the primary, before, after, or SAR satellite image for an analysis."""
    doc = db.get_analysis(analysis_id)
    if not doc:
        raise NotFoundError(f"Analysis '{analysis_id}' not found.")

    if not current_user.get("is_dev") and doc.get("uid") != current_user["uid"]:
        raise ForbiddenError("You are not authorized to access this analysis image.")

    path_map = {
        "primary": doc.get("primary_image_path"),
        "after": doc.get("primary_image_path"),
        "before": doc.get("before_image_path") or doc.get("primary_image_path"),
        "sar": doc.get("sar_image_path") or doc.get("primary_image_path"),
        "evidence": doc.get("evidence_path"),
    }

    img_path = path_map.get(image_type.lower())
    if not img_path:
        raise NotFoundError(f"Image of type '{image_type}' not found for analysis.")

    resolved_path = Path(img_path).resolve()
    base_data_dir = settings.DATA_DIR.resolve()
    try:
        resolved_path.relative_to(base_data_dir)
    except ValueError:
        raise ForbiddenError("Invalid image path.")

    if not resolved_path.is_file():
        raise NotFoundError(f"Image file for '{image_type}' does not exist on disk.")

    media_type = "image/png"
    if resolved_path.suffix.lower() in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif resolved_path.suffix.lower() in [".tif", ".tiff"]:
        media_type = "image/tiff"

    return FileResponse(str(resolved_path), media_type=media_type)

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
