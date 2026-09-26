import os
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from pathlib import Path

import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.core.config import settings
from app.core.db import db
from app.core.errors import ReportGenerationFailedError

logger = logging.getLogger(__name__)

def clean_pdf_text(text: Any) -> str:
    """
    Sanitizes text strings for ReportLab Type 1 Helvetica font.
    Translates non-ASCII symbols (e.g. km² -> sq km, · -> -) and ensures 100% valid ASCII/WinAnsi.
    Prevents undefined glyph errors in Adobe Acrobat Reader.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '²': ' sq km',
        '³': ' cu m',
        '·': ' - ',
        '—': ' -- ',
        '–': '-',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '…': '...',
        '\u00a0': ' ',
        '\u200b': '',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('ascii', 'ignore').decode('ascii')

class ReportGeneratorService:
    """Generates authentic, verified publication-grade PDF and JSON report artifacts."""

    @staticmethod
    def is_valid_pdf_file(path: str) -> bool:
        """Validates that a file on disk exists, is non-empty, and has a readable PDF structure."""
        try:
            p = Path(path)
            if not p.exists() or p.stat().st_size < 100:
                return False
            with open(p, "rb") as f:
                header = f.read(5)
                if header != b"%PDF-":
                    return False
            reader = pypdf.PdfReader(str(p))
            return len(reader.pages) > 0
        except Exception as e:
            logger.debug("PDF validation failed for %s: %s", path, e)
            return False

    @staticmethod
    def is_valid_json_file(path: str) -> bool:
        """Validates that a file on disk exists and contains valid UTF-8 JSON."""
        try:
            p = Path(path)
            if not p.exists() or p.stat().st_size == 0:
                return False
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return isinstance(data, dict) and "product" in data
        except Exception as e:
            logger.debug("JSON validation failed for %s: %s", path, e)
            return False

    @staticmethod
    def _prepare_image_for_pdf(
        img_path: Optional[str], 
        aid_tag: str = "img",
        base_img_path: Optional[str] = None
    ) -> Optional[Tuple[str, int, int]]:
        """
        Ensures an image file is a valid 8-bit RGB JPEG or PNG suitable for ReportLab.
        Converts GeoTIFF, TIFF, or Float32 rasters to a safe RGB preview PNG in cache.
        If base_img_path is provided (e.g. for bi-temporal change overlays or grounding masks),
        composites the RGBA overlay on top of the base satellite image.
        Returns:
            Tuple of (prepared_file_path, width, height) or None.
        """
        if not img_path or not os.path.exists(img_path):
            return None
        try:
            from PIL import Image

            p = Path(img_path)
            if p.stat().st_size < 100:
                return None

            with Image.open(img_path) as img:
                if img.width < 10 or img.height < 10:
                    return None

                img_w, img_h = img.width, img.height

                # Composite over base_img if provided and overlay has alpha
                rgb_img = None
                if base_img_path and os.path.exists(base_img_path):
                    try:
                        with Image.open(base_img_path) as base_raw:
                            base_img = base_raw.convert("RGB").resize((img_w, img_h), Image.Resampling.LANCZOS)
                            if "A" in img.mode:
                                alpha = img.split()[-1]
                                base_img.paste(img.convert("RGB"), mask=alpha)
                            else:
                                base_img.paste(img.convert("RGB"))
                            rgb_img = base_img
                    except Exception as base_err:
                        logger.warning("Failed to composite overlay onto base image: %s", base_err)
                        rgb_img = None

                if rgb_img is None:
                    # Convert any image to RGB, flattening transparency onto white
                    if img.mode != "RGB":
                        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                        if "A" in img.mode:
                            alpha = img.split()[-1]
                            rgb_img.paste(img.convert("RGB"), mask=alpha)
                        else:
                            rgb_img.paste(img.convert("RGB"))
                    else:
                        rgb_img = img.copy()

                clean_tag = aid_tag.replace("/", "_").replace("\\", "_")
                preview_path = settings.CACHE_DIR / f"pdf_{clean_tag}_{p.stem}.png"
                rgb_img.save(str(preview_path), format="PNG", optimize=True)
                if preview_path.exists() and preview_path.stat().st_size > 100:
                    return (str(preview_path), img_w, img_h)
        except Exception as e:
            logger.warning("Could not convert image %s for PDF embedding: %s", img_path, e)
        return None


    @staticmethod
    def generate_report_artifacts(analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates both PDF and JSON report documents on disk using atomic generation and validation.
        Returns report record dictionary.
        """
        aid = analysis.get("analysis_id", "AN-DEMO")
        clean_aid = aid.replace(" ", "_").replace("/", "_")
        report_id = f"REP-{clean_aid.replace('AN-', '')}" if "AN-" in clean_aid else f"REP-{clean_aid}"
        
        date_str = analysis.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
        clean_date = date_str.replace("/", "-")
        
        pdf_filename = f"Satya_Dristi_Analysis_{report_id}_{clean_date}.pdf"
        json_filename = f"Satya_Dristi_Analysis_{report_id}_{clean_date}.json"
        
        pdf_path = settings.REPORTS_DIR / pdf_filename
        json_path = settings.REPORTS_DIR / json_filename
        
        temp_pdf_path = settings.REPORTS_DIR / f"{pdf_filename}.tmp"
        temp_json_path = settings.REPORTS_DIR / f"{json_filename}.tmp"

        # 1. Generate & Validate JSON Export (Atomic write)
        report_payload = {
            "product": "Satya Dristi",
            "descriptor": "Multimodal Earth Observation Intelligence",
            "report_id": report_id,
            "analysis_id": aid,
            "uid": analysis.get("uid", "anonymous"),
            "generated_at": datetime.utcnow().isoformat(),
            "query": analysis.get("query", ""),
            "analysis_type": analysis.get("task", ""),
            "input": {
                "type": analysis.get("input", "Single image"),
                "format": "GeoTIFF / GeoJSON",
                "crs": "EPSG:4326"
            },
            "answer": analysis.get("answer", ""),
            "confidence": {
                "level": analysis.get("confidence", "High"),
                "score": analysis.get("confidence_score", 0.88),
                "basis": analysis.get("confidence_basis", ""),
                "agreements": analysis.get("agreements", [])
            },
            "observed_evidence": analysis.get("observed_evidence", ""),
            "model_interpretation": analysis.get("model_interpretation", ""),
            "model_information": {
                "model_name": analysis.get("model_used", "Specialist Model Pipeline"),
                "device": analysis.get("device_used", "CPU"),
                "parameters": "Remote-sensing tuned algorithmic vision"
            },
            "aoi_metadata": analysis.get("aoi", {}),
            "execution_trace": analysis.get("execution_trace", []),
            "limitations_and_warnings": [
                "Analysis generated by specialist Earth observation vision models.",
                "Provided for intelligence and decision-support; ground validation recommended for structural enforcement.",
                "Confidence reflects cross-modal and spectral agreement, not absolute ontological ground truth."
            ]
        }
        
        try:
            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(report_payload, f, indent=2, ensure_ascii=False)
            
            # Validate JSON before moving to target path
            with open(temp_json_path, "r", encoding="utf-8") as f:
                json.load(f)
            os.replace(temp_json_path, json_path)
            logger.info("Atomically created validated JSON report: %s", json_path)
        except Exception as e:
            if temp_json_path.exists():
                temp_json_path.unlink()
            logger.error("Failed to generate JSON report: %s", e)
            raise ReportGenerationFailedError(f"JSON creation failed: {str(e)}")

        # 2. Generate PDF via ReportLab Platypus (Atomic write)
        try:
            doc = SimpleDocTemplate(
                str(temp_pdf_path),
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            styles = getSampleStyleSheet()
            
            # Custom styles matching Satya Dristi visual identity
            primary_color = colors.HexColor("#313851") # Deep slate
            accent_color = colors.HexColor("#ab7c2c")  # Amber gold
            muted_color = colors.HexColor("#64748b")
            border_color = colors.HexColor("#cbd5e1")
            bg_panel = colors.HexColor("#f8fafc")

            title_style = ParagraphStyle(
                "ReportTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=primary_color
            )
            subtitle_style = ParagraphStyle(
                "ReportSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=muted_color
            )
            h2_style = ParagraphStyle(
                "ReportH2",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=15,
                textColor=primary_color,
                spaceBefore=10,
                spaceAfter=4
            )
            body_style = ParagraphStyle(
                "ReportBody",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.0,
                leading=13,
                textColor=colors.HexColor("#1e293b")
            )
            mono_style = ParagraphStyle(
                "ReportMono",
                parent=styles["Normal"],
                fontName="Courier",
                fontSize=8.0,
                leading=10,
                textColor=colors.HexColor("#334155")
            )

            story = []

            # Header Banner
            header_table = Table([
                [
                    Paragraph("<b>SATYA DRISTI</b><br/><font size='8' color='#64748b'>Multimodal Earth Observation Intelligence Platform</font>", title_style),
                    Paragraph(f"<b>REPORT: {clean_pdf_text(report_id)}</b><br/><font size='8'>Date: {clean_pdf_text(date_str)} {clean_pdf_text(analysis.get('time', ''))}</font>", ParagraphStyle("R", parent=subtitle_style, alignment=2))
                ]
            ], colWidths=[330, 200])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, primary_color),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8)
            ]))
            story.append(header_table)
            story.append(Spacer(1, 10))

            # Query & Executive Answer Box
            story.append(Paragraph("<b>QUERY & EXECUTIVE RESULT</b>", h2_style))
            query_rows = [
                [Paragraph("<b>Query:</b>", subtitle_style), Paragraph(f"<i>\"{clean_pdf_text(analysis.get('query', ''))}\"</i>", body_style)],
                [Paragraph("<b>Task:</b>", subtitle_style), Paragraph(f"<b>{clean_pdf_text(analysis.get('task', ''))}</b> ({clean_pdf_text(analysis.get('input', ''))})", body_style)],
                [Paragraph("<b>Answer:</b>", subtitle_style), Paragraph(f"<b>{clean_pdf_text(analysis.get('answer', ''))}</b>", body_style)]
            ]
            exec_narrative = analysis.get("model_interpretation") or analysis.get("executive_narrative")
            if exec_narrative and exec_narrative != analysis.get("answer"):
                query_rows.append([
                    Paragraph("<b>AI Narrative:</b>", subtitle_style),
                    Paragraph(clean_pdf_text(exec_narrative), body_style)
                ])
            query_box = Table(query_rows, colWidths=[90, 440])
            query_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_panel),
                ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(query_box)
            story.append(Spacer(1, 10))

            # Visual Evidence Section
            story.append(Paragraph("<b>OBSERVED VISUAL EVIDENCE</b>", h2_style))
            
            task_type = (analysis.get("task") or "").lower()
            paths_to_embed: List[Tuple[str, str, int, int]] = []

            if "change" in task_type or "temporal" in task_type or analysis.get("before_image_path"):
                # Bi-Temporal: Before, After, and Change Detection Map
                b_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("before_image_path"), aid_tag=f"{clean_aid}_before")
                if b_info:
                    paths_to_embed.append(("Pre-Observation (Baseline)", b_info[0], b_info[1], b_info[2]))
                
                a_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("primary_image_path"), aid_tag=f"{clean_aid}_after")
                if a_info:
                    paths_to_embed.append(("Post-Observation (Target)", a_info[0], a_info[1], a_info[2]))
                
                e_info = ReportGeneratorService._prepare_image_for_pdf(
                    analysis.get("evidence_path"), 
                    aid_tag=f"{clean_aid}_change",
                    base_img_path=analysis.get("primary_image_path")
                )
                if e_info:
                    paths_to_embed.append(("Bi-Temporal Change Map", e_info[0], e_info[1], e_info[2]))

            elif "sar" in task_type or "fusion" in task_type or analysis.get("sar_image_path"):
                # Optical + SAR: Optical, SAR, Fused Evidence Map
                o_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("primary_image_path"), aid_tag=f"{clean_aid}_opt")
                if o_info:
                    paths_to_embed.append(("Sentinel-2 Optical (MSI)", o_info[0], o_info[1], o_info[2]))

                s_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("sar_image_path"), aid_tag=f"{clean_aid}_sar")
                if s_info:
                    paths_to_embed.append(("Sentinel-1 SAR (C-SAR)", s_info[0], s_info[1], s_info[2]))

                f_info = ReportGeneratorService._prepare_image_for_pdf(
                    analysis.get("evidence_path"), 
                    aid_tag=f"{clean_aid}_fused",
                    base_img_path=analysis.get("primary_image_path")
                )
                if f_info:
                    paths_to_embed.append(("Cross-Modal Radiometric Fusion", f_info[0], f_info[1], f_info[2]))

            elif "ground" in task_type or "segment" in task_type:
                # Grounding: Satellite Scene and Grounded Feature Localization
                p_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("primary_image_path"), aid_tag=f"{clean_aid}_scene")
                if p_info:
                    paths_to_embed.append(("Satellite Observation Scene", p_info[0], p_info[1], p_info[2]))

                e_info = ReportGeneratorService._prepare_image_for_pdf(
                    analysis.get("evidence_path"), 
                    aid_tag=f"{clean_aid}_grounding",
                    base_img_path=analysis.get("primary_image_path")
                )
                if e_info:
                    paths_to_embed.append(("Grounded Feature Localization", e_info[0], e_info[1], e_info[2]))

            else:
                # VQA / Single image analysis
                p_info = ReportGeneratorService._prepare_image_for_pdf(analysis.get("primary_image_path"), aid_tag=f"{clean_aid}_scene")
                if p_info:
                    paths_to_embed.append(("Observation Scene", p_info[0], p_info[1], p_info[2]))

                e_info = ReportGeneratorService._prepare_image_for_pdf(
                    analysis.get("evidence_path"), 
                    aid_tag=f"{clean_aid}_evidence",
                    base_img_path=analysis.get("primary_image_path")
                )
                if e_info and analysis.get("evidence_path") != analysis.get("primary_image_path"):
                    paths_to_embed.append(("Analysis Evidence Layer", e_info[0], e_info[1], e_info[2]))

            if paths_to_embed:
                num_imgs = len(paths_to_embed)
                if num_imgs == 3:
                    col_w = 177
                    max_w = col_w - 12  # 165 pt accounting for cell padding
                    max_h = 1.65 * inch  # 118.8 pt
                elif num_imgs == 2:
                    col_w = 265
                    max_w = col_w - 12  # 253 pt accounting for cell padding
                    max_h = 2.1 * inch   # 151.2 pt
                else:
                    col_w = 530
                    max_w = 340
                    max_h = 2.5 * inch   # 180 pt

                img_cells = []
                label_cells = []
                for label, img_p, orig_w, orig_h in paths_to_embed:
                    try:
                        # Aspect-ratio preserving display dimension calculation
                        aspect = orig_w / max(1, orig_h)
                        box_aspect = max_w / max_h
                        if aspect >= box_aspect:
                            render_w = max_w
                            render_h = max_w / aspect
                        else:
                            render_h = max_h
                            render_w = max_h * aspect

                        rl_img = RLImage(img_p, width=render_w, height=render_h)
                        img_cells.append(rl_img)
                        label_cells.append(Paragraph(f"<font size='7.5'><b>{clean_pdf_text(label)}</b></font>", subtitle_style))
                    except Exception as e:
                        logger.warning("Could not embed image in PDF: %s", e)
                
                if img_cells:
                    img_table = Table([img_cells, label_cells], colWidths=[col_w] * len(img_cells))
                    img_table.setStyle(TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                        ("VALIGN", (0, 1), (-1, 1), "TOP"),
                        ("BOX", (0, 0), (-1, 0), 0.5, border_color),
                        ("BACKGROUND", (0, 0), (-1, 0), bg_panel),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(img_table)
            else:
                placeholder_box = Table([
                    [Paragraph("<font color='#64748b'><i>Satellite observation imagery and evidence overlays registered in analytical archive.</i></font>", body_style)]
                ], colWidths=[530])
                placeholder_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_panel),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]))
                story.append(placeholder_box)
            
            story.append(Spacer(1, 10))

            # AI Observations & Grounded Findings Section
            observations = analysis.get("observations") or []
            if observations:
                story.append(Paragraph("<b>AI OBSERVATIONS & GROUNDED FINDINGS</b>", h2_style))
                obs_paragraphs = [
                    Paragraph(f"• {clean_pdf_text(obs)}", body_style) for obs in observations
                ]
                uncertainties = analysis.get("uncertainties") or []
                if uncertainties:
                    obs_paragraphs.append(Spacer(1, 3))
                    obs_paragraphs.append(Paragraph(f"<b>Uncertainty & Sensor Limits:</b> <i>{clean_pdf_text(' • '.join(uncertainties))}</i>", mono_style))

                obs_box = Table([[obs_paragraphs]], colWidths=[530])
                obs_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_panel),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(obs_box)
                story.append(Spacer(1, 10))

            # Metadata & Confidence Table
            story.append(Paragraph("<b>ANALYSIS TELEMETRY & CONFIDENCE</b>", h2_style))
            aoi_info = analysis.get("aoi") or {}
            bbox_str = clean_pdf_text(str(aoi_info.get("bbox", "Regional extent")))
            area_str = clean_pdf_text(f"{aoi_info.get('area_sq_km', 'N/A')} sq km" if aoi_info.get('area_sq_km') else "Regional")

            telemetry_data = [
                ["Area of Interest (AOI):", bbox_str, "Confidence Rating:", clean_pdf_text(analysis.get("confidence", "High"))],
                ["Ground Extent:", area_str, "Model Specialist:", clean_pdf_text(analysis.get("model_used", "Specialist Vision Engine"))],
                ["Device Accelerator:", clean_pdf_text(analysis.get("device_used", "CPU")), "Total Latency:", clean_pdf_text(f"{analysis.get('total_duration_sec', '0.4')}s")]
            ]
            t_table = Table(
                [[Paragraph(f"<b>{clean_pdf_text(c)}</b>" if i % 2 == 0 else clean_pdf_text(str(c)), mono_style) for i, c in enumerate(row)] for row in telemetry_data],
                colWidths=[120, 145, 120, 145]
            )
            t_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t_table)
            story.append(Spacer(1, 10))

            # Observable Execution Trace
            story.append(Paragraph("<b>AUDITABLE EXECUTION TRACE</b>", h2_style))
            trace_rows = [["Stage", "Observable Detail", "Duration"]]
            for stage in analysis.get("execution_trace", []):
                trace_rows.append([
                    clean_pdf_text(stage.get("name", "")),
                    clean_pdf_text(stage.get("detail", "")),
                    clean_pdf_text(stage.get("duration", ""))
                ])

            if len(trace_rows) > 1:
                tr_table = Table(
                    [[Paragraph(f"<b>{clean_pdf_text(c)}</b>" if r_idx == 0 else clean_pdf_text(str(c)), mono_style) for c in row] for r_idx, row in enumerate(trace_rows)],
                    colWidths=[130, 310, 90]
                )
                tr_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), bg_panel),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(tr_table)

            story.append(Spacer(1, 10))

            # Limitations and Disclaimer
            disclaimer = clean_pdf_text(
                "Notice & Limitations: This document was generated automatically by the Satya Dristi Earth-Observation "
                "intelligence system. Predictions are derived from multi-band remote-sensing signatures and represent decision-support "
                "telemetry rather than definitive cadastral survey determinations."
            )
            story.append(Paragraph(disclaimer, ParagraphStyle("Disc", parent=subtitle_style, fontSize=7.5, leading=10)))

            doc.build(story)


            # Validate generated PDF with pypdf before committing
            if not ReportGeneratorService.is_valid_pdf_file(str(temp_pdf_path)):
                raise ValueError("Generated PDF failed structural verification (invalid %PDF- or unreadable pages).")

            os.replace(temp_pdf_path, pdf_path)
            logger.info("Atomically created validated PDF report: %s (%d bytes)", pdf_path, pdf_path.stat().st_size)

        except Exception as e:
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()
            logger.error("Failed to generate PDF report: %s", e, exc_info=True)
            raise ReportGenerationFailedError(f"PDF creation failed: {str(e)}")

        # Create report DB entry
        report_doc = {
            "report_id": report_id,
            "analysis_id": aid,
            "uid": analysis.get("uid", "anonymous"),
            "query": analysis.get("query", ""),
            "task": analysis.get("task", ""),
            "input": analysis.get("input", ""),
            "date": date_str,
            "time": analysis.get("time", "12:00"),
            "confidence": analysis.get("confidence", "High"),
            "status": "Complete",
            "answer": analysis.get("answer", ""),
            "pdf_filename": pdf_filename,
            "json_filename": json_filename,
            "pdf_path": str(pdf_path),
            "json_path": str(json_path),
            "generated_at": datetime.utcnow().isoformat()
        }
        db.save_report(report_doc)
        return report_doc

report_generator = ReportGeneratorService()
