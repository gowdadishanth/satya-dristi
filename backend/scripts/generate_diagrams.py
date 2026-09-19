import os
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Output directory for diagrams
DIAGRAM_DIR = Path(__file__).resolve().parent / "diagrams"
DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)

# Styling Constants matching Satya Dristi theme
C_PRIMARY = "#313851"     # Deep Slate
C_ACCENT = "#AB7C2C"      # Amber Gold
C_SECONDARY = "#4F6F8A"   # Steel Blue
C_NEUTRAL = "#C2CBD3"     # Silver Neutral
C_BG = "#F6F3ED"          # Cream Canvas
C_WHITE = "#FFFFFF"
C_TEXT = "#1E293B"
C_MUTED = "#64748B"
C_OK = "#2E7D32"
C_WARN = "#ED6C02"

def save_fig(fig, filename):
    out_path = DIAGRAM_DIR / filename
    fig.savefig(str(out_path), dpi=200, bbox_inches="tight", facecolor=C_WHITE)
    plt.close(fig)
    print(f"Generated diagram: {filename}")

# -------------------------------------------------------------
# Diagram 1: Overall System Architecture
# -------------------------------------------------------------
def make_diagram_1():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.axis("off")

    # Title
    ax.text(5, 9.5, "Satya Dristi · Overall System Architecture", ha="center", va="center",
            fontsize=13, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    # Boxes: [x, y, w, h, title, subtitle, color]
    boxes = [
        # Presentation
        (0.5, 6.2, 2.5, 2.3, "Presentation Tier\n(React 19 + Vite 8)", "• Leaflet 1.9.4 Explorer\n• 3-Column Workspace\n• Multi-Layer Evidence Canvas\n• Timeline Pipeline", C_PRIMARY),
        # API Gateway
        (3.7, 6.2, 2.6, 2.3, "API Gateway Tier\n(FastAPI / Python 3.11)", "• REST Routing (/api/v1)\n• Asynchronous Job Queue\n• Hardware Telemetry Engine\n• Domain Error Sanitizer", C_SECONDARY),
        # Geospatial
        (7.0, 6.2, 2.5, 2.3, "Geospatial & Ingestion\n(STAC + GDAL/Shapely)", "• AWS Earth Search STAC\n• Copernicus Data Space\n• PyProj EPSG:6933 Area\n• AOI Raster Clipper", C_PRIMARY),
        
        # Specialist Models
        (0.5, 2.2, 4.2, 2.6, "Specialist Model Engine\n(Memory-Aware Remote Sensing)", "• VQASpecialist: Spectral Index Decomposition\n• GroundingSpecialist: Contour Localization\n• ChangeSpecialist: CVA & Structural Diff\n• OpticalSARSpecialist: Radiometric Fusion\n• Deterministic Task Router", C_PRIMARY),
        # Evidence & Confidence
        (5.3, 2.2, 4.2, 2.6, "Evidence, Storage & Reports\n(Dual-Mode Persistence)", "• Multi-Signal Confidence Engine\n• RGBA Evidence Overlays (PNG)\n• Google Cloud Firestore / SQLite Store\n• ReportLab Vector PDF & JSON Export\n• Observable Execution Trace", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in boxes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        # Header banner
        banner = patches.Rectangle((x, y + h - 0.65), w, 0.65, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.32, title, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.15, y + (h - 0.65)/2, desc, ha="left", va="center",
                fontsize=7.5, color=C_TEXT, fontfamily="sans-serif", linespacing=1.4)

    # Connecting Arrows
    arrows = [
        ((3.0, 7.35), (3.7, 7.35), "REST HTTP"),
        ((6.3, 7.35), (7.0, 7.35), "STAC Query"),
        ((5.0, 6.2), (2.6, 4.8), "Dispatch Task"),
        ((5.0, 6.2), (7.4, 4.8), "Persist State"),
        ((4.7, 3.5), (5.3, 3.5), "Output Evidence"),
    ]
    for (x1, y1), (x2, y2), label in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.6))
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2 + 0.18
        ax.text(mid_x, mid_y, label, ha="center", va="center",
                fontsize=7, fontweight="bold", color=C_ACCENT, fontfamily="sans-serif")

    ax.set_xlim(0, 10)
    ax.set_ylim(1.5, 10)
    save_fig(fig, "diagram_system_overview.png")

# -------------------------------------------------------------
# Diagram 2: Frontend 3-Column Layout Architecture
# -------------------------------------------------------------
def make_diagram_2():
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")

    ax.text(5, 9.2, "Satya Dristi · Frontend 3-Column Desktop Grid Architecture", ha="center", va="center",
            fontsize=13, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    cols = [
        (0.5, 2.0, 2.6, 6.4, "LEFT: Control Panel (~300px)", [
            ("1. Input Source", "Global Map vs Manual Upload"),
            ("2. Analysis Mode", "Single | Optical+SAR | Temporal"),
            ("3. Selected Scene", "Sensor, Date, Cloud, ID (compact)"),
            ("4. Natural Query", "Textarea for VQA questions"),
            ("5. Quick Examples", "Concise query prompt chips"),
            ("6. Primary Action", "Run Analysis / Change Analysis"),
        ], C_PRIMARY),
        (3.5, 2.0, 4.0, 6.4, "CENTER: Earth Observation Explorer (~750px)", [
            ("Header & Context Bar", "Location, Coordinates, Active status"),
            ("Row 1: Search & Sensors", "Place search + Year 2016-2026 + Sensor"),
            ("Row 2: Cloud & Actions", "Cloud cover filter + Presets + Search"),
            ("Large Leaflet Map (460px)", "Esri satellite tiles + Drag-to-Draw AOI"),
            ("Compact GIS Toolbar", "Zoom In/Out, Reset center, Draw AOI"),
            ("Scene Results Below Map", "Readable grid of Sentinel-2/1 cards"),
            ("Post-Analysis Canvas", "Multi-layer evidence & Answer panel"),
        ], C_ACCENT),
        (7.9, 2.0, 1.8, 6.4, "RIGHT: Pipeline (~280px)", [
            ("Analysis Pipeline", "1. Query interpretation"),
            ("Timeline Stages", "2. Input validation\n3. Task selection\n4. Specialist routing\n5. Model inference\n6. Evidence fusion\n7. Confidence rating\n8. Result generation"),
            ("Observable Telemetry", "18px indicators, nominal detail"),
            ("Result Audit", "Confidence agreement"),
            ("Execution Trace", "Collapsible stage timings"),
            ("Report Export", "PDF & JSON download"),
        ], C_SECONDARY),
    ]

    for x, y, w, h, header, items, col in cols:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.55), w, 0.55, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.28, header, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        
        curr_y = y + h - 0.85
        for title, detail in items:
            ax.text(x + 0.12, curr_y, title, fontsize=7.5, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")
            curr_y -= 0.24
            ax.text(x + 0.12, curr_y, detail, fontsize=6.8, color=C_TEXT, fontfamily="sans-serif")
            curr_y -= 0.42

    ax.set_xlim(0, 10.2)
    ax.set_ylim(1.5, 9.8)
    save_fig(fig, "diagram_frontend_layout.png")

# -------------------------------------------------------------
# Diagram 3: Backend Layered Architecture
# -------------------------------------------------------------
def make_diagram_3():
    fig, ax = plt.subplots(figsize=(10, 5.0))
    ax.axis("off")

    ax.text(5, 9.3, "Satya Dristi · Backend Layered Service Architecture", ha="center", va="center",
            fontsize=13, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    layers = [
        (0.6, 7.3, 8.8, 1.3, "API Router Layer (FastAPI / ASGI)", 
         "auth.py (/auth) · earth.py (/earth) · analyses.py (/analyses) · history.py (/history) · reports.py (/reports) · system.py (/system)", C_PRIMARY),
        (0.6, 5.5, 8.8, 1.3, "Service & Orchestration Layer", 
         "async_queue.py (JobManager) · task_router.py (Router) · stac_service.py (STAC) · geospatial_processor.py (Shapely/PyProj) · report_generator.py", C_SECONDARY),
        (0.6, 3.7, 8.8, 1.3, "AI / Specialist Model Layer", 
         "resource_manager.py (PyTorch CUDA) · vqa_specialist.py (VQA) · grounding_specialist.py (Grounding) · change_specialist.py (CVA) · optical_sar_specialist.py", C_PRIMARY),
        (0.6, 1.9, 8.8, 1.3, "Data Access & Persistence Layer", 
         "db.py (DatabaseService: Firestore Client / LocalDocumentStore SQLite) · firebase.py (Auth Verification) · data/ (Cache, Evidence, Reports)", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in layers:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + 0.2, y + h - 0.22, title, ha="left", va="center",
                fontsize=8.5, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.2, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.5, color=C_TEXT, fontfamily="sans-serif")

    # Connecting arrows
    for y_start in [7.3, 5.5, 3.7]:
        ax.annotate("", xy=(5.0, y_start), xytext=(5.0, y_start + 0.2),
                    arrowprops=dict(arrowstyle="<-", color=C_ACCENT, lw=2.0))

    ax.set_xlim(0, 10)
    ax.set_ylim(1.5, 9.8)
    save_fig(fig, "diagram_backend_layers.png")

# -------------------------------------------------------------
# Diagram 4: Authentication Flow
# -------------------------------------------------------------
def make_diagram_4():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · Authentication & Session Flow", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.5, 4.5, 1.8, 2.0, "Analyst Login", "• User profile in UI\n• Sign-in trigger\n• LocalStorage session", C_PRIMARY),
        (2.7, 4.5, 1.8, 2.0, "Token Generation", "• Firebase Web SDK\n• dev-token-<uid>\n• Bearer Authorization", C_SECONDARY),
        (4.9, 4.5, 2.0, 2.0, "Token Verification", "• firebase.py middleware\n• RSA cert verification\n• Dev token decoder", C_PRIMARY),
        (7.3, 4.5, 1.8, 2.0, "User Scoping", "• UID multi-tenancy\n• Firestore user save\n• Analysis ownership", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.5)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_auth_flow.png")

# -------------------------------------------------------------
# Diagram 5: Satellite STAC Ingestion & Scene Discovery
# -------------------------------------------------------------
def make_diagram_5():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · Satellite Data STAC Ingestion Pipeline", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.4, 4.5, 1.8, 2.0, "1. Location & Query", "• Place geocoding\n• Lat/Lon coordinates\n• Year: 2016-2026\n• Cloud cover filter", C_PRIMARY),
        (2.6, 4.5, 2.0, 2.0, "2. STAC Gateways", "• AWS Earth Search\n• Copernicus Ecosystem\n• Sentinel-2 L2A (Opt)\n• Sentinel-1 GRD (SAR)", C_SECONDARY),
        (5.0, 4.5, 1.8, 2.0, "3. Scene Selection", "• Footprint overlap\n• Date & cloud check\n• Authentic thumbnail\n• Scene metadata", C_PRIMARY),
        (7.2, 4.5, 2.0, 2.0, "4. Asset Processing", "• AOI raster clipping\n• Lanczos resampling\n• SAR logarithmic dB\n• Cache: data/cache/", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.6)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_satellite_pipeline.png")

# -------------------------------------------------------------
# Diagram 6: AOI Processing Flow
# -------------------------------------------------------------
def make_diagram_6():
    fig, ax = plt.subplots(figsize=(9, 4.0))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · AOI Geometry & Geodesic Surface Area Flow", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.4, 4.5, 1.8, 2.0, "Map Interaction", "• Drag-to-draw box\n• Polygon GeoJSON\n• WGS84 coordinates", C_PRIMARY),
        (2.6, 4.5, 2.0, 2.0, "Geometry Validation", "• Shapely validation\n• Range check [-180,180]\n• Zero-buffer self-fix", C_SECONDARY),
        (5.0, 4.5, 2.0, 2.0, "Geodesic Projection", "• PyProj transformer\n• EPSG:6933 Equal Area\n• True surface km²", C_PRIMARY),
        (7.4, 4.5, 1.8, 2.0, "Raster Subsetting", "• Bbox ratio crop\n• Pixel coordinate map\n• Model-ready tensor", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.6)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_aoi_processing.png")

# -------------------------------------------------------------
# Diagram 7: End-to-End Analysis Pipeline
# -------------------------------------------------------------
def make_diagram_7():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.axis("off")

    ax.text(5, 7.8, "Satya Dristi · Asynchronous Analysis Execution Pipeline", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    stages = [
        ("1. Validating", "Verify AOI & CRS", C_PRIMARY),
        ("2. Routing", "Query Classification", C_SECONDARY),
        ("3. Retrieval", "Clip AOI Raster", C_PRIMARY),
        ("4. Inference", "Specialist Execution", C_SECONDARY),
        ("5. Evidence", "Render Visual Masks", C_PRIMARY),
        ("6. Confidence", "Multi-Signal Rating", C_SECONDARY),
        ("7. Reports", "PDF/JSON Artifacts", C_PRIMARY),
    ]

    for i, (name, desc, col) in enumerate(stages):
        x = 0.3 + i * 1.38
        y = 4.5
        w = 1.25
        h = 2.0
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.4)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, name, ha="center", va="center",
                fontsize=7.5, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + w/2, y + (h - 0.45)/2, desc, ha="center", va="center",
                fontsize=6.8, color=C_TEXT, fontfamily="sans-serif")

        if i < len(stages) - 1:
            ax.annotate("", xy=(x + w + 0.13, 5.5), xytext=(x + w, 5.5),
                        arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.5))

    ax.set_xlim(0, 10.2)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_analysis_pipeline.png")

# -------------------------------------------------------------
# Diagram 8: Bi-Temporal Change Detection Flow
# -------------------------------------------------------------
def make_diagram_8():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · Bi-Temporal Change Detection (CVA)", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.4, 4.5, 1.8, 2.0, "Temporal Pair", "• Observation 1 (2022)\n• Observation 2 (2024)\n• Spatial alignment check", C_PRIMARY),
        (2.6, 4.5, 2.0, 2.0, "CVA Magnitude", "• Band difference (A-B)\n• Euclidean magnitude\n• Structural diff absdiff", C_SECONDARY),
        (5.0, 4.5, 2.0, 2.0, "Adaptive Threshold", "• 82nd percentile cutoff\n• Morphological opening\n• Noise elimination", C_PRIMARY),
        (7.4, 4.5, 1.8, 2.0, "Evidence Overlay", "• Gold: Built-up gain\n• Blue: Water extent\n• RGBA change map PNG", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.6)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_change_detection.png")

# -------------------------------------------------------------
# Diagram 9: Optical + SAR Fusion Flow
# -------------------------------------------------------------
def make_diagram_9():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · Optical + SAR Cross-Modal Fusion", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.4, 4.5, 1.8, 2.0, "Dual Modalities", "• Sentinel-2 MSI Optical\n• Sentinel-1 SAR GRD\n• CRS co-registration", C_PRIMARY),
        (2.6, 4.5, 2.0, 2.0, "Modality Analysis", "• Optical: Vegetation/water\n• SAR: dB transform\n• Backscatter reflection", C_SECONDARY),
        (5.0, 4.5, 2.0, 2.0, "Cross-Agreement", "• Urban: Double bounce\n• Water: Specular low-dB\n• Boolean intersection", C_PRIMARY),
        (7.4, 4.5, 1.8, 2.0, "Fused Evidence", "• Multi-band confidence\n• Highlighted consensus\n• Fused PNG overlay", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.6)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_optical_sar_fusion.png")

# -------------------------------------------------------------
# Diagram 10: Report Generation Flow
# -------------------------------------------------------------
def make_diagram_10():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    ax.text(4.5, 7.8, "Satya Dristi · Publication-Grade Report Generation", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C_PRIMARY, fontfamily="sans-serif")

    steps = [
        (0.4, 4.5, 1.8, 2.0, "Analysis Record", "• Answer text\n• Land-cover metrics\n• Observable trace\n• Evidence PNGs", C_PRIMARY),
        (2.6, 4.5, 2.0, 2.0, "ReportLab Platypus", "• SimpleDocTemplate\n• Custom styles (#313851)\n• Formatted tables\n• Embedded images", C_SECONDARY),
        (5.0, 4.5, 2.0, 2.0, "Artifact Storage", "• Vector PDF on disk\n• Structured JSON export\n• Saved in data/reports/", C_PRIMARY),
        (7.4, 4.5, 1.8, 2.0, "Client Download", "• GET /download\n• Content-Type: pdf\n• Content-Disposition\n• Audit compliance", C_SECONDARY),
    ]

    for x, y, w, h, title, desc, col in steps:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                      facecolor=C_BG, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        banner = patches.Rectangle((x, y + h - 0.45), w, 0.45, facecolor=col, edgecolor=col)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.22, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_WHITE, fontfamily="sans-serif")
        ax.text(x + 0.1, y + (h - 0.45)/2, desc, ha="left", va="center",
                fontsize=7.2, color=C_TEXT, fontfamily="sans-serif", linespacing=1.3)

    for i in range(len(steps)-1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        y = 5.5
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=C_ACCENT, lw=1.8))

    ax.set_xlim(0, 9.6)
    ax.set_ylim(3.5, 8.5)
    save_fig(fig, "diagram_report_generation.png")

if __name__ == "__main__":
    make_diagram_1()
    make_diagram_2()
    make_diagram_3()
    make_diagram_4()
    make_diagram_5()
    make_diagram_6()
    make_diagram_7()
    make_diagram_8()
    make_diagram_9()
    make_diagram_10()
    print("All 10 diagrams generated successfully in:", DIAGRAM_DIR)
