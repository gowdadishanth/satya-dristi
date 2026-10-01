import os
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.firebase import get_current_user
from app.core.db import db
from app.core.errors import NotFoundError, UnauthorizedError, ForbiddenError, ReportGenerationFailedError
from app.services.report_generator import report_generator
from app.schemas.report import ReportListItem, ReportDetailResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

def sanitize_filename(filename: str) -> str:
    """Removes invalid filesystem characters and prevents directory traversal."""
    name = re.sub(r'[\\/*?:"<>|]', "", filename)
    return name.strip() or "Satya_Dristi_Report.bin"

def get_user_scoped_id(base_id: str, uid: str) -> str:
    user_tag = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:8].upper()
    if base_id.startswith("AN-"):
        return f"AN-{user_tag}-{base_id[3:]}"
    if base_id.startswith("REP-"):
        return f"REP-{user_tag}-{base_id[4:]}"
    return f"{base_id}-{user_tag}"

def find_or_create_report_for_id(report_id: str, uid: str, is_dev: bool = False) -> Dict[str, Any]:
    """
    Robustly resolves a report or analysis by identifier:
    - Direct report_id (e.g. REP-...)
    - Direct analysis_id (e.g. AN-...)
    Enforces user ownership and tenant isolation.
    """
    target_id = report_id

    # 2. Try direct report lookup
    rep = db.get_report(target_id)
    if rep:
        if not is_dev and rep.get("uid") and rep["uid"] != uid:
            raise ForbiddenError("You are not authorized to access this report.")
        return rep

    # 3. Try with/without REP- prefix or converted from AN-
    rep_variants = [
        f"REP-{target_id.replace('AN-', '').replace('REP-', '')}",
        f"REP-{target_id}",
        target_id.replace("REP-", "").replace("AN-", "")
    ]
    for r_cand in rep_variants:
        rep = db.get_report(r_cand)
        if rep:
            if not is_dev and rep.get("uid") and rep["uid"] != uid:
                raise ForbiddenError("You are not authorized to access this report.")
            return rep

    # 4. Try user-scoped report ID
    base_clean = target_id.replace("AN-", "").replace("REP-", "")
    scoped_rep_id = get_user_scoped_id(f"REP-{base_clean}", uid)
    rep = db.get_report(scoped_rep_id)
    if rep:
        if not is_dev and rep.get("uid") and rep["uid"] != uid:
            raise ForbiddenError("You are not authorized to access this report.")
        return rep

    # 5. Try analysis lookup in database
    target_aid = target_id.replace("REP-", "AN-") if target_id.startswith("REP-") else target_id
    analysis = db.get_analysis(target_aid)
    if not analysis and not target_aid.startswith("AN-"):
        analysis = db.get_analysis(f"AN-{target_aid}")

    if analysis:
        if not is_dev and analysis.get("uid") and analysis["uid"] != uid:
            raise ForbiddenError("You are not authorized to access the analysis for this report.")

    # 6. Try user-scoped analysis lookup in database
    scoped_aid = get_user_scoped_id(target_aid if target_aid.startswith("AN-") else f"AN-{target_aid}", uid)
    if not analysis:
        analysis = db.get_analysis(scoped_aid)
        if analysis and not is_dev and analysis.get("uid") and analysis["uid"] != uid:
            raise ForbiddenError("You are not authorized to access the analysis for this report.")

    # 7. If found as analysis, generate artifacts
    if analysis:
        rep = report_generator.generate_report_artifacts(analysis)
        rep["uid"] = uid
        db.save_report(rep)
        return rep

    raise NotFoundError(f"Report or analysis record '{report_id}' could not be located.")

@router.get("", response_model=List[ReportListItem])
async def list_reports(current_user: dict = Depends(get_current_user)):
    """
    Lists all generated reports for the authenticated user.
    """
    uid = current_user["uid"]
    reports = db.list_reports(uid=uid)
    
    # If no reports yet, auto-generate for any existing completed analyses
    if not reports:
        analyses = db.list_analyses(uid=uid, limit=10)
        for a in analyses:
            try:
                r = report_generator.generate_report_artifacts(a)
                r["uid"] = uid
                db.save_report(r)
                reports.append(r)
            except Exception as e:
                logger.error("Failed auto-generating report for %s: %s", a.get("analysis_id"), e)
                
    return reports

@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves metadata for a specific report."""
    uid = current_user["uid"]
    is_dev = current_user.get("is_dev", False)
    rep = find_or_create_report_for_id(report_id, uid, is_dev=is_dev)
    if not is_dev and rep.get("uid") and rep["uid"] != uid:
        raise ForbiddenError("You are not authorized to access this report.")
    return rep

@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Downloads the authentic, publication-grade vector PDF report document.
    Guarantees Content-Type: application/pdf and Content-Disposition: attachment.
    Validates PDF integrity on disk; automatically regenerates if missing or corrupt.
    """
    uid = current_user["uid"]
    is_dev = current_user.get("is_dev", False)
    rep = find_or_create_report_for_id(report_id, uid, is_dev=is_dev)

    # Enforce report ownership for non-dev users
    if not is_dev and rep.get("uid") and rep["uid"] != uid:
        raise ForbiddenError("You are not authorized to download this report document.")

    pdf_path = rep.get("pdf_path")
    # Verify file existence and valid %PDF- signature
    if not pdf_path or not report_generator.is_valid_pdf_file(pdf_path):
        target_aid = rep.get("analysis_id") or report_id
        analysis = db.get_analysis(target_aid)
        if not analysis:
            raise NotFoundError(f"Underlying analysis for report '{report_id}' not found.")
        
        rep = report_generator.generate_report_artifacts(analysis)
        rep["uid"] = uid
        db.save_report(rep)
        pdf_path = rep.get("pdf_path")

    if not pdf_path or not os.path.exists(pdf_path) or not report_generator.is_valid_pdf_file(pdf_path):
        raise ReportGenerationFailedError("Failed to produce a verified PDF binary artifact.")

    raw_filename = rep.get("pdf_filename") or f"Satya_Dristi_Analysis_{report_id}.pdf"
    clean_filename = sanitize_filename(raw_filename)
    if not clean_filename.startswith("Satya_Dristi_"):
        clean_filename = f"Satya_Dristi_Analysis_{clean_filename}"
    if not clean_filename.lower().endswith(".pdf"):
        clean_filename += ".pdf"

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=clean_filename,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": f'attachment; filename="{clean_filename}"'
        }
    )

@router.get("/{report_id}/json")
async def download_report_json(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Downloads the full auditable structured JSON export for the analysis.
    Guarantees Content-Type: application/json and Content-Disposition: attachment.
    Validates JSON integrity on disk; automatically regenerates if missing or corrupt.
    """
    uid = current_user["uid"]
    is_dev = current_user.get("is_dev", False)
    rep = find_or_create_report_for_id(report_id, uid, is_dev=is_dev)

    # Enforce report ownership for non-dev users
    if not is_dev and rep.get("uid") and rep["uid"] != uid:
        raise ForbiddenError("You are not authorized to download this report metadata.")

    json_path = rep.get("json_path")
    if not json_path or not report_generator.is_valid_json_file(json_path):
        logger.info("JSON report artifact missing or invalid for %s. Regenerating...", report_id)
        target_aid = rep.get("analysis_id") or report_id
        analysis = db.get_analysis(target_aid)
        if not analysis:
            raise NotFoundError(f"Underlying analysis for report '{report_id}' not found.")
        
        rep = report_generator.generate_report_artifacts(analysis)
        rep["uid"] = uid
        db.save_report(rep)
        json_path = rep.get("json_path")

    if not json_path or not os.path.exists(json_path) or not report_generator.is_valid_json_file(json_path):
        raise ReportGenerationFailedError("Failed to produce a verified JSON structured artifact.")

    raw_filename = rep.get("json_filename") or f"Satya_Dristi_Analysis_{report_id}.json"
    clean_filename = sanitize_filename(raw_filename)
    if not clean_filename.startswith("Satya_Dristi_"):
        clean_filename = f"Satya_Dristi_Analysis_{clean_filename}"
    if not clean_filename.lower().endswith(".json"):
        clean_filename += ".json"

    return FileResponse(
        path=json_path,
        media_type="application/json",
        filename=clean_filename,
        headers={
            "Content-Type": "application/json",
            "Content-Disposition": f'attachment; filename="{clean_filename}"'
        }
    )

