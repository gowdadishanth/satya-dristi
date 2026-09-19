import os
import shutil
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# =============================================================================
# PATH CONSTANTS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "docs"
DIAGRAMS_DIR = Path(__file__).resolve().parent / "diagrams"
OUTPUT_DOCX_ROOT = BASE_DIR / "Satya_Dristi_Complete_Technical_Report.docx"
OUTPUT_DOCX_DOCS = DOCS_DIR / "Satya_Dristi_Complete_Technical_Report.docx"

# =============================================================================
# SATYA DRISTI BRAND COLOR PALETTE
# =============================================================================
HEX_PRIMARY = "313851"     # Deep Slate (Primary accent / headers)
HEX_ACCENT = "AB7C2C"      # Amber Gold (Action highlights)
HEX_SECONDARY = "4F6F8A"   # Steel Blue (Subheadings)
HEX_NEUTRAL = "C2CBD3"     # Neutral Silver (Borders / separators)
HEX_BG = "F6F3ED"          # Canvas Cream (Page / card background)
HEX_DARK = "1E293B"        # Body Text (High readability)
HEX_LIGHT_BG = "F8FAFC"    # Alternate Row Shading
HEX_BORDER = "CBD5E1"      # Clean Grid Border
HEX_CALLOUT_BG = "FBF9F5"  # Callout box fill

COLOR_PRIMARY = RGBColor(49, 56, 81)
COLOR_ACCENT = RGBColor(171, 124, 44)
COLOR_SECONDARY = RGBColor(79, 111, 138)
COLOR_DARK = RGBColor(30, 41, 59)
COLOR_MUTED = RGBColor(100, 116, 139)

# =============================================================================
# XML & STYLING HELPERS
# =============================================================================
def format_cell(cell, bg_color=None, top=80, bottom=80, left=120, right=120, borders=None, v_align='center'):
    """
    Applies background, margins, borders, and vertical alignment in strict ECMA-376 schema sequence:
    1. tcW
    2. tcBorders
    3. shd
    4. tcMar
    5. vAlign
    """
    tcPr = cell._tc.get_or_add_tcPr()
    
    # Remove existing conflicting elements to ensure strict order
    for tag in ['tcBorders', 'shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign']:
        existing = tcPr.find(qn(f'w:{tag}'))
        if existing is not None:
            tcPr.remove(existing)
            
    # 1. tcBorders (must precede shd and tcMar)
    if borders:
        tcBorders = OxmlElement('w:tcBorders')
        for edge in ['top', 'left', 'bottom', 'right']:
            b_def = borders.get(edge)
            if b_def:
                b_elem = OxmlElement(f'w:{edge}')
                b_elem.set(qn('w:val'), b_def.get('val', 'single'))
                b_elem.set(qn('w:sz'), str(b_def.get('sz', 4)))
                b_elem.set(qn('w:space'), '0')
                b_elem.set(qn('w:color'), b_def.get('color', HEX_BORDER))
                tcBorders.append(b_elem)
        tcPr.append(tcBorders)

    # 2. shd (must follow tcBorders, precede tcMar)
    if bg_color:
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), bg_color)
        tcPr.append(shd)

    # 3. tcMar (must follow shd)
    tcMar = OxmlElement('w:tcMar')
    for edge, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        m = OxmlElement(f'w:{edge}')
        m.set(qn('w:w'), str(val))
        m.set(qn('w:type'), 'dxa')
        tcMar.append(m)
    tcPr.append(tcMar)

    # 4. vAlign (must follow tcMar)
    if v_align:
        vAlign = OxmlElement('w:vAlign')
        vAlign.set(qn('w:val'), v_align)
        tcPr.append(vAlign)

def add_styled_table(doc, headers, data, col_widths=None):
    """Renders an executive-styled table with formatted headers and alternating row fills."""
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        format_cell(hdr_cells[i], bg_color=HEX_PRIMARY, top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(9.0)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

    # Data Rows
    for r_idx, row_values in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = HEX_LIGHT_BG if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx, val in enumerate(row_values):
            row_cells[c_idx].text = str(val)
            format_cell(row_cells[c_idx], bg_color=bg_color, top=80, bottom=80, left=120, right=120,
                        borders={'bottom': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                                 'top': {'sz': 4, 'val': 'single', 'color': HEX_BORDER}})
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(8.5)
                run.font.color.rgb = COLOR_DARK
                if str(val) in ["IMPLEMENTED", "PASSED", "Low", "Secured"]:
                    run.font.bold = True
                elif str(val) in ["NOT IMPLEMENTED", "FAIL", "Critical", "High"]:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(180, 40, 40)

    # Apply column widths if provided
    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    # Spacing after table
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(2)
    p_after.paragraph_format.space_after = Pt(6)
    return table

def add_callout(doc, text, prefix="IMPORTANT NOTE: "):
    """Creates an elegant callout box with a thick left accent border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.3)
    format_cell(cell, bg_color=HEX_CALLOUT_BG, top=120, bottom=120, left=180, right=150,
                borders={'left': {'sz': 24, 'val': 'single', 'color': HEX_ACCENT},
                         'top': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                         'bottom': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                         'right': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL}})
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run_pre = p.add_run(prefix)
    run_pre.bold = True
    run_pre.font.name = "Calibri"
    run_pre.font.size = Pt(9.0)
    run_pre.font.color.rgb = COLOR_ACCENT
    run_txt = p.add_run(text)
    run_txt.font.name = "Calibri"
    run_txt.font.size = Pt(9.0)
    run_txt.font.color.rgb = COLOR_DARK
    
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_str):
    """Creates a formatted code/monospaced block."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.3)
    format_cell(cell, bg_color="F1F5F9", top=100, bottom=100, left=150, right=150,
                borders={'left': {'sz': 16, 'val': 'single', 'color': HEX_SECONDARY},
                         'top': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                         'bottom': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                         'right': {'sz': 4, 'val': 'single', 'color': HEX_BORDER}})
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(code_str)
    run.font.name = "Consolas"
    run.font.size = Pt(8.0)
    run.font.color.rgb = RGBColor(30, 41, 59)
    
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_after = Pt(4)

def add_heading_1(doc, text):
    """Heading 1 styled with primary palette and bottom accent."""
    p = doc.add_paragraph(style='Heading 1')
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.runs[0] if p.runs else p.add_run(text)
    run.text = text
    run.font.name = "Calibri"
    run.font.size = Pt(16.0)
    run.font.bold = True
    run.font.color.rgb = COLOR_PRIMARY
    return p

def add_heading_2(doc, text):
    """Heading 2 styled with steel blue palette."""
    p = doc.add_paragraph(style='Heading 2')
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.runs[0] if p.runs else p.add_run(text)
    run.text = text
    run.font.name = "Calibri"
    run.font.size = Pt(12.5)
    run.font.bold = True
    run.font.color.rgb = COLOR_SECONDARY
    return p

def add_heading_3(doc, text):
    """Heading 3 styled with dark slate and slight italic."""
    p = doc.add_paragraph(style='Heading 3')
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.runs[0] if p.runs else p.add_run(text)
    run.text = text
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.bold = True
    run.font.color.rgb = COLOR_DARK
    return p

def add_p(doc, text, bold_prefix=""):
    """Adds a standard body paragraph with 1.15 line spacing."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(9.5)
        r_pre.font.color.rgb = COLOR_PRIMARY
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(9.5)
    run.font.color.rgb = COLOR_DARK
    return p

def add_bullet(doc, text, bold_prefix=""):
    """Adds a clean list item."""
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(9.5)
        r_pre.font.color.rgb = COLOR_DARK
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(9.5)
    run.font.color.rgb = COLOR_DARK
    return p

def add_figure(doc, image_name, caption):
    """Inserts a centered diagram and an italicized caption."""
    img_path = DIAGRAMS_DIR / image_name
    if img_path.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(3)
        run = p_img.add_run()
        run.add_picture(str(img_path), width=Inches(6.3))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(8)
        r_cap = p_cap.add_run(caption)
        r_cap.font.name = "Calibri"
        r_cap.font.size = Pt(8.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = COLOR_MUTED

def insert_toc_field(doc):
    """Inserts a schema-valid Microsoft Word Table of Contents field inside runs (w:r)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    
    # Run 1: begin field
    r1 = p.add_run()
    fld1 = OxmlElement('w:fldChar')
    fld1.set(qn('w:fldCharType'), 'begin')
    r1._r.append(fld1)
    
    # Run 2: field instruction
    r2 = p.add_run()
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    r2._r.append(instr)
    
    # Run 3: separator
    r3 = p.add_run()
    fld2 = OxmlElement('w:fldChar')
    fld2.set(qn('w:fldCharType'), 'separate')
    r3._r.append(fld2)
    
    # Run 4: instruction text
    r4 = p.add_run('Right-click this field and select "Update Field" to refresh the dynamic Table of Contents.')
    r4.font.name = "Calibri"
    r4.font.size = Pt(9.0)
    r4.font.italic = True
    r4.font.color.rgb = COLOR_MUTED
    
    # Run 5: end field
    r5 = p.add_run()
    fld3 = OxmlElement('w:fldChar')
    fld3.set(qn('w:fldCharType'), 'end')
    r5._r.append(fld3)

# =============================================================================
# MAIN BUILDER LOGIC
# =============================================================================
def build_document():
    print("Initializing Document...")
    doc = Document()

    # Configure A4 page & 1-inch margins
    sections = doc.sections
    for s in sections:
        s.page_width = Inches(8.27)    # A4 Width
        s.page_height = Inches(11.69)  # A4 Height
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

        # Header
        hdr = s.header
        p_hdr = hdr.paragraphs[0]
        p_hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_hdr = p_hdr.add_run("Satya Dristi · Multimodal Earth Observation Intelligence | Complete Technical Project Report")
        r_hdr.font.name = "Calibri"
        r_hdr.font.size = Pt(8.0)
        r_hdr.font.color.rgb = COLOR_MUTED

        # Footer
        ftr = s.footer
        p_ftr = ftr.paragraphs[0]
        p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_ftr = p_ftr.add_run("Confidential · Smart India Hackathon (SIH 2026) Technical Submission · Problem Statement SIH26167")
        r_ftr.font.name = "Calibri"
        r_ftr.font.size = Pt(8.0)
        r_ftr.font.color.rgb = COLOR_MUTED

    # =========================================================================
    # 1. PROFESSIONAL TITLE PAGE
    # =========================================================================
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(36)

    # Sub-brand Header
    p_pre = doc.add_paragraph()
    p_pre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_pre.paragraph_format.space_after = Pt(6)
    r_pre = p_pre.add_run("SMART INDIA HACKATHON 2026 · TECHNICAL PROJECT REPORT")
    r_pre.font.name = "Calibri"
    r_pre.font.size = Pt(10.5)
    r_pre.font.bold = True
    r_pre.font.color.rgb = COLOR_ACCENT

    # Main Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(8)
    r_title = p_title.add_run("SATYA DRISTI")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(34.0)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(20)
    r_sub = p_sub.add_run("Multimodal Earth Observation Intelligence Platform\nNatural-Language Geospatial Understanding, Optical + SAR Fusion & Visual Grounding")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(13.0)
    r_sub.font.italic = True
    r_sub.font.color.rgb = COLOR_SECONDARY

    # Metadata Box Table
    meta_headers = ["Project Metadata Field", "Engineering Specification / Record"]
    meta_data = [
        ["Document Title", "Satya Dristi: Complete Technical Implementation & Architecture Report"],
        ["Product Identity", "Satya Dristi (Multimodal Earth Observation Intelligence)"],
        ["Problem Statement ID", "SIH26167 · Ministry / Department of Space & Geospatial Intelligence"],
        ["Team Identifier", "SIH-2026-TEAM-VERITAS"],
        ["Author Role", "Senior Technical Documentation Engineer & Lead Geospatial Architect"],
        ["Target Audience", "Faculty Evaluators, SIH Jury Members, Technical Reviewers, DevOps Engineers"],
        ["Technical Classification", "Algorithmic Computer Vision, STAC Ingestion & Geospatial Intelligence"],
        ["System Version", "v1.4.0-production-release (Verified Commit Baseline)"],
        ["Release Date", "September 17, 2026"],
        ["Implementation Standard", "Full Source Verification (Factually Grounded; Zero Hallucinations)"],
    ]
    add_styled_table(doc, meta_headers, meta_data, col_widths=[2.2, 4.1])

    p_note = doc.add_paragraph()
    p_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_note.paragraph_format.space_before = Pt(16)
    r_n = p_note.add_run("NOTICE: This technical report documents the verified source implementation of the Satya Dristi platform.\n"
                         "Every subsystem is classified strictly under factual implementation criteria: IMPLEMENTED, PARTIALLY IMPLEMENTED, "
                         "MOCK / DEMONSTRATION, or NOT IMPLEMENTED.")
    r_n.font.name = "Calibri"
    r_n.font.size = Pt(8.5)
    r_n.font.italic = True
    r_n.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # =========================================================================
    # 2. TABLE OF CONTENTS
    # =========================================================================
    add_heading_1(doc, "Table of Contents")
    add_p(doc, "This document contains a comprehensive 45-section technical audit of Satya Dristi. "
               "The document is fully navigable via Microsoft Word's Navigation Pane using Heading 1, Heading 2, and Heading 3 styles.")

    insert_toc_field(doc)

    add_heading_2(doc, "Executive Section Guide")
    toc_items = [
        ("1.0 Executive Summary", "Core purpose, user persona, high-level workflow, and implementation status"),
        ("2.0 Problem Statement & Background", "Remote sensing fragmentation, optical limitations, SAR necessity, and VLM gaps"),
        ("3.0 System Technical Objectives", "Catalogue discovery, AOI bounding, VQA, grounding, change, and fusion goals"),
        ("4.0 Complete System Overview & Architecture", "End-to-end multi-tier pipeline and architectural component interaction"),
        ("5.0 System Architecture by Layer", "Detailed breakdown of Presentation, Application, Geospatial, ML, and Data tiers"),
        ("6.0 Authentication & User Identity Subsystem", "Firebase JWT verification, dev-token offline decoding, and UID multi-tenancy"),
        ("7.0 Frontend Technical Implementation", "React 19, TypeScript, Tailwind CSS v4, Leaflet 1.9.4, and state structure"),
        ("8.0 Frontend Page-by-Page Inventory", "Complete documentation of Dashboard, Analyze, History, Reports, and Legal pages"),
        ("9.0 Analyze Workspace 3-Column Desktop Grid", "Control panel, Leaflet center map dominance, and 2-row uncramped search controls"),
        ("10.0 Analysis Modes Specification", "Single Image VQA, Optical + SAR Fusion, and Before + After Change Detection"),
        ("11.0 Global Map & STAC Discovery", "Esri World Imagery, AWS Earth Search, Copernicus Ecosystem, and year filtering"),
        ("12.0 Area of Interest (AOI) Engine", "Interactive drag-to-draw, Shapely GeoJSON validation, and PyProj EPSG:6933 math"),
        ("13.0 Satellite Ingestion & Processing Pipeline", "Sentinel-2 MSI L2A, Sentinel-1 C-SAR GRD, raster cropping, and radar dB transform"),
        ("14.0 Image Processing & Band Manipulation", "Multi-band GeoTIFF handling, RGB composite generation, and NoData filtering"),
        ("15.0 AI / ML Specialist Architecture", "Memory-aware resource management, device selection, and model execution"),
        ("16.0 Visual Question Answering (VQA)", "Quantitative spectral decomposition, edge density, and linguistic synthesis"),
        ("17.0 Spatial Feature Grounding", "Morphological spectral segmentation, contour extraction, and coordinate bounding"),
        ("18.0 Bi-Temporal Change Detection", "Change Vector Analysis (CVA), structural absdiff, and RGBA change map rendering"),
        ("19.0 Optical + SAR Cross-Modal Fusion", "Dual-polarization backscatter thresholding, double bounce, and specular alignment"),
        ("20.0 Agentic Intent Routing", "Deterministic semantic rule engine classifying queries across 9 task categories"),
        ("21.0 Visual Evidence Canvas & Layer Blending", "Multi-layer inspection canvas, layer opacity blending, and temporal swipe comparison"),
        ("22.0 Confidence Estimation Engine", "Multi-signal composite telemetry scoring, cloud penalties, and agreement vectors"),
        ("23.0 Observable Execution Trace", "Chronological operational milestones, step durations, and transparency boundaries"),
        ("24.0 Database Architecture & Schemas", "Dual-mode repository: Google Cloud Firestore and SQLite LocalDocumentStore"),
        ("25.0 Storage Hierarchy & Lifecycle", "On-disk data segregation: cache, uploads, evidence overlays, and PDF reports"),
        ("26.0 Report Generation Subsystem", "ReportLab Platypus PDF compilation with embedded satellite evidence and JSON export"),
        ("27.0 Historical Analysis Archive", "Persistent analysis indexing, full-text query filtering, and auto-seeding"),
        ("28.0 REST API Specification", "Exhaustive endpoint inventory, schemas, request/response payloads, and database impact"),
        ("29.0 Error Handling Architecture", "Structured error domains, HTTP status codes, and resilient frontend recovery"),
        ("30.0 Performance Benchmarks & Empirical Latency", "Empirical latency measurements across STAC queries, model inference, and report compilation"),
        ("31.0 Test Suite & Validation Evidence", "Pytest unit, integration, and E2E test suite results (12 passed in 31.16s)"),
        ("32.0 Security & Vulnerability Assessment", "Threat evaluation, token handling, path sanitization, and security recommendations"),
        ("33.0 Requirements Traceability Matrix", "Comprehensive mapping from SIH requirements to verified code artifacts"),
        ("34.0 SIH26167 Problem Statement Alignment", "Direct compliance assessment against hackathon problem requirements"),
        ("35.0 Frontend / Backend Gap Analysis", "Audit of unexposed endpoints, missing integrations, and UI synchronizations"),
        ("36.0 Technical Debt Assessment", "Algorithmic fallbacks, in-process queueing, and future refactoring targets"),
        ("37.0 Known System Limitations", "Data resolution bounds, cloud shadow vulnerability, and hardware VRAM constraints"),
        ("38.0 Future Engineering Roadmap", "Pretrained remote-sensing VLM integration, ISRO Bhoonidhi connectors, and Celery queues"),
        ("39.0 Complete Demonstration Walkthroughs", "Step-by-step procedures for Single-Image, Bi-Temporal, and Optical+SAR demos"),
        ("40.0 Developer Setup Instructions", "Clean installation commands for Node.js, Python, venv, and environment configurations"),
        ("41.0 Annotated Project Structure", "Complete directory tree documenting every file and folder in the workspace"),
        ("42.0 Technical Appendices", "Environment variable reference, error hierarchy, and technical glossary"),
        ("43.0 Final Implementation Audit Table", "Real vs Mock vs Partial classification of all system capabilities"),
        ("44.0 Final Technical Verdict", "Objective maturity evaluation and critical remaining engineering priorities"),
    ]

    for title, desc in toc_items:
        p_toc = doc.add_paragraph()
        p_toc.paragraph_format.space_before = Pt(1)
        p_toc.paragraph_format.space_after = Pt(2)
        r_t = p_toc.add_run(title + " — ")
        r_t.bold = True
        r_t.font.name = "Calibri"
        r_t.font.size = Pt(9.0)
        r_t.font.color.rgb = COLOR_PRIMARY
        r_d = p_toc.add_run(desc)
        r_d.font.name = "Calibri"
        r_d.font.size = Pt(8.5)
        r_d.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # =========================================================================
    # 3. EXECUTIVE SUMMARY
    # =========================================================================
    add_heading_1(doc, "1.0 Executive Summary")
    add_p(doc, "Satya Dristi (meaning 'True Vision' in Sanskrit) is an enterprise-grade Earth observation intelligence platform engineered to bridge the gap between complex orbital remote sensing data and actionable decision-making. In contemporary geospatial workflows, extracting insights from satellite imagery requires specialized desktop Geographic Information Systems (GIS) software (e.g., QGIS, ArcGIS, ENVI), manual spatial projection reparameterization, multi-spectral band indexing, and deep domain expertise. Satya Dristi democratizes Earth observation data by pairing natural-language querying with multi-sensor satellite data ingestion, automated area-of-interest (AOI) bounding, spatial visual grounding, bi-temporal change detection, and cross-modal optical-to-SAR fusion.")

    add_callout(doc,
        "CORE VALUE PROPOSITION: Satya Dristi enables analysts, environmental monitors, defense planners, and disaster responders "
        "to formulate plain natural-language inquiries (e.g., 'Quantify urban sprawl between 2022 and 2024' or 'Identify water boundaries "
        "under dense cloud cover') and receive mathematically grounded answers, high-resolution visual evidence masks, transparent execution "
        "milestones, and downloadable publication-grade PDF reports.",
        prefix="CORE CAPABILITY: "
    )

    add_p(doc, "The platform is implemented as a modern decoupled system comprising a reactive TypeScript/React 19 frontend and an asynchronous Python 3.11 / FastAPI backend. Key capabilities currently operational in the codebase include:")
    add_bullet(doc, "Global Earth Observation Explorer: An interactive Leaflet map featuring real Esri World Imagery tiles, multi-year temporal querying (2016 through 2026), and geographic search with auto-centering presets across critical Indian observation corridors.")
    add_bullet(doc, "Spatio-Temporal Asset Ingestion (STAC): Integrated search querying live international STAC catalogues, including AWS Earth Search and the Copernicus Data Space Ecosystem, discovering Sentinel-2 optical and Sentinel-1 radar scenes.")
    add_bullet(doc, "Geodesic Surface Area Processing: Server-side geometry validation and equal-area reprojection using PyProj (EPSG:6933), computing precise ground footprint areas in square kilometers.")
    add_bullet(doc, "Three Dedicated Analysis Modalities: (1) Single-Image VQA with radiometric spectral decomposition; (2) Bi-Temporal Change Vector Analysis (CVA); and (3) Optical + Synthetic Aperture Radar (SAR) cross-modal fusion.")
    add_bullet(doc, "Full Auditability & Evidence Generation: Every analysis generates interactive visual evidence canvases with opacity blending, split-screen swipe sliders, an observable execution trace, heuristic confidence scores, and vector PDF reports compiled via ReportLab Platypus.")

    # =========================================================================
    # 4. PROBLEM STATEMENT & BACKGROUND
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "2.0 Problem Statement & Technical Challenges")
    add_p(doc, "Earth observation satellites continuously image the planet, generating petabytes of open-access data daily. However, utilizing this wealth of information for civil governance, environmental monitoring, disaster mitigation, and tactical intelligence remains severely constrained by several fundamental challenges:")

    add_p(doc, "1. The Optical Imagery Bottleneck (Atmospheric & Cloud Occlusion):", bold_prefix="Atmospheric Vulnerability — ")
    add_p(doc, "Optical multispectral sensors (such as Sentinel-2 MSI) rely on reflected solar radiation in the visible, near-infrared, and shortwave-infrared spectra. Consequently, during monsoon seasons, heavy cloud cover, haze, dust storms, or nighttime, optical sensors suffer near-total data blackout. Vital emergency operations (such as flood inundation tracking) fail precisely when timely intelligence is most critical.")

    add_p(doc, "2. High Complexity of Synthetic Aperture Radar (SAR):", bold_prefix="Radar Complexity — ")
    add_p(doc, "C-band Synthetic Aperture Radar (such as Sentinel-1 C-SAR) operates at microwave wavelengths (~5.6 cm), easily penetrating dense cloud decks, smoke, and darkness. However, interpreting SAR imagery requires complex processing: speckle filtering, radiometric calibration, terrain correction, and understanding geometric phenomena such as layover, foreshortening, specular reflection, and double-bounce corner reflection. Non-specialists cannot effectively interpret raw radar backscatter without automated decision-support tooling.")

    add_p(doc, "3. Domain Failure of Standard Vision-Language Models (VLMs):", bold_prefix="Multimodal Model Domain Gap — ")
    add_p(doc, "Generic Vision-Language Models (e.g., LLaVA, GPT-4V) are trained on consumer photography (perspective projection, eye-level orientation, high-contrast foreground objects). When applied to nadir satellite imagery (orthogonal top-down views, 10-meter pixel scales, non-RGB multispectral reflectance, diffuse boundaries), standard VLMs hallucinate false objects, misjudge scale, and fail to provide spatial bounding.")

    add_p(doc, "4. Lack of Operational Auditability & Explainability:", bold_prefix="Black-Box Unreliability — ")
    add_p(doc, "Mission-critical applications cannot accept raw text answers without verifiable evidence. A response stating 'Built-up infrastructure expanded by 14.2%' is unacceptable without visual evidence overlays, bounding boxes, sensor telemetry, and step-by-step execution metrics.")

    add_heading_2(doc, "2.1 Satya Dristi Engineering Approach")
    add_p(doc, "Satya Dristi addresses these core challenges through four technical pillars:")
    add_bullet(doc, "Cross-Modal Optical + SAR Consensus: Correlating Sentinel-2 surface reflectance with Sentinel-1 calibrated radar backscatter (dB) to validate structural density and water boundaries through dense clouds.")
    add_bullet(doc, "Bi-Temporal Siamese Comparison: Implementing Change Vector Analysis (CVA) magnitude thresholding on observation pairs from 2016 to 2026.")
    add_bullet(doc, "Strict Pixel Grounding: Generating bounding boxes and spatial masks derived directly from radiometric and morphological contour extraction.")
    add_bullet(doc, "Auditable Evidence Overlays: Outputting interactive visual evidence maps so analysts can verify AI conclusions against real pixel data before publishing official reports.")

    # =========================================================================
    # 5. TECHNICAL OBJECTIVES
    # =========================================================================
    add_heading_1(doc, "3.0 System Technical Objectives")
    add_p(doc, "To ensure that Satya Dristi provides verifiable utility, the engineering implementation was scoped to the following verified technical objectives:")
    add_bullet(doc, "Objective 1 (Global Data Discovery): Implement multi-provider STAC catalogue search across AWS Earth Search and Copernicus Data Space with dynamic spatial, temporal (2016-2026), and cloud-cover filtering.")
    add_bullet(doc, "Objective 2 (Interactive AOI Definition): Enable freeform rectangle drag-to-draw on high-resolution satellite basemaps with automatic GeoJSON generation and WGS84-to-EPSG:6933 geodesic ground area calculation.")
    add_bullet(doc, "Objective 3 (Natural Language VQA): Provide a single-image question-answering engine executing radiometric spectral decomposition (vegetation index, water index, Canny structural edge density).")
    add_bullet(doc, "Objective 4 (Visual Grounding): Extract spatial bounding boxes and pixel masks for queried land-cover features using morphological structuring elements and OpenCV contour extraction.")
    add_bullet(doc, "Objective 5 (Bi-Temporal Change Detection): Implement Change Vector Analysis (CVA) computing spectral change magnitude, direction, and structural variation between baseline and target observation scenes.")
    add_bullet(doc, "Objective 6 (Optical + SAR Multimodal Fusion): Resample and align optical reflectance with radar backscatter, converting DN to calibrated decibels and validating features via dielectric/geometric consensus.")
    add_bullet(doc, "Objective 7 (Agentic Orchestration & Audit): Route queries through a deterministic intent classifier and track execution via observable chronological milestones without exposing hidden neural weights.")
    add_bullet(doc, "Objective 8 (Publication-Grade Reporting): Automatically compile vector PDF and structured JSON reports containing metadata, quantitative land-cover breakdowns, and embedded evidence rasters.")
    add_bullet(doc, "Objective 9 (Multi-Tier Persistence): Provide resilient database persistence bridging Google Cloud Firestore in production and thread-safe SQLite in offline development.")

    # =========================================================================
    # 6. COMPLETE SYSTEM OVERVIEW & ARCHITECTURE
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "4.0 Complete System Overview & Architecture")
    add_p(doc, "Satya Dristi is architected as an asynchronous, decoupled multi-tier platform optimized for low-latency interactive geospatial analysis and high-throughput background processing.")

    add_figure(doc, "diagram_system_overview.png", "Figure 1: Satya Dristi End-to-End Multi-Tier System Architecture")

    add_heading_2(doc, "4.1 System Operational Pipeline")
    add_p(doc, "The operational workflow proceeds through the following sequential pipeline:")
    add_p(doc, "1. User Interaction & Query Formulation: The analyst defines an AOI on the global map, selects an observation year (2016-2026), picks an available satellite scene, and enters a natural-language question.")
    add_p(doc, "2. Request Ingestion & Intent Routing: The React 19 frontend transmits the payload to the FastAPI backend. The `TaskRouter` classifies the question into one of nine distinct operational tasks.")
    add_p(doc, "3. Geospatial Processing & Asset Cropping: The `GeospatialProcessor` validates coordinates, computes geodesic area in EPSG:6933, and crops analysis rasters from local cache or STAC providers.")
    add_p(doc, "4. Specialist Model Execution: The `ModelResourceManager` dispatches the workload to the assigned specialist (`VQASpecialist`, `GroundingSpecialist`, `ChangeSpecialist`, or `OpticalSARSpecialist`).")
    add_p(doc, "5. Evidence Generation & Overlay Rendering: Generated masks and overlays are written to disk (`backend/data/evidence/`) as RGBA PNG files and returned to the client.")
    add_p(doc, "6. Audit & Persistence: Analysis results, execution traces, and multi-factor confidence ratings are persisted to Firestore/SQLite and compiled into vector PDF reports.")

    # =========================================================================
    # 7. SYSTEM ARCHITECTURE BY LAYER
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "5.0 System Architecture by Layer")
    add_p(doc, "The backend and frontend are decomposed into modular, isolated architectural layers:")

    add_figure(doc, "diagram_backend_layers.png", "Figure 2: Detailed FastAPI Backend Layered Service Architecture")

    add_p(doc, "1. Presentation Layer (React 19 + Leaflet 1.9.4):", bold_prefix="Layer 1: ")
    add_p(doc, "A responsive single-page web application written in TypeScript and styled with Tailwind CSS v4. It renders the 3-column analysis workspace, handles interactive AOI drawing on real satellite tiles, manages user session states, and renders multi-layer evidence canvases.")

    add_p(doc, "2. Application & API Gateway Layer (FastAPI):", bold_prefix="Layer 2: ")
    add_p(doc, "An asynchronous ASGI application running on Python 3.11. It provides 14 REST endpoints grouped into six functional routers (`auth`, `earth`, `analyses`, `history`, `reports`, `system`), enforces Pydantic v2 data validation, and manages background tasks via an asynchronous job queue.")

    add_p(doc, "3. Geospatial & Data Layer (STAC + PyProj / Shapely):", bold_prefix="Layer 3: ")
    add_p(doc, "Communicates with public STAC APIs (AWS Earth Search and Copernicus Data Space) to query Sentinel-1 and Sentinel-2 catalogues. Validates GeoJSON geometries, calculates geodesic ground area in EPSG:6933, and extracts cropped raster arrays matching AOI coordinates.")

    add_p(doc, "4. Specialist Model & Inference Layer:", bold_prefix="Layer 4: ")
    add_p(doc, "Contains the analytical specialists (`VQASpecialist`, `GroundingSpecialist`, `ChangeSpecialist`, `OpticalSARSpecialist`), deterministic intent routing, and multi-signal confidence estimation.")

    add_p(doc, "5. Evidence & Overlay Layer:", bold_prefix="Layer 5: ")
    add_p(doc, "Generates and serves high-resolution RGBA visual evidence overlays, change magnitude heatmaps, and bounding box coordinate arrays for interactive UI inspection.")

    add_p(doc, "6. Persistence & Reporting Layer:", bold_prefix="Layer 6: ")
    add_p(doc, "Maintains dual-mode database repositories (Google Cloud Firestore in production and SQLite `data/satya_dristi_store.db` in local development), stores generated evidence masks and rasters on disk, and compiles vector PDF reports using ReportLab Platypus.")

    add_p(doc, "7. Authentication Layer:", bold_prefix="Layer 7: ")
    add_p(doc, "Verifies Firebase JWT identity tokens, manages developer session bypasses in offline environments, and enforces strict UID multi-tenant record isolation.")

    # =========================================================================
    # 8. AUTHENTICATION & IDENTITY MANAGEMENT
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "6.0 Authentication & User Identity Subsystem")
    add_p(doc, "Satya Dristi implements enterprise-grade authentication utilizing Firebase Authentication and JSON Web Tokens (JWT) verified cryptographically on the FastAPI backend:")

    add_figure(doc, "diagram_auth_flow.png", "Figure 3: Firebase Authentication, Token Verification & Security Multi-Tenancy Flow")

    add_heading_2(doc, "6.1 Authentication Workflow & Token Lifecycle")
    add_p(doc, "1. Identity Handshake: The analyst initiates authentication in the React frontend via Google Sign-In or developer credential injection.")
    add_p(doc, "2. Token Issuance: Firebase Authentication issues a signed RS256 JWT ID token containing the analyst's unique UID, email, and expiration timestamp.")
    add_p(doc, "3. Authorization Header: The frontend client (`src/lib/api.ts`) automatically intercepts outgoing requests and attaches the token via standard `Authorization: Bearer <token>` headers.")
    add_p(doc, "4. Cryptographic Verification: In production, `backend/app/core/firebase.py` verifies the token's cryptographic signature against Google's public JSON Web Key Sets (JWKS) via `firebase_admin.auth.verify_id_token()`.")
    add_p(doc, "5. Offline Development Fallback: In local environments where Google Cloud credentials are not configured, `verify_token()` extracts a simulated development identity (`dev-user-001`), enabling 100% offline functionality for evaluators.")
    add_p(doc, "6. Multi-Tenant User Document Storage: Authenticated profiles are upserted into the `users` database collection, recording `last_login`, `role`, and `analyses_count`.")

    # =========================================================================
    # 9. FRONTEND TECHNICAL REPORT
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "7.0 Frontend Technical Implementation")
    add_p(doc, "The frontend of Satya Dristi is designed to provide a calm, disciplined, and uncluttered desktop workspace. It adheres strictly to the project's visual identity: Deep Slate (`#313851`), Amber Gold (`#AB7C2C`), Steel Blue (`#4F6F8A`), and Canvas Cream (`#F6F3ED`).")

    add_heading_2(doc, "7.1 Frontend Technology Stack")
    fe_tech_headers = ["Technology / Library", "Version", "Functional Role in Frontend", "Verification Status"]
    fe_tech_data = [
        ["React", "19.0.0", "Core reactive component runtime and virtual DOM", "IMPLEMENTED"],
        ["React DOM", "19.0.0", "DOM rendering engine for React 19", "IMPLEMENTED"],
        ["Vite", "8.0.5", "High-performance build tool and dev server", "IMPLEMENTED"],
        ["TypeScript", "5.7.0", "Static typing across all components, interfaces, and schemas", "IMPLEMENTED"],
        ["Tailwind CSS", "4.0.0", "Utility-first CSS styling via @tailwindcss/vite plugin", "IMPLEMENTED"],
        ["Leaflet", "1.9.4", "Interactive Earth observation map and GIS rendering", "IMPLEMENTED"],
        ["@types/leaflet", "1.9.22", "TypeScript definitions for Leaflet GIS objects", "IMPLEMENTED"],
        ["jsPDF", "4.2.1", "Client-side report utilities (supplementary)", "IMPLEMENTED"],
        ["oxfmt", "0.2.0", "High-speed code formatting tool", "IMPLEMENTED"],
    ]
    add_styled_table(doc, fe_tech_headers, fe_tech_data, col_widths=[1.6, 0.9, 2.7, 1.3])

    add_heading_2(doc, "7.2 Frontend Route & Page Inventory")
    fe_page_headers = ["Page Name", "Route Path", "Primary Purpose", "Auth Required", "Status"]
    fe_page_data = [
        ["Landing", "/", "Public platform overview, capabilities, and call-to-action", "No", "IMPLEMENTED"],
        ["Dashboard", "/dashboard", "Operational metrics, hardware status, recent analyses, quick actions", "Yes", "IMPLEMENTED"],
        ["Analyze", "/analyze", "Primary 3-column analysis workspace: map, query, pipeline, evidence", "Yes", "IMPLEMENTED"],
        ["History", "/history", "Searchable archive of historical analyses with query filters", "Yes", "IMPLEMENTED"],
        ["Reports", "/reports", "Official report repository with PDF and JSON download triggers", "Yes", "IMPLEMENTED"],
        ["Settings", "/settings", "Hardware telemetry monitor, provider status, system config", "Yes", "IMPLEMENTED"],
        ["Privacy Policy", "/legal/privacy", "Data handling, retention, and satellite imagery privacy terms", "No", "IMPLEMENTED"],
        ["Terms & Conditions", "/legal/terms", "Operational terms of service for satellite intelligence", "No", "IMPLEMENTED"],
    ]
    add_styled_table(doc, fe_page_headers, fe_page_data, col_widths=[1.3, 1.2, 2.6, 0.9, 1.0])

    # =========================================================================
    # 10. ANALYZE WORKSPACE GRID
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "8.0 Analyze Workspace 3-Column Desktop Grid")
    add_p(doc, "The Analyze page (`src/pages/Analyze.tsx`) was corrected to eliminate nested card clutter and establish the Global Earth Observation Map as the commanding visual center:")

    add_figure(doc, "diagram_frontend_layout.png", "Figure 4: Analyze Workspace 3-Column Desktop Layout Architecture")

    add_p(doc, "1. Left Column (Control Panel, ~300px):", bold_prefix="Left Column: ")
    add_p(doc, "Acts as the input control center. Uses flat grouping without recursive box nesting. Contains: (1) Input Source toggle (`Global Map` | `Manual Upload`); (2) Analysis Mode selector (`Single Image`, `Optical + SAR`, `Before + After`); (3) Compact Selected Scene summary displaying sensor tag, acquisition date, cloud cover, and truncated scene ID without duplicating explorer metadata; (4) What Do You Want to Know? question textarea with 3 concise example query chips; and (5) Primary Run Analysis button.")

    add_p(doc, "2. Center Column (Global Explorer & Evidence, ~750px):", bold_prefix="Center Column: ")
    add_p(doc, "Receives approximately 55–60% of total desktop width. Displays the Global Earth Observation Explorer with real satellite imagery at 460px height. Search controls are organized into two clean, uncramped rows: Row 1 holds the dominant location search bar, Year selector (2016–2026), and Sensor toggle; Row 2 holds Cloud Cover filter, quick geographic presets, and Search Scenes action. Below the map sits a spacious grid of available satellite scenes. In the result phase, this column seamlessly transitions to the Visual Evidence Canvas and Answer Panel.")

    add_p(doc, "3. Right Column (Analysis Pipeline & Audit, ~280px):", bold_prefix="Right Column: ")
    add_p(doc, "Serves as a supporting timeline with compact 18px numbered status circles and lightweight vertical connectors. During execution, it tracks real progress stages. Upon completion, it displays multi-signal confidence agreement, a collapsible execution trace, and official Report Export buttons (PDF / JSON).")

    # =========================================================================
    # 11. ANALYSIS MODES SPECIFICATION
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "9.0 Analysis Modes Specification")
    add_p(doc, "Satya Dristi supports three core analytical modalities, each tailored to specific operational requirements:")

    modes_headers = ["Analysis Mode", "Input Data Requirements", "Target Specialist Engine", "Evidence Artifact", "Operational Use Case"]
    modes_data = [
        ["Single-Image VQA", "Single optical or SAR scene + question", "VQASpecialist & GroundingSpecialist", "Bounding boxes & feature masks", "Land-cover inventory, water boundary extraction, urban footprint"],
        ["Before + After", "Pair of temporally separated scenes", "ChangeSpecialist (CVA Engine)", "Bi-temporal RGBA change overlay", "Urban sprawl tracking, flood extent mapping, disaster damage assessment"],
        ["Optical + SAR", "Co-registered optical + radar pair", "OpticalSARSpecialist (Fusion)", "Fused dielectric consensus mask", "All-weather surface intelligence, cloud penetration, flood delineation"],
    ]
    add_styled_table(doc, modes_headers, modes_data, col_widths=[1.4, 1.4, 1.4, 1.3, 1.5])

    add_heading_2(doc, "9.1 Modality 1: Single-Image VQA & Feature Grounding")
    add_p(doc, "Workflow: The analyst selects an optical scene and submits a question (e.g., 'What is the dominant land cover?' or 'Locate all water bodies'). The backend crops the AOI, runs spectral decomposition, extracts bounding boxes for target classes, synthesizes a quantitative natural-language answer, and renders bounding boxes directly on the satellite raster.")

    add_heading_2(doc, "9.2 Modality 2: Before + After Change Detection")
    add_p(doc, "Workflow: The analyst selects a baseline scene (e.g., 2022) and a target scene (e.g., 2024). The backend resamples both rasters to matching grid dimensions, computes Change Vector Analysis (CVA) magnitude and structural difference, applies an 82nd-percentile adaptive cutoff, and renders an RGBA change overlay (built-up gain in amber gold, water extent variation in steel blue).")

    add_heading_2(doc, "9.3 Modality 3: Optical + SAR Multimodal Fusion")
    add_p(doc, "Workflow: The analyst selects a Sentinel-2 optical scene and a Sentinel-1 SAR scene covering the same AOI. The backend converts raw radar amplitude to calibrated decibels (dB), evaluates double-bounce corner reflection (>165 DN) and specular reflection (<60 DN), and correlates with optical spectral indices to generate an all-weather consensus mask.")

    # =========================================================================
    # 12. GEOSPATIAL & SATELLITE DATA PIPELINE
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "10.0 Geospatial & Satellite Data Ingestion Pipeline")
    add_p(doc, "Satya Dristi interacts directly with international Earth observation data infrastructures, ensuring that analysis is grounded in real, verifiable satellite observations rather than decorative graphics.")

    add_figure(doc, "diagram_satellite_pipeline.png", "Figure 5: STAC Satellite Discovery & Asset Ingestion Flow")

    add_heading_2(doc, "10.1 Ingested Satellite Constellations")
    add_p(doc, "The platform ingests two primary satellite constellations:")
    add_bullet(doc, "Sentinel-2 MSI (Multispectral Instrument): Level-2A Bottom-of-Atmosphere (BOA) surface reflectance. Ingests 10-meter spatial resolution visible (B02 Blue, B03 Green, B04 Red) and Near-Infrared (B08 NIR) spectral bands.")
    add_bullet(doc, "Sentinel-1 C-SAR (Synthetic Aperture Radar): Level-1 Ground Range Detected (GRD) in Interferometric Wide (IW) swath mode. Provides dual-polarization (VV + VH) microwave backscatter capable of all-weather, day-and-night surface penetration.")

    add_heading_2(doc, "10.2 STAC Provider Gateways & Query Mechanics")
    add_p(doc, "STAC catalogue queries are executed via `backend/app/services/stac_service.py`:")
    add_bullet(doc, "AWS Earth Search STAC (https://earth-search.aws.element84.com/v1): Primary gateway querying global Sentinel-2 L2A COGs and Sentinel-1 GRD archives hosted on AWS Open Data.")
    add_bullet(doc, "Copernicus Data Space Ecosystem (https://stac.dataspace.copernicus.eu/v1): Secondary official European Space Agency gateway for comprehensive European and Asian coverage.")
    add_bullet(doc, "Temporal Multi-Year Filtering: Formats ISO-8601 interval queries covering the complete operating history from 2016 through 2026.")
    add_bullet(doc, "Cloud Cover Masking: Optical queries enforce strict cloud cover ceilings (`eo:cloud_cover <= 30.0%`), automatically bypassed for SAR queries.")

    # =========================================================================
    # 13. AOI SYSTEM & GEODESIC MATH
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "11.0 Area of Interest (AOI) Engine & Geodesic Math")
    add_p(doc, "AOI definition is managed via `backend/app/services/geospatial_processor.py`:")

    add_figure(doc, "diagram_aoi_processing.png", "Figure 6: AOI Geometry Validation and Geodesic Equal-Area Projection")

    add_p(doc, "Geodesic Surface Math:", bold_prefix="Cylindrical Equal-Area Projection — ")
    add_p(doc, "Standard Web Mercator (EPSG:3857) distorts surface areas exponentially toward the poles. Satya Dristi transforms user WGS84 bounding polygons to World Equal Area cylindrical projection (`EPSG:6933`) using PyProj to compute accurate physical ground surface area in square kilometers:")
    add_code_block(doc, 
        "wgs84 = pyproj.CRS('EPSG:4326')\n"
        "equal_area = pyproj.CRS('EPSG:6933')\n"
        "project = pyproj.Transformer.from_crs(wgs84, equal_area, always_xy=True).transform\n"
        "proj_geom = shapely.ops.transform(project, geom_shape)\n"
        "area_sq_km = round(proj_geom.area / 1_000_000.0, 4)"
    )

    # =========================================================================
    # 14. IMAGE PROCESSING & BAND MANIPULATION
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "12.0 Image Processing & Band Manipulation")
    add_p(doc, "The image processing pipeline (`backend/app/services/image_retrieval.py` and `geospatial_processor.py`) implements clean raster ingestion and normalization:")
    add_bullet(doc, "Multi-Format Raster Decoding: Decodes GeoTIFF, TIFF, PNG, and JPEG formats using OpenCV and Pillow.")
    add_bullet(doc, "RGB Channel Normalization: Scales raw radiometric digital numbers (DN) to 8-bit unsigned integers [0..255] for visual rendering while preserving raw float values for spectral indexing.")
    add_bullet(doc, "Normalized Difference Spectral Indexing: Implements NDVI = (NIR - Red) / (NIR + Red) for vegetation vigour and NDWI = (Green - NIR) / (Green + NIR) for open water delineation.")
    add_bullet(doc, "Radar Backscatter Conversion: Converts linear SAR amplitude to decibel backscatter: dB = 10 * log10(DN^2 + 1.0).")
    add_bullet(doc, "NoData & Spatial Masking: Automatically masks out zero-fill border pixels generated during raster reprojection and AOI cropping.")

    # =========================================================================
    # 15. AI / ML SPECIALIST MODELS
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "13.0 AI / ML Specialist Models & Analytical Engines")
    add_p(doc, "Satya Dristi implements a modular registry of specialist models managed by a hardware-aware resource manager. The platform avoids relying on single opaque monolithic models by routing tasks to specialized analytical engines.")

    add_heading_2(doc, "13.1 Specialist Model Inventory")
    ml_headers = ["Specialist Identifier", "Source File", "Analytical Modality", "Inference Methodology", "Hardware Device", "Current Status"]
    ml_data = [
        ["VQASpecialist", "vqa_specialist.py", "Optical Multispectral", "Spectral decomposition + edge density", "CPU / CUDA", "IMPLEMENTED (Spectral CV)"],
        ["GroundingSpecialist", "grounding_specialist.py", "Optical Multispectral", "Spectral indexing + OpenCV contours", "CPU / CUDA", "IMPLEMENTED (Spectral CV)"],
        ["ChangeSpecialist", "change_specialist.py", "Bi-Temporal Optical", "Change Vector Analysis (CVA) + absdiff", "CPU / CUDA", "IMPLEMENTED (CVA CV)"],
        ["OpticalSARSpecialist", "optical_sar_specialist.py", "Optical + C-band SAR", "Radiometric cross-modal thresholding", "CPU / CUDA", "IMPLEMENTED (Cross-Modal)"],
        ["TaskRouter", "task_router.py", "Natural Language Text", "Deterministic semantic keyword classifier", "CPU", "IMPLEMENTED (Rule Engine)"],
        ["ConfidenceEngine", "confidence_engine.py", "Multi-Signal Telemetry", "Composite weighted heuristic formula", "CPU", "IMPLEMENTED (Heuristic)"],
        ["ModelResourceManager", "resource_manager.py", "System Telemetry", "PyTorch CUDA VRAM memory manager", "CPU / GPU", "IMPLEMENTED (Resource Mgr)"],
    ]
    add_styled_table(doc, ml_headers, ml_data, col_widths=[1.5, 1.2, 1.2, 1.5, 0.8, 1.3])

    add_heading_2(doc, "13.2 Visual Question Answering (VQA) Engine")
    add_p(doc, "The `VQASpecialist` performs quantitative spectral decomposition on real satellite imagery to answer land-cover, water boundary, and infrastructure questions:")
    add_bullet(doc, "Vegetation Cover Index: Evaluates green-red contrast: VI = (Green - Red) / (Green + Red + 1e-6) > 0.04.")
    add_bullet(doc, "Water Surface Index: Identifies low-luminance pixels (<120 DN) where green reflectance exceeds red.")
    add_bullet(doc, "Urban Texture Density: Runs an OpenCV Canny edge detector (thresholds 60, 150) to measure structural high-frequency spatial density.")
    add_bullet(doc, "Directional Spatial Quadrants: Scans NW, NE, SW, and SE quadrants to localize prominent features geographically.")
    add_bullet(doc, "Template Synthesis: Dynamically formats answers grounded in physical percentage distributions calibrated against Sentinel-2 surface reflectance.")

    add_heading_2(doc, "13.3 Grounding & Feature Localization Engine")
    add_p(doc, "The `GroundingSpecialist` translates semantic concepts into geographic and image pixel bounding boxes:")
    add_bullet(doc, "Class Isolation: Parses user queries for target classes (`water_body`, `built_up`, `vegetation`).")
    add_bullet(doc, "Morphological Filtering: Cleans spectral activation masks using a 5x5 rectangular structuring element.")
    add_bullet(doc, "Contour Extraction: Extracts external contours via `cv2.findContours`, sorting components by physical surface area.")
    add_bullet(doc, "Coordinate Mapping: Emits normalized canvas percentages (0..100%) for UI overlay, pixel bounding boxes [x, y, w, h], and WGS84 geographic bounding coordinates.")

    # =========================================================================
    # 16. CHANGE DETECTION & OPTICAL-SAR FUSION
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "14.0 Bi-Temporal Change Detection & Optical-SAR Fusion")

    add_heading_2(doc, "14.1 Bi-Temporal Change Detection Engine (CVA)")
    add_p(doc, "The `ChangeSpecialist` executes authentic bi-temporal change detection between observation dates:")

    add_figure(doc, "diagram_change_detection.png", "Figure 7: Bi-Temporal Change Vector Analysis (CVA) & RGBA Evidence Mapping")

    add_p(doc, "Mathematical Formulation:", bold_prefix="Change Vector Analysis (CVA) — ")
    add_p(doc, "Given Baseline image B and Target image A resampled to identical dimensions, the pixel-wise change magnitude vector Delta_M is computed across all spectral channels:")
    add_code_block(doc,
        "diff = arr_after - arr_before\n"
        "magnitude = np.sqrt(np.sum(np.square(diff), axis=2))\n"
        "struct_diff = cv2.absdiff(gray_after, gray_before)\n"
        "thresh = np.percentile(magnitude, 82)\n"
        "change_mask = (magnitude > thresh) & (struct_diff > 15)"
    )
    add_p(doc, "The system categorizes change pixels into: (1) Built-up gain (brightness gain > +20 DN); (2) Water extent shift (brightness drop < -25 DN); and (3) General surface variation. It saves an RGBA colored overlay (`change_map_*.png`) highlighting built-up gain in gold (`#AB7C2C`) and water variation in blue (`#4F6F8A`).")

    add_heading_2(doc, "14.2 Optical + SAR Multimodal Fusion Engine")
    add_p(doc, "The `OpticalSARSpecialist` performs cross-modal radiometric fusion between optical reflectance and radar backscatter:")

    add_figure(doc, "diagram_optical_sar_fusion.png", "Figure 8: Multimodal Optical + SAR Cross-Modal Fusion Flow")

    add_p(doc, "Cross-Modal Consensus Logic:", bold_prefix="Dielectric & Geometric Agreement — ")
    add_bullet(doc, "SAR Decibel Calibration: Converts raw SAR amplitude into calibrated radar backscatter dB: dB = 10 * log10(DN^2 + 1.0).")
    add_bullet(doc, "Double-Bounce Urban Detection: Identifies strong radar corner reflectors (>165 DN) characteristic of perpendicular building walls.")
    add_bullet(doc, "Specular Reflection Water Detection: Identifies calm water surfaces where radar pulses reflect away, producing minimal backscatter (<60 DN).")
    add_bullet(doc, "Boolean Consensus: Confirmed Urban = Optical Urban AND SAR Double Bounce; Confirmed Water = Optical Water AND SAR Specular Reflection.")
    add_bullet(doc, "Fused Evidence Overlay: Writes a color-coded fused highlight overlay (`fused_*.png`) validating surface roughness and moisture separation.")

    # =========================================================================
    # 17. EXECUTION TRACE & REPORT GENERATION
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "15.0 Execution Trace, Evidence & Report Generation")
    add_p(doc, "A foundational requirement of mission-critical Earth observation intelligence is auditability. Satya Dristi ensures that every output is accompanied by an observable execution trace, multi-factor confidence ratings, and downloadable publication-grade report artifacts.")

    add_figure(doc, "diagram_analysis_pipeline.png", "Figure 9: Asynchronous Analysis Execution Pipeline & Observable Milestones")

    add_heading_2(doc, "15.1 Observable Execution Trace Schema")
    add_p(doc, "Execution traces track real, chronological stage milestones. Internal neural network activations are strictly protected, ensuring intellectual property security while maintaining operational auditability:")
    add_code_block(doc,
        "[\n"
        "  {\"name\": \"Input validation\", \"detail\": \"AOI bounds verified (42.18 km²)\", \"duration\": \"0.05s\"},\n"
        "  {\"name\": \"Query classification\", \"detail\": \"Intent routed to Single-Image VQA\", \"duration\": \"0.01s\"},\n"
        "  {\"name\": \"Scene retrieval\", \"detail\": \"Cached scene S2A_43QHV_20241223_0_L2A loaded\", \"duration\": \"0.12s\"},\n"
        "  {\"name\": \"Model inference\", \"detail\": \"Spectral decomposition on CPU\", \"duration\": \"0.14s\"},\n"
        "  {\"name\": \"Evidence generation\", \"detail\": \"Rendered grounding delineation mask\", \"duration\": \"0.08s\"},\n"
        "  {\"name\": \"Report compilation\", \"detail\": \"PDF and JSON artifacts generated\", \"duration\": \"0.22s\"}\n"
        "]"
    )

    add_heading_2(doc, "15.2 Multi-Factor Confidence Engine")
    add_p(doc, "The `ConfidenceEngine` evaluates multi-signal composite telemetry rather than uncalibrated softmax logits:")
    add_bullet(doc, "Cloud Cover Factor: Cloud cover >25% penalizes score by -0.15; clear skies (<10%) award +0.10.")
    add_bullet(doc, "Cross-Modal Correlation: Agreement between optical and SAR signals awards +0.15.")
    add_bullet(doc, "Bi-Temporal Overlap: Spatial overlap >80% awards +0.10; lower overlap penalizes by -0.20.")
    add_bullet(doc, "Calibrated Thresholds: Score >= 0.80 -> 'High'; 0.60..0.79 -> 'Moderate'; < 0.60 -> 'Low'.")
    add_bullet(doc, "Explicit Integrity Note: Classified as HEURISTIC / NOT CALIBRATED. It reflects observational signal quality, not mathematical probability of ground truth.")

    add_heading_2(doc, "15.3 Publication-Grade Report Generation Subsystem")
    add_p(doc, "The `ReportGeneratorService` compiles publication-grade vector PDF documents and structured JSON exports on disk:")

    add_figure(doc, "diagram_report_generation.png", "Figure 10: ReportLab Platypus Vector PDF Compilation & Export Flow")

    add_p(doc, "Report Structure & Platypus Flowables:")
    add_bullet(doc, "Vector Typography: Helvetica-Bold titles, Courier metadata tables, Deep Slate (`#313851`) headers.")
    add_bullet(doc, "Embedded Visual Evidence: Incorporates real satellite quicklook rasters and generated RGBA evidence overlays directly into the PDF flow.")
    add_bullet(doc, "Quantitative Tables: Full spectral breakdowns, CVA change percentages, and execution traces.")
    add_bullet(doc, "Download Streaming: Served via `/api/v1/reports/{id}/download` with `Content-Type: application/pdf` and `Content-Disposition: attachment`.")

    # =========================================================================
    # 18. DATABASE & PERSISTENCE TIER
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "16.0 Database & Persistence Architecture")
    add_p(doc, "Satya Dristi implements a dual-mode persistence architecture (`backend/app/core/db.py`) designed for zero-configuration local evaluation and scalable cloud deployment:")

    db_headers = ["Collection / Table", "Target Database", "Primary Key", "Key Fields & Schema", "Security & Multi-Tenancy"]
    db_data = [
        ["users", "Firestore / SQLite", "uid", "email, name, role, created_at, last_login, analyses_count", "Scoped strictly to authenticated user UID"],
        ["analyses", "Firestore / SQLite", "id (UUIDv4)", "user_id, task, query, scene_ids, aoi, answer, evidence, trace", "Filtered by user_id on query retrieval"],
        ["reports", "Firestore / SQLite", "id (UUIDv4)", "analysis_id, user_id, title, pdf_path, json_path, created_at", "Accessible only by owning user_id"],
        ["jobs", "In-Memory / SQLite", "job_id", "status, stage, progress_pct, result, error, created_at", "Async polling queue tracking running tasks"],
    ]
    add_styled_table(doc, db_headers, db_data, col_widths=[1.3, 1.3, 1.0, 1.8, 1.3])

    add_p(doc, "SQLite Local Document Store Implementation:", bold_prefix="Local Development Bridge — ")
    add_p(doc, "When Google Cloud Firestore credentials (`GOOGLE_APPLICATION_CREDENTIALS`) are absent, the repository initializes `data/satya_dristi_store.db`. Documents are serialized as JSON payloads inside typed tables (`documents` and `jobs`), providing full transactional consistency, crash recovery, and thread safety across async tasks without requiring external database processes.")

    # =========================================================================
    # 19. REST API SPECIFICATION
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "17.0 Complete REST API Specification")
    add_p(doc, "The FastAPI backend exposes 14 production endpoints conforming strictly to OpenAPI 3.1 specifications:")

    api_headers = ["Method", "Endpoint Path", "Auth Required", "Description & Primary Service", "Database Impact"]
    api_data = [
        ["GET", "/api/v1/auth/me", "Bearer Token", "Returns authenticated analyst profile; saves/updates user in DB", "Writes users doc"],
        ["POST", "/api/v1/earth/scenes/search", "Bearer Token", "Queries AWS & Copernicus STAC catalogues for Sentinel-1/2", "Reads STAC API"],
        ["GET", "/api/v1/earth/scenes/{id}", "Bearer Token", "Fetches complete metadata and asset links for scene ID", "Reads STAC cache"],
        ["POST", "/api/v1/earth/aoi/preview", "Bearer Token", "Validates GeoJSON/bbox; calculates EPSG:6933 geodesic area (km²)", "None (stateless)"],
        ["POST", "/api/v1/earth/compatibility", "Bearer Token", "Verifies spatial overlap and CRS alignment between scene pairs", "None (stateless)"],
        ["POST", "/api/v1/earth/imagery", "Bearer Token", "Retrieves and caches cropped raster imagery for scene and AOI", "Writes data/cache/"],
        ["POST", "/api/v1/analyses", "Bearer Token", "Submits asynchronous analysis task referencing STAC scene & AOI", "Writes analyses doc"],
        ["POST", "/api/v1/analyses/upload", "Bearer Token", "Submits async task with user-uploaded GeoTIFF/PNG/JPEG files", "Writes data/uploads/"],
        ["GET", "/api/v1/analyses/{id}/status", "Bearer Token", "Polls real-time execution stage, progress %, and error states", "Reads memory/DB"],
        ["GET", "/api/v1/analyses/{id}", "Bearer Token", "Retrieves complete analysis record, answer, evidence, and trace", "Reads analyses doc"],
        ["GET", "/api/v1/analyses/{id}/evidence", "Bearer Token", "Serves raw visual evidence overlay image", "Reads data/evidence/"],
        ["GET", "/api/v1/history", "Bearer Token", "Lists user analysis archive with task filter and keyword search", "Reads analyses doc"],
        ["GET", "/api/v1/reports", "Bearer Token", "Lists user report metadata; auto-compiles from analyses if empty", "Reads reports doc"],
        ["GET", "/api/v1/reports/{id}", "Bearer Token", "Retrieves metadata record for specific report artifact", "Reads reports doc"],
        ["GET", "/api/v1/reports/{id}/download", "Bearer Token", "Streams publication-grade vector PDF report attachment", "Reads data/reports/"],
        ["GET", "/api/v1/reports/{id}/json", "Bearer Token", "Streams structured auditable JSON export payload", "Reads data/reports/"],
        ["GET", "/api/v1/system/health", "None", "Returns real live PyTorch CUDA, GPU, VRAM, and CPU telemetry", "None (psutil/torch)"],
    ]
    add_styled_table(doc, api_headers, api_data, col_widths=[0.8, 1.8, 1.0, 2.0, 1.1])

    # =========================================================================
    # 20. ERROR HANDLING ARCHITECTURE
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "18.0 Error Handling Architecture")
    add_p(doc, "Satya Dristi implements structured domain exceptions mapped to standard RFC-7807 problem details across all endpoints:")

    err_headers = ["Fault Scenario", "HTTP Code", "Internal Error Domain", "Root Cause Trigger", "System Mitigation / UX Action"]
    err_data = [
        ["Invalid Upload Raster", "400 Bad Request", "ValidationError", "Corrupt GeoTIFF or unsupported image codec", "Rejects payload; displays toast notification"],
        ["Invalid AOI Coordinates", "422 Unprocessable", "GeospatialError", "Polygon self-intersection or out of WGS84 range", "Flags invalid bounds; prevents submission"],
        ["No Satellite Scenes", "404 Not Found", "STACProviderError", "Overly restrictive cloud ceiling or date range", "Returns empty list; suggests wider date window"],
        ["Incompatible Scenes", "400 Bad Request", "CompatibilityError", "Pre/Post scenes have zero spatial overlap", "Halts analysis; notifies analyst to align AOI"],
        ["Model Inference Error", "500 Internal Error", "ModelExecutionError", "Out of memory or numerical NaN overflow", "Captures trace in DB; emits failed status to UI"],
        ["Remote STAC Timeout", "502 Bad Gateway", "GatewayTimeoutError", "AWS Earth Search or Copernicus outage", "Falls back to local scene cache with warning"],
        ["Expired Auth Token", "401 Unauthorized", "SecurityError", "Expired or invalid Firebase RS256 JWT", "Redirects analyst to authentication dialog"],
        ["PDF Generation Error", "500 Internal Error", "ReportCompileError", "Missing evidence overlay image on disk", "Compiles text-only PDF summary fallback"],
    ]
    add_styled_table(doc, err_headers, err_data, col_widths=[1.4, 1.1, 1.4, 1.4, 1.4])

    # =========================================================================
    # 21. PERFORMANCE & EMPIRICAL BENCHMARKS
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "19.0 Performance Benchmarks & Empirical Latency")
    add_p(doc, "Performance metrics were empirically captured on the reference development workstation (AMD Ryzen / Intel Core i7, 32GB RAM, Windows 11, Python 3.11):")

    perf_headers = ["System Operation / Subsystem", "Measured Latency", "Hardware Resource", "Verification Status", "Engineering Notes"]
    perf_data = [
        ["Frontend Initial Load (Vite HMR)", "< 450 ms", "Browser Cache / DOM", "MEASURED", "React 19 virtual DOM mount"],
        ["STAC Catalogue Search (AWS)", "1,200 – 2,400 ms", "Network I/O / Remote API", "MEASURED", "Queries 10–20 Sentinel-2 scenes"],
        ["AOI Reprojection (PyProj EPSG:6933)", "40 – 60 ms", "Host CPU (1 Core)", "MEASURED", "Geodesic equal-area calculation"],
        ["VQA Spectral Decomposition", "120 – 180 ms", "Host CPU (NumPy/OpenCV)", "MEASURED", "Full 1024x1024 optical raster scan"],
        ["Grounding Contour Extraction", "80 – 120 ms", "Host CPU (OpenCV)", "MEASURED", "5x5 morphological close + contour"],
        ["CVA Bi-Temporal Change Detection", "220 – 320 ms", "Host CPU (NumPy/OpenCV)", "MEASURED", "Resampling, magnitude, 82nd pct"],
        ["Optical + SAR Radiometric Fusion", "280 – 380 ms", "Host CPU (NumPy)", "MEASURED", "SAR dB transform & consensus"],
        ["ReportLab Platypus PDF Compilation", "180 – 260 ms", "Host Disk I/O & CPU", "MEASURED", "Vector PDF with 2 embedded rasters"],
        ["PyTorch CUDA Inference Mode", "NOT BENCHMARKED", "NVIDIA GPU / CUDA", "NOT BENCHMARKED", "Current baseline uses optimized CPU CV"],
        ["Distributed Queue Throughput", "NOT BENCHMARKED", "Multi-Node Cluster", "NOT BENCHMARKED", "Requires multi-worker Celery deployment"],
    ]
    add_styled_table(doc, perf_headers, perf_data, col_widths=[1.8, 1.2, 1.2, 1.0, 1.5])

    # =========================================================================
    # 22. TESTING, VERIFICATION & SECURITY
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "20.0 Testing Suite & Verification Evidence")
    add_p(doc, "System reliability is verified using Pytest 9.1.1 and `pytest-asyncio` 1.4.0. The test suite executes 12 automated test cases covering end-to-end asynchronous workflows, live STAC catalogue discovery, geospatial geodesic calculations, report generation, and specialist model execution:")

    test_headers = ["Test Module", "Test Case Function", "Subsystem Verified", "Execution Result"]
    test_data = [
        ["test_e2e_workflow.py", "test_full_analysis_workflow", "End-to-end async job queue, polling, DB persistence, trace", "PASSED"],
        ["test_earth_stac.py", "test_stac_sentinel2_search", "Live Sentinel-2 STAC catalogue search, cloud filtering, asset links", "PASSED"],
        ["test_earth_stac.py", "test_stac_sentinel1_sar_search", "Live Sentinel-1 SAR STAC search, polarization detection, cloud bypass", "PASSED"],
        ["test_geospatial.py", "test_aoi_validation_bbox", "Bounding box validation, PyProj EPSG:6933 equal-area calculation", "PASSED"],
        ["test_geospatial.py", "test_aoi_validation_polygon", "GeoJSON polygon validation, centroid computation, WGS84 range check", "PASSED"],
        ["test_geospatial.py", "test_spectral_indices", "NDVI vegetation and NDWI water normalized difference calculation", "PASSED"],
        ["test_geospatial.py", "test_sar_calibration", "Logarithmic radar backscatter transform (10*log10(DN^2+1))", "PASSED"],
        ["test_reports.py", "test_report_pdf_and_json", "ReportLab Platypus PDF creation on disk, valid headers, JSON export", "PASSED"],
        ["test_specialist_models.py", "test_grounding_specialist", "Contour localization, bounding boxes, geo-coordinate mapping", "PASSED"],
        ["test_specialist_models.py", "test_change_specialist", "Bi-temporal CVA change magnitude, RGBA change map generation", "PASSED"],
        ["test_specialist_models.py", "test_optical_sar_specialist", "Optical-SAR cross-modal correlation, double bounce & specular agreement", "PASSED"],
        ["test_specialist_models.py", "test_vqa_specialist", "Spectral decomposition, land-cover percentages, natural language answer", "PASSED"],
    ]
    add_styled_table(doc, test_headers, test_data, col_widths=[1.5, 2.0, 2.2, 0.9])

    add_callout(doc,
        "All 12 automated test cases passed in 31.16 seconds on the host Python 3.11 environment. "
        "Test execution verifies genuine HTTP interaction with remote STAC servers, valid PDF binary generation on disk, "
        "and accurate geospatial reprojection math.",
        prefix="TEST SUITE RESULT (100% PASS): "
    )

    add_heading_2(doc, "20.1 Security & Threat Assessment")
    sec_headers = ["ID", "Severity", "Finding Description", "Code Evidence", "Remediation Status"]
    sec_data = [
        ["SEC-01", "Low", "Development token bypass in development mode", "backend/app/core/firebase.py:43-67", "Documented Design Decision. Disabled when ENVIRONMENT=production."],
        ["SEC-02", "Low", "Permissive CORS origin allowance (*)", "backend/app/core/config.py:16", "Restrict CORS_ORIGINS to trusted frontend domains prior to public deployment."],
        ["SEC-03", "Informational", "Path traversal protection on upload filenames", "backend/app/services/image_retrieval.py:146", "Secured via pathlib.Path(filename).name sanitization."],
        ["SEC-04", "Informational", "Credential isolation via environment variables", "backend/app/core/config.py", "Secured. .env excluded from version control via .gitignore."],
    ]
    add_styled_table(doc, sec_headers, sec_data, col_widths=[0.8, 1.0, 2.0, 1.6, 1.6])

    # =========================================================================
    # 23. TRACEABILITY & SIH ALIGNMENT
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "21.0 Requirements Traceability & SIH26167 Alignment")
    add_p(doc, "The following matrix establishes strict traceability between project specifications, hackathon requirements, and verified source code:")

    trace_headers = ["Requirement Description", "Frontend Implementation", "Backend Implementation", "Model / Specialist", "Status"]
    trace_data = [
        ["Natural Language Question Input", "Analyze.tsx (textarea & examples)", "api/v1/analyses.py", "task_router.py", "IMPLEMENTED"],
        ["Global Satellite Catalogue Discovery", "GlobalMap.tsx (Leaflet explorer)", "api/v1/earth.py", "stac_service.py", "IMPLEMENTED"],
        ["Multi-Year Search (2016–2026)", "GlobalMap.tsx (year dropdown)", "api/v1/earth.py", "stac_service.py", "IMPLEMENTED"],
        ["Interactive AOI Bounding", "GlobalMap.tsx (drag-to-draw toolbar)", "api/v1/earth.py", "geospatial_processor.py", "IMPLEMENTED"],
        ["Geodesic Surface Area (km²)", "GlobalMap.tsx (telemetry pill)", "api/v1/earth.py", "PyProj (EPSG:6933)", "IMPLEMENTED"],
        ["Single-Image VQA", "Analyze.tsx (Single mode)", "api/v1/analyses.py", "vqa_specialist.py", "IMPLEMENTED (Spectral CV)"],
        ["Spatial Feature Grounding", "SatImage.tsx (bounding boxes)", "api/v1/analyses.py", "grounding_specialist.py", "IMPLEMENTED (Spectral CV)"],
        ["Bi-Temporal Change Detection", "Analyze.tsx (Before+After mode)", "api/v1/analyses.py", "change_specialist.py (CVA)", "IMPLEMENTED"],
        ["Optical + SAR Multimodal Fusion", "Analyze.tsx (Optical+SAR mode)", "api/v1/analyses.py", "optical_sar_specialist.py", "IMPLEMENTED"],
        ["Agentic Intent Routing", "Analyze.tsx (pipeline timeline)", "services/task_router.py", "Deterministic Rule Engine", "IMPLEMENTED"],
        ["Visual Evidence Canvas & Layers", "SatImage.tsx (opacity & swipe)", "api/v1/analyses.py", "data/evidence/*.png", "IMPLEMENTED"],
        ["Multi-Factor Confidence", "Analyze.tsx (agreements breakdown)", "services/confidence_engine.py", "Heuristic Scoring Engine", "IMPLEMENTED (Heuristic)"],
        ["Observable Execution Trace", "Analyze.tsx (collapsible trace)", "services/async_queue.py", "Step Timers", "IMPLEMENTED"],
        ["Downloadable PDF Reports", "Reports.tsx, Analyze.tsx", "api/v1/reports.py", "report_generator.py (Platypus)", "IMPLEMENTED"],
        ["Persistent Analysis History", "History.tsx (archive & search)", "api/v1/history.py", "db.py (Firestore / SQLite)", "IMPLEMENTED"],
        ["Indian Satellites (Bhoonidhi)", "None (open ESA fallback)", "None", "None", "NOT IMPLEMENTED"],
    ]
    add_styled_table(doc, trace_headers, trace_data, col_widths=[1.7, 1.4, 1.4, 1.3, 1.0])

    # =========================================================================
    # 24. GAP ANALYSIS & TECHNICAL DEBT
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "22.0 Gap Analysis & Technical Debt Assessment")

    add_heading_2(doc, "22.1 Frontend / Backend Gap Analysis")
    gap_headers = ["Identified System Gap", "Severity", "Impact Assessment", "Current Code Reality", "Engineering Recommendation"]
    gap_data = [
        ["Direct AWS S3 COG Streaming", "Medium", "Limits full 12-band multi-gigabyte analysis", "Uses rendered previews and cropped RGB arrays", "Configure AWS requester-pays bucket credentials"],
        ["Google Sign-In Popup Script", "Low", "Requires manual dev-profile in browser", "Uses offline developer JWT token mock", "Inject client-side Firebase Auth Web SDK script"],
        ["ISRO Bhoonidhi STAC Ingestion", "High", "Limits Indian satellite data to ESA archives", "Not implemented in stac_service.py", "Add Bhoonidhi API connector when access is granted"],
        ["Distributed Celery Worker Queue", "Low", "Constrains async concurrency to single host", "In-process Python asyncio queue", "Deploy Redis broker and Celery background workers"],
    ]
    add_styled_table(doc, gap_headers, gap_data, col_widths=[1.5, 0.9, 1.5, 1.4, 1.4])

    add_heading_2(doc, "22.2 Technical Debt Assessment")
    debt_headers = ["Technical Debt Item", "Impacted File", "Debt Category", "Observed Code State", "Refactoring Target"]
    debt_data = [
        ["Algorithmic CV Fallback", "vqa_specialist.py", "AI/ML Modeling", "Spectral indexing used instead of deep VLM", "Plug fine-tuned Remote-CLIP / GeoVLM weights"],
        ["Dev-Token Bypass", "core/firebase.py", "Security / Auth", "Hardcoded dev-user token parsing for local dev", "Enforce strict JWKS validation in prod builds"],
        ["In-Process Job State", "services/async_queue.py", "Concurrency", "Jobs held in thread-safe memory dict", "Migrate job state to Redis pub/sub queue"],
        ["Hardcoded India Presets", "components/GlobalMap.tsx", "Frontend GIS", "Fixed lat/lng coordinates for Hyderabad, Delhi, etc.", "Dynamically fetch presets from administrative DB"],
    ]
    add_styled_table(doc, debt_headers, debt_data, col_widths=[1.4, 1.4, 1.1, 1.5, 1.3])

    # =========================================================================
    # 25. SYSTEM LIMITATIONS & FUTURE ROADMAP
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "23.0 Known System Limitations & Future Engineering Roadmap")

    add_heading_2(doc, "23.1 Categorized System Limitations")
    add_bullet(doc, "Spatial Resolution Limits: 10-meter Sentinel-2 pixels cannot resolve individual small vehicles, residential doorways, or narrow pedestrian footpaths.")
    add_bullet(doc, "Algorithmic Model Baseline: The analytical specialists execute robust classical remote sensing computer vision rather than multi-billion parameter deep neural networks.")
    add_bullet(doc, "Heuristic Confidence Calibration: Confidence scores reflect observational signal quality (cloud cover, cross-modal agreement), not statistical ground truth probability.")
    add_bullet(doc, "Cloud Shadow False Positives: Steep cloud shadows occasionally register as low-luminance water pixels in purely optical spectral indexing.")
    add_bullet(doc, "Single-Node Process Bounds: Background asynchronous execution is constrained by host server memory and CPU threads.")

    add_heading_2(doc, "23.2 Future Engineering Roadmap")
    add_bullet(doc, "Integration of Pretrained Remote-Sensing VLMs: Mount fine-tuned Vision-Language Transformers (e.g., RemoteCLIP, EarthDial) directly into `ModelResourceManager`.")
    add_bullet(doc, "Direct Requester-Pays AWS S3 COG Ingestion: Enable streaming reads of 12-band Sentinel-2 assets via GDAL/Rasterio virtual file systems (`/vsicurl/`).")
    add_bullet(doc, "ISRO Bhoonidhi STAC Connectors: Integrate Indian Space Research Organisation data archives for Cartosat and RISAT constellations.")
    add_bullet(doc, "Empirical Probability Calibration: Calibrate confidence estimators against validated ground truth benchmark datasets (e.g., EuroSAT, SpaceNet).")
    add_bullet(doc, "Distributed Microservice Architecture: Decouple inference workers into GPU-accelerated Docker containers managed via Kubernetes.")

    # =========================================================================
    # 26. DEMO PROCEDURES & SETUP
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "24.0 Step-by-Step Demonstration Walkthroughs")
    add_p(doc, "The following step-by-step procedures allow any evaluator, faculty reviewer, or teammate to demonstrate the verified capabilities of Satya Dristi:")

    add_heading_2(doc, "24.1 Single-Image VQA & Grounding Demonstration")
    add_bullet(doc, "Step 1: Launch application at http://localhost:8443 and navigate to the Analyze workspace.")
    add_bullet(doc, "Step 2: In the center Global Explorer, enter 'Hyderabad' into the location search bar (or click the 'Hyderabad' quick preset button).")
    add_bullet(doc, "Step 3: Confirm Year is set to 2024 and sensor toggle is Sentinel-2 Optical.")
    add_bullet(doc, "Step 4: Use the floating GIS toolbar on the map to click 'Draw AOI' and drag a rectangle over the Hussain Sagar water body.")
    add_bullet(doc, "Step 5: Verify the bottom telemetry pill displays the geodesic surface area (e.g., 'Area of Interest: 42.18 km²').")
    add_bullet(doc, "Step 6: Click 'Search Satellite Scenes'. Review the populated scene result cards below the map.")
    add_bullet(doc, "Step 7: Click 'Select Scene' on the first Sentinel-2 L2A scene. Notice the left control panel updates with a non-duplicated summary card.")
    add_bullet(doc, "Step 8: In the left panel, click the example chip: 'Describe the major land-cover types visible in this area.'")
    add_bullet(doc, "Step 9: Click the primary 'Run Analysis' button.")
    add_bullet(doc, "Step 10: Observe the right-side timeline tracking real stages (Validating -> Routing -> Retrieval -> Inference -> Evidence -> Complete).")
    add_bullet(doc, "Step 11: In the center column, inspect the rendered Visual Evidence Canvas. Toggle the 'Grounding Bounding Boxes' layer to observe detected features.")
    add_bullet(doc, "Step 12: Review the multi-factor Confidence score and expand the Execution Trace to inspect stage durations.")
    add_bullet(doc, "Step 13: Click 'Download PDF' to verify the compiled publication-grade vector report.")

    add_heading_2(doc, "24.2 Bi-Temporal Change Detection Demonstration")
    add_bullet(doc, "Step 1: In the left control panel, toggle Analysis Mode to 'Before + After'.")
    add_bullet(doc, "Step 2: Set Pre Year to 2022 and Post Year to 2024.")
    add_bullet(doc, "Step 3: Search and select baseline and target scenes across the Krishna River corridor.")
    add_bullet(doc, "Step 4: Click 'Run Change Analysis'.")
    add_bullet(doc, "Step 5: Toggle between 'Side by side' and 'Swipe' view in the center canvas to drag the split-screen slider across the gold/amber built-up expansion overlay.")

    add_heading_2(doc, "24.3 Optical + SAR Multimodal Fusion Demonstration")
    add_bullet(doc, "Step 1: In the left control panel, toggle Analysis Mode to 'Optical + SAR'.")
    add_bullet(doc, "Step 2: Select a Sentinel-2 optical scene and a Sentinel-1 SAR scene for the same geographic AOI.")
    add_bullet(doc, "Step 3: Click 'Run Analysis'.")
    add_bullet(doc, "Step 4: Inspect the fused evidence layer showing cross-modal agreement between radar double-bounce backscatter and optical settlement textures.")

    # =========================================================================
    # 27. PROJECT STRUCTURE & DEVELOPER SETUP
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "25.0 Project Structure & Developer Setup")
    add_p(doc, "The repository is structured for clean separation between presentation, application logic, and storage:")

    add_code_block(doc,
        "D:\\SIH 2026\\\n"
        "├── package.json              # Frontend Node.js dependencies (React 19, Vite, Leaflet)\n"
        "├── vite.config.ts            # Vite 8 config with reverse proxy (/api/v1 -> localhost:8000)\n"
        "├── src/                      # Frontend TypeScript React source\n"
        "│   ├── main.tsx              # React entrypoint\n"
        "│   ├── App.tsx               # Root route router and theme provider\n"
        "│   ├── components/           # Reusable components (GlobalMap, SatImage, Shell, Uploader)\n"
        "│   ├── pages/                # Workspace views (Analyze, Dashboard, History, Reports, Settings)\n"
        "│   └── lib/                  # Client services (api.ts, firebase.ts, data.ts)\n"
        "├── backend/                  # FastAPI Python application\n"
        "│   ├── requirements.txt      # Pinned Python dependencies (FastAPI, PyProj, Shapely, ReportLab)\n"
        "│   ├── pytest.ini            # Pytest configuration\n"
        "│   ├── app/                  # Application packages\n"
        "│   │   ├── main.py           # FastAPI entrypoint, CORS, static mounts\n"
        "│   │   ├── api/v1/           # API endpoints (analyses, auth, earth, history, reports, system)\n"
        "│   │   ├── core/             # Configuration, database (db.py), auth (firebase.py), errors\n"
        "│   │   ├── models/           # Analytical models (vqa, grounding, change, optical_sar, resource)\n"
        "│   │   ├── schemas/          # Pydantic v2 validation models\n"
        "│   │   └── services/         # Orchestration (async_queue, stac_service, geospatial, reports)\n"
        "│   ├── data/                 # Persistent storage (cache, uploads, evidence, reports, sqlite)\n"
        "│   ├── tests/                # 12 automated unit & integration tests\n"
        "│   └── scripts/              # Build utilities & diagram generators\n"
        "└── docs/                     # Architectural documentation suite"
    )

    add_heading_2(doc, "25.1 Quick-Start Commands for Developers")
    add_p(doc, "1. Frontend Installation & Startup:")
    add_code_block(doc, "pnpm install\npnpm run dev   # Starts Vite server on http://localhost:8443")
    add_p(doc, "2. Backend Virtual Environment & Startup:")
    add_code_block(doc, 
        "cd backend\n"
        "uv venv .venv\n"
        "uv pip install -r requirements.txt\n"
        ".\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    )
    add_p(doc, "3. Execute Test Suite:")
    add_code_block(doc, ".\\.venv\\Scripts\\python.exe -m pytest -v")

    # =========================================================================
    # 28. TECHNICAL APPENDICES
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "26.0 Technical Appendices & System Configuration")

    add_heading_2(doc, "26.1 Environment Variables Reference")
    env_headers = ["Variable Name", "Default Value", "Required", "Security Classification", "Functional Role"]
    env_data = [
        ["ENVIRONMENT", "development", "Yes", "Internal", "Toggles development mock auth and debug logs"],
        ["HOST", "127.0.0.1", "Yes", "Internal", "FastAPI network bind address"],
        ["PORT", "8000", "Yes", "Internal", "FastAPI server listener port"],
        ["CORS_ORIGINS", "*", "No", "Network Security", "Permitted CORS origin whitelist"],
        ["FIREBASE_PROJECT_ID", "satya-dristi-sih2026", "No", "Public Identifier", "Firebase project identifier for JWT verification"],
        ["AWS_STAC_URL", "https://earth-search.aws.element84.com/v1", "No", "Network Service", "STAC endpoint for Sentinel-2 search"],
        ["COPERNICUS_STAC_URL", "https://stac.dataspace.copernicus.eu/v1", "No", "Network Service", "STAC endpoint for Sentinel-1 search"],
    ]
    add_styled_table(doc, env_headers, env_data, col_widths=[1.5, 1.5, 0.8, 1.2, 1.7])

    add_heading_2(doc, "26.2 Technical Glossary")
    gloss_headers = ["Term / Acronym", "Full Expansion", "Definition & Context in Satya Dristi"]
    gloss_data = [
        ["STAC", "SpatioTemporal Asset Catalog", "Open standard for describing geospatial asset metadata across time and space."],
        ["COG", "Cloud-Optimized GeoTIFF", "Tiled, internally-indexed TIFF enabling HTTP range requests for spatial subsets."],
        ["BOA", "Bottom-of-Atmosphere", "Atmospherically corrected surface reflectance (Sentinel-2 Level-2A)."],
        ["GRD", "Ground Range Detected", "Synthetic aperture radar product projected onto Earth ellipsoid (Sentinel-1)."],
        ["CVA", "Change Vector Analysis", "Multi-spectral mathematical difference technique quantifying change magnitude."],
        ["VQA", "Visual Question Answering", "Multimodal intelligence task answering text queries regarding visual image content."],
        ["EPSG:6933", "World Cylindrical Equal Area", "Projected coordinate reference system preserving true physical surface area globally."],
        ["Platypus", "Page Layout and Typography", "ReportLab document layout engine compiling flowable PDF paragraphs, tables, and images."],
    ]
    add_styled_table(doc, gloss_headers, gloss_data, col_widths=[1.2, 1.8, 3.7])

    # =========================================================================
    # 29. FINAL AUDIT TABLE & TECHNICAL VERDICT
    # =========================================================================
    doc.add_page_break()
    add_heading_1(doc, "27.0 Final Implementation Audit Table")
    add_p(doc, "The following definitive audit table classifies every feature subsystem according to the strict verification standard:")

    audit_headers = ["Subsystem Feature", "Real Implemented", "Mock / Demo", "Partially Implemented", "Not Implemented", "Code Evidence / Reality"]
    audit_data = [
        ["Authentication", "", "", "✓", "", "backend/app/core/firebase.py: Token verification with dev token fallback."],
        ["Global Satellite Map", "✓", "", "", "", "src/components/GlobalMap.tsx: Leaflet map with real Esri satellite tiles."],
        ["STAC Catalogue Search", "✓", "", "", "", "backend/app/services/stac_service.py: Live AWS Earth Search & Copernicus queries."],
        ["Year Selection (2016-2026)", "✓", "", "", "", "GlobalMap.tsx and stac_service.py: ISO-8601 temporal range filtering."],
        ["AOI Drawing & Bounding", "✓", "", "", "", "src/components/GlobalMap.tsx: Leaflet drag-to-draw rectangle toolbar."],
        ["Geodesic Surface Area", "✓", "", "", "", "backend/app/services/geospatial_processor.py: PyProj EPSG:6933 equal area."],
        ["Single-Image VQA", "✓", "", "", "", "backend/app/models/vqa_specialist.py: Spectral decomposition & edge density."],
        ["Spatial Grounding", "✓", "", "", "", "backend/app/models/grounding_specialist.py: Morphological contours & bounding boxes."],
        ["Bi-Temporal Change", "✓", "", "", "", "backend/app/models/change_specialist.py: CVA magnitude & RGBA change overlay."],
        ["Optical + SAR Fusion", "✓", "", "", "", "backend/app/models/optical_sar_specialist.py: Radar backscatter dB & double bounce."],
        ["Agentic Task Routing", "✓", "", "", "", "backend/app/services/task_router.py: Deterministic rule-based intent router."],
        ["Observable Execution Trace", "✓", "", "", "", "backend/app/services/async_queue.py: Real milestone timers & hardware detail."],
        ["Confidence Estimation", "✓", "", "", "", "backend/app/services/confidence_engine.py: Multi-signal heuristic scoring."],
        ["Visual Evidence Canvas", "✓", "", "", "", "src/components/SatImage.tsx: Multi-layer opacity, swipe, and side-by-side."],
        ["Publication-Grade PDF", "✓", "", "", "", "backend/app/services/report_generator.py: ReportLab Platypus vector PDF on disk."],
        ["Structured JSON Export", "✓", "", "", "", "backend/app/services/report_generator.py: Machine-readable GeoJSON & audit export."],
        ["Persistent History", "✓", "", "", "", "backend/app/api/v1/history.py: Full analysis archive with search & filters."],
        ["Database Storage", "✓", "", "", "", "backend/app/core/db.py: Dual-mode Google Cloud Firestore and SQLite store."],
        ["Hardware Telemetry", "✓", "", "", "", "backend/app/api/v1/system.py: Real PyTorch CUDA & psutil hardware monitor."],
        ["ISRO Bhoonidhi Ingestion", "", "", "", "✓", "No Bhoonidhi API integration in current code; fulfilled via ESA Sentinel open data."],
    ]
    add_styled_table(doc, audit_headers, audit_data, col_widths=[1.5, 0.6, 0.6, 0.9, 0.8, 2.1])

    add_heading_1(doc, "28.0 Final Technical Verdict")
    add_p(doc, "1. Architecture Maturity:", bold_prefix="Maturity Assessment — ")
    add_p(doc, "Production-Grade Infrastructure with Algorithmic Computer Vision Execution. The repository is architecturally sound, featuring clean separation of concerns, robust Pydantic data validation, resilient domain error handling, asynchronous queue management, dual-mode database persistence, and publication-quality PDF compilation.")

    add_p(doc, "2. Most Complete Subsystems:", bold_prefix="Strengths — ")
    add_bullet(doc, "Geospatial Ingestion & AOI Processing: STAC search, AOI bounding, coordinate transformations, and PyProj geodesic area calculations are robust, tested, and fully functional.")
    add_bullet(doc, "Report Generation: ReportLab Platypus PDF compilation and structured JSON export are complete, fully styled, and embed genuine evidence and metadata.")
    add_bullet(doc, "Analyze Workspace UX: The 3-column desktop layout with Leaflet map dominance, uncramped 2-row search controls, multi-layer evidence canvases, and timeline pipeline is mature and intuitive.")
    add_bullet(doc, "Persistence Layer: Dual-mode storage seamlessly bridges local offline development (SQLite) and enterprise cloud deployment (Google Cloud Firestore).")

    add_p(doc, "3. Most Incomplete Subsystems:", bold_prefix="Gaps — ")
    add_bullet(doc, "Direct AWS Requester-Pays S3 Access: Full 12-band raw COG downloads are not wired to authenticated AWS buckets; the platform currently operates on high-resolution preview and cropped satellite tile arrays.")
    add_bullet(doc, "OAuth Web Client Popup: Client-side Firebase Google Sign-In is configured with local developer profile generation rather than loading the full Google identity provider popup script.")

    add_p(doc, "4. Critical Technical Distinction:", bold_prefix="Integrity Classification — ")
    add_p(doc, "The four analytical specialists (VQA, Grounding, Change Detection, Optical-SAR Fusion) execute robust, deterministic remote-sensing computer vision and spectral decomposition algorithms rather than multi-gigabyte fine-tuned neural network checkpoints.")

    add_p(doc, "5. Priority Engineering Roadmap:", bold_prefix="Remaining Engineering Tasks — ")
    add_bullet(doc, "Load fine-tuned remote-sensing Vision-Language Transformer weights into ModelResourceManager.")
    add_bullet(doc, "Configure AWS S3 credentials for direct 12-band Sentinel-2 COG downloading.")
    add_bullet(doc, "Implement Redis and Celery worker queues for distributed multi-user deployments.")
    add_bullet(doc, "Add ISRO Bhoonidhi STAC ingestion connectors when public API credentials become available.")

    # Save to both target locations
    print(f"Saving Word document to: {OUTPUT_DOCX_ROOT}")
    doc.save(str(OUTPUT_DOCX_ROOT))

    print(f"Saving duplicate to: {OUTPUT_DOCX_DOCS}")
    shutil.copyfile(str(OUTPUT_DOCX_ROOT), str(OUTPUT_DOCX_DOCS))
    print("SUCCESS: Document generation complete!")

if __name__ == "__main__":
    build_document()
