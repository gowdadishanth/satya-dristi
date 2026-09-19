# Satya Dristi (सत्य दृष्टि)
### Multimodal Earth-Observation Intelligence Platform

Satya Dristi is an intelligence and analysis platform that empowers analysts to query, inspect, and analyze genuine Earth-observation satellite observations in natural language. The platform combines public Earth observation catalogues (**Copernicus Data Space Ecosystem** and **AWS Earth Search STAC**) with a specialist ensemble of remote-sensing models to deliver auditable, evidence-grounded answers.

---

## 🛰️ Architecture & Capabilities

```
+-----------------------------------------------------------------------------------+
|                                  Frontend                                         |
|  - React 19 + Vite + Tailwind CSS v4                                              |
|  - Interactive Global Map (Leaflet) with global geocoding & AOI bounding box     |
|  - Multi-decade historical observation search (2016 - 2026)                       |
|  - Visual Evidence: Bounding boxes, CVA Change Maps, Optical+SAR fused overlays    |
|  - Firebase Google Sign-In & Authentication state tracking                        |
+-----------------------------------------------------------------------------------+
                                         │  HTTP / REST (Bearer JWT)
                                         ▼
+-----------------------------------------------------------------------------------+
|                             FastAPI Geospatial Backend                            |
|  - Core Security: Firebase Admin token validation + Multi-tenant isolation        |
|  - Async Job Execution Queue with observable stage telemetry                      |
|  - Document Store: Firestore Client with offline JSON/SQLite persistence fallback |
+-----------------------------------------------------------------------------------+
        │                                  │                                  │
        ▼                                  ▼                                  ▼
┌───────────────────┐            ┌───────────────────┐            ┌───────────────────┐
│   STAC Catalog    │            │ Geospatial Engine │            │ Model Specialists │
│ - Copernicus L2A  │            │ - Rasterio & GDAL │            │ - RS-VLM (Remote  │
│ - Sentinel-1 GRD  │            │ - Shapely AOI     │            │   CLIP / VQA)     │
│ - AWS Earth Search│            │ - PyProj CRS      │            │ - Grounding / Box │
│ - Band Extraction │            │ - NDVI / NDWI     │            │ - Bi-Temporal CVA │
│ - GeoTIFF/COG Clip│            │ - SAR dB Sigma0   │            │ - Optical+SAR Fuse│
└───────────────────┘            └───────────────────┘            └───────────────────┘
                                                                            │
                                                                            ▼
                                                                  ┌───────────────────┐
                                                                  │ ReportLab Engine  │
                                                                  │ - Official PDF    │
                                                                  │ - Embedded Images │
                                                                  │ - Execution Trace │
                                                                  │ - JSON Metadata   │
                                                                  └───────────────────┘
```

---

## 🌍 Core Workflow

1. **Global Map & Geocoding**: Select or search any geographic location on Earth.
2. **Year & Date Selection**: Filter across 10 years of real satellite observations (2016–2026) for Sentinel-2 Optical (10m L2A) and Sentinel-1 SAR (C-band GRD).
3. **Real Scene Search**: Live queries to the Copernicus Data Space STAC (`stac.dataspace.copernicus.eu/v1`) and AWS Earth Search STAC (`earth-search.aws.element84.com/v1`).
4. **AOI Selection**: Draw or select bounding boxes/polygons. Backend computes exact geographic bounds, centroid, and area in km².
5. **On-Demand Imagery Retrieval**: Extracts real satellite assets, clips to the AOI, and caches locally under `backend/data/cache`.
6. **Task Routing & Specialist Models**:
   - **Single-Image VQA & Scene Description**: Interprets land-cover, infrastructure, and environmental patterns.
   - **Grounding & Localization**: Identifies target features and delineates pixel and geographic bounding boxes and segmentation masks.
   - **Bi-Temporal Change Detection**: Genuine Change Vector Analysis (CVA) and structural differentiation over before/after observations, generating classified change maps (built-up gain, water variation, stable background).
   - **Optical + SAR Multimodal Fusion**: Fuses optical multi-spectral reflectance with Sentinel-1 SAR radar backscatter ($\sigma^0$ in dB) to penetrate cloud cover and distinguish high-backscatter urban structures from calm water surfaces.
7. **Calibrated Confidence**: Multi-factor confidence score derived from cross-modal agreement, cloud cover penalty, and spatial overlap.
8. **Observable Execution Trace**: Real stage-by-stage timings without exposing hidden chain-of-thought.
9. **Official Report Export**: Publication-grade, server-side ReportLab PDF reports embedding genuine visual evidence, scene coordinates, sensor parameters, and audit trails.

---

## 🚀 Getting Started

### Prerequisites
- **Node.js**: v20+ and pnpm / npm
- **Python**: 3.10+ (Python 3.11 recommended)
- **Git**

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Windows (or source .venv/bin/activate on Linux/macOS)

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure environment variables in backend/.env
cp .env.example .env

# Run automated test suite
python -m pytest tests -v

# Start FastAPI server on port 8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend documentation will be accessible at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 2. Frontend Setup

```bash
# In the root project directory
npm install

# Start Vite dev server (proxies /api and /static to http://127.0.0.1:8000)
npm run dev
```

Open `http://localhost:8443` in your browser.

---

## 🧪 Verification & Testing

The backend includes a comprehensive pytest suite and live end-to-end verification scripts:

```bash
# Run pytest unit and integration tests (12 tests)
backend\.venv\Scripts\python.exe -m pytest backend/tests -v

# Run live end-to-end API test (Scene search -> AOI -> Inference -> Evidence -> PDF)
backend\.venv\Scripts\python.exe backend/verify_live_e2e.py

# Run live bi-temporal change and optical-SAR fusion test
backend\.venv\Scripts\python.exe backend/verify_temporal_and_fusion.py
```

---

## 🔒 Security & Persistence

- **Firebase Authentication**: Client passes Firebase ID tokens via `Authorization: Bearer <token>`. In development, dev tokens (`dev-token-<uid>`) are accepted for local offline development.
- **Firestore Integration**: User records, analysis sessions, reports, and evidence references are saved in Firestore (with automatic local SQLite/JSON document store fallback for offline/air-gapped setups).
- **Multi-Tenant Isolation**: Analyses and reports are strictly scoped to the authenticated UID.

---

## 📄 License
Released for Satya Dristi Earth-Observation Intelligence.
