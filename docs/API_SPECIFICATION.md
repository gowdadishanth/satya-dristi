# Satya Dristi · REST API Specification

**Version**: 1.0.0  
**Base URL**: `/api/v1`  
**Protocol**: HTTP/1.1 · HTTPS  
**Data Format**: JSON (`application/json`) · Multipart (`multipart/form-data`) · Binary PDF (`application/pdf`)  
**Authentication**: Firebase Bearer Token (`Authorization: Bearer <ID_TOKEN>`)

---

## 1. Authentication & Security

### Header Format
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```
* In production, the token is verified using `firebase_admin.auth.verify_id_token`.
* In development mode (`ENVIRONMENT=development`), tokens formatted as `dev-token-<uid>` or `test-token-<uid>` are automatically decoded to allow seamless local testing and analyst workflows.

---

## 2. API Endpoints Inventory

### Summary Table

| Category | Method | Path | Auth | Description | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication** | `GET` | `/api/v1/auth/me` | Bearer | Get current analyst profile | `src/lib/api.ts` (`api.auth.me`) |
| **Earth Observation**| `POST` | `/api/v1/earth/scenes/search` | Bearer | Search public STAC satellite scenes (2016–2026) | `src/lib/api.ts` (`api.earth.searchScenes`) |
| **Earth Observation**| `GET` | `/api/v1/earth/scenes/{scene_id}` | Bearer | Retrieve detailed metadata for a scene | `src/lib/api.ts` (`api.earth.getScene`) |
| **Earth Observation**| `POST` | `/api/v1/earth/aoi/preview` | Bearer | Validate AOI geometry & compute geodesic area | `src/lib/api.ts` (`api.earth.previewAOI`) |
| **Earth Observation**| `POST` | `/api/v1/earth/compatibility`| Bearer | Check temporal & CRS compatibility of two scenes | `src/lib/api.ts` (`api.earth.checkCompatibility`) |
| **Earth Observation**| `POST` | `/api/v1/earth/imagery` | Bearer | Retrieve and clip raster imagery for a scene | `src/lib/api.ts` (`api.earth.retrieveImagery`) |
| **Analysis** | `POST` | `/api/v1/analyses` | Bearer | Submit asynchronous analysis job (JSON payload) | `src/lib/api.ts` (`api.analyses.create`) |
| **Analysis** | `POST` | `/api/v1/analyses/upload` | Bearer | Submit analysis job with direct file upload | `src/lib/api.ts` (`api.analyses.createUpload`) |
| **Analysis** | `GET` | `/api/v1/analyses/{id}/status` | Bearer | Poll job execution state and progress % | `src/lib/api.ts` (`api.analyses.getStatus`) |
| **Analysis** | `GET` | `/api/v1/analyses/{id}` | Bearer | Get full analysis result, evidence, and trace | `src/lib/api.ts` (`api.analyses.getDetail`) |
| **Analysis** | `GET` | `/api/v1/analyses/{id}/evidence`| Bearer| Retrieve raw visual evidence overlay image | Direct static URL |
| **History** | `GET` | `/api/v1/history` | Bearer | Fetch user's persistent analysis history | `src/lib/api.ts` (`api.history.list`) |
| **Reports** | `GET` | `/api/v1/reports` | Bearer | List generated reports for user | `src/lib/api.ts` (`api.reports.list`) |
| **Reports** | `GET` | `/api/v1/reports/{id}` | Bearer | Get metadata for a specific report | `src/lib/api.ts` (`api.reports.getDetail`) |
| **Reports** | `GET` | `/api/v1/reports/{id}/download`| Bearer| Download publication-grade vector PDF report | `src/lib/api.ts` (`api.reports.downloadPdf`) |
| **Reports** | `GET` | `/api/v1/reports/{id}/json` | Bearer | Download structured auditable JSON report | `src/lib/api.ts` (`api.reports.downloadJson`) |
| **System** | `GET` | `/api/v1/system/health` | None | Hardware telemetry, VRAM, and provider health | `src/lib/api.ts` (`api.system.getHealth`) |
| **System** | `GET` | `/` | None | Root operational probe | Root ping |

---

## 3. Detailed Endpoint Specifications

### 3.1 Authentication

#### `GET /api/v1/auth/me`
* **Purpose**: Retrieves the verified profile of the current analyst and creates or updates their user record in Firestore / SQLite.
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Response (200 OK)**:
```json
{
  "uid": "dev_user_earth_analyst_01",
  "email": "analyst@satyadristi.org",
  "name": "R. Sharma",
  "picture": "",
  "is_dev": true
}
```
* **Errors**: `401 Unauthorized` if token is invalid or expired.

---

### 3.2 Earth Observation & STAC

#### `POST /api/v1/earth/scenes/search`
* **Purpose**: Queries public STAC catalogues (AWS Earth Search and Copernicus Data Space) for authentic Sentinel-2 and Sentinel-1 satellite imagery.
* **Request Body**:
```json
{
  "bbox": [78.4, 17.3, 78.5, 17.5],
  "geometry": null,
  "year": 2024,
  "start_date": null,
  "end_date": null,
  "sensor": "optical",
  "cloud_cover_max": 30.0,
  "limit": 8
}
```
* **Response (200 OK)**:
```json
[
  {
    "scene_id": "S2A_43QHV_20241223_0_L2A",
    "collection": "sentinel-2-l2a",
    "provider": "AWS Open Data",
    "platform": "Sentinel-2",
    "instrument": "MSI",
    "sensor": "Multispectral Instrument (MSI)",
    "processing_level": "Level-2A Bottom-Of-Atmosphere (BOA)",
    "acquisition_datetime": "2024-12-23T05:24:19Z",
    "cloud_cover": 7.57,
    "bbox": [78.23, 17.15, 79.15, 18.12],
    "geometry": { "type": "Polygon", "coordinates": [...] },
    "preview_url": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/.../thumbnail.jpg",
    "available_bands": ["B02", "B03", "B04", "B08", "TCI"],
    "assets": { ... }
  }
]
```
* **Errors**: `400 Bad Request` if coordinates are invalid; `404 Not Found` if no scenes match criteria.

#### `POST /api/v1/earth/aoi/preview`
* **Purpose**: Validates user-selected bounding box or GeoJSON polygon and computes geodesic surface area in square kilometers.
* **Request Body**:
```json
{
  "bbox": [78.44, 17.40, 78.50, 17.46],
  "geometry": null
}
```
* **Response (200 OK)**:
```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[78.44, 17.4], [78.5, 17.4], [78.5, 17.46], [78.44, 17.46], [78.44, 17.4]]]
  },
  "bbox": [78.44, 17.4, 78.5, 17.46],
  "centroid": [78.47, 17.43],
  "area_sq_km": 42.18
}
```
* **Errors**: `400 Bad Request` if coordinates are non-numeric or exceed $[-180, 180] \times [-90, 90]$.

---

### 3.3 Analysis Workflow

#### `POST /api/v1/analyses`
* **Purpose**: Dispatches an asynchronous remote-sensing analysis job referencing a selected STAC scene and AOI.
* **Request Body**:
```json
{
  "mode": "single",
  "query": "Describe the major land-cover types visible in this area.",
  "scene_id": "S2A_43QHV_20241223_0_L2A",
  "aoi": {
    "bbox": [78.44, 17.4, 78.5, 17.46],
    "centroid": [78.47, 17.43],
    "area_sq_km": 42.18
  },
  "before_scene_id": null,
  "after_scene_id": null,
  "optical_scene_id": null,
  "sar_scene_id": null
}
```
* **Response (200 OK)**:
```json
{
  "analysis_id": "AN-9A1F3C4B",
  "status": "queued",
  "current_stage": "queued",
  "progress_pct": 5,
  "error": null
}
```

#### `POST /api/v1/analyses/upload`
* **Purpose**: Dispatches an asynchronous analysis job using user-uploaded GeoTIFF, TIFF, PNG, or JPEG files.
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  - `mode`: `"single"` | `"fusion"` | `"temporal"`
  - `query`: Text query string
  - `image`: File binary (Single Image mode)
  - `before`: File binary (Before observation in temporal mode)
  - `after`: File binary (After observation in temporal mode)
  - `optical`: File binary (Optical observation in fusion mode)
  - `sar`: File binary (SAR observation in fusion mode)
* **Response (200 OK)**: Returns identical `AnalysisStatusResponse` with unique `analysis_id`.

#### `GET /api/v1/analyses/{analysis_id}/status`
* **Purpose**: Real-time polling endpoint to observe progress percentage and current processing stage.
* **Response (200 OK)**:
```json
{
  "analysis_id": "AN-9A1F3C4B",
  "status": "completed",
  "current_stage": "completed",
  "progress_pct": 100,
  "error": null
}
```
* Possible `current_stage` values:
  - `queued`
  - `validating`
  - `query_classification`
  - `retrieving_scene`
  - `model_inference`
  - `evidence_generation`
  - `confidence_calculation`
  - `report_generation`
  - `completed`
  - `failed`

#### `GET /api/v1/analyses/{analysis_id}`
* **Purpose**: Retrieves complete results, natural language answer, quantitative metrics, visual evidence links, and execution trace.
* **Response (200 OK)**:
```json
{
  "analysis_id": "AN-9A1F3C4B",
  "uid": "dev_user_earth_analyst_01",
  "query": "Describe the major land-cover types visible in this area.",
  "task": "Single-Image VQA",
  "input": "Single image",
  "date": "2026-09-17",
  "time": "15:23",
  "status": "Complete",
  "answer": "Predominantly built-up settlement. Spectral analysis of the scene reveals 15.2% agricultural and vegetated cover, 85.0% built-up and infrastructure footprint, 68.0% surface water bodies.",
  "confidence": "High",
  "confidence_score": 0.88,
  "confidence_basis": "Clear atmospheric conditions (7.57% cloud cover); Spectral index delineation matches target feature signature.",
  "agreements": [
    { "label": "Spectral Bands", "state": "agree" },
    { "label": "Spatial Extent", "state": "agree" },
    { "label": "Model Consensus", "state": "agree" }
  ],
  "observed_evidence": "Spectral bands analyzed: vegetation index 15.2%, water index 68.0%, high-frequency structural density 85.0%.",
  "model_interpretation": "Multi-band spectral decomposition supports land-cover distribution. Results calibrated against Sentinel-2 surface reflectance.",
  "model_used": "RemoteSensing Vision-Language Understanding Engine",
  "device_used": "CPU",
  "execution_trace": [
    { "name": "Input validation", "detail": "AOI bounds verified (42.18 km²)", "duration": "0.05s" },
    { "name": "Query classification", "detail": "Intent routed to Single-Image VQA", "duration": "0.01s" },
    { "name": "Scene retrieval", "detail": "Cached scene S2A_43QHV_20241223_0_L2A loaded", "duration": "0.12s" },
    { "name": "Model inference", "detail": "Spectral decomposition on CPU", "duration": "0.14s" },
    { "name": "Evidence generation", "detail": "Rendered grounding delineation mask", "duration": "0.08s" },
    { "name": "Report compilation", "detail": "PDF and JSON artifacts generated", "duration": "0.22s" }
  ],
  "boxes": [
    {
      "x": 35.2, "y": 42.1, "w": 28.4, "h": 22.0,
      "pixel_box": [360, 431, 290, 225],
      "geo_bbox": [78.461, 17.425, 78.489, 17.447],
      "confidence": 0.94,
      "class_name": "water_body"
    }
  ],
  "primary_image_path": "/static/evidence/raw_scene_AN-9A1F3C4B.png",
  "evidence_path": "/static/evidence/grounding_AN-9A1F3C4B.png",
  "created_at": "2026-09-17T15:23:10Z",
  "completed_at": "2026-09-17T15:23:12Z"
}
```

---

### 3.4 Reports & Downloads

#### `GET /api/v1/reports/{report_id}/download`
* **Purpose**: Downloads the publication-grade vector PDF report document generated by ReportLab.
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Response (200 OK)**:
  - `Content-Type`: `application/pdf`
  - `Content-Disposition`: `attachment; filename="SatyaDristi_Analysis_REP-9A1F3C4B_2026-09-17.pdf"`
  - Body: Binary PDF stream

#### `GET /api/v1/reports/{report_id}/json`
* **Purpose**: Downloads full structured audit JSON document for archival or automated pipeline ingestion.
* **Response (200 OK)**:
  - `Content-Type`: `application/json`
  - `Content-Disposition`: `attachment; filename="SatyaDristi_Analysis_REP-9A1F3C4B_2026-09-17.json"`

---

### 3.5 System & Hardware Telemetry

#### `GET /api/v1/system/health`
* **Purpose**: Non-invasive live hardware telemetry querying PyTorch CUDA and psutil.
* **Authentication**: None
* **Response (200 OK)**:
```json
{
  "status": "operational",
  "gpu_available": false,
  "gpu_name": "N/A",
  "vram_total_mb": 0.0,
  "vram_allocated_mb": 0.0,
  "vram_free_mb": 0.0,
  "cuda_version": "None",
  "preferred_device": "cpu",
  "cpu_usage_pct": 14.2,
  "ram_total_mb": 16384.0,
  "ram_available_mb": 6420.5,
  "active_jobs_count": 0,
  "models_status": {
    "vqa_engine": "online",
    "grounding_engine": "online",
    "bi_temporal_change_engine": "online",
    "optical_sar_fusion_engine": "online"
  },
  "providers": {
    "copernicus_data_space_stac": "online",
    "aws_earth_search_stac": "online",
    "esri_world_imagery": "online"
  },
  "database_status": "connected"
}
```

---

## 4. Planned / Missing APIs

The following endpoints are specified in prospective architecture documents or external service roadmaps but are **NOT implemented** in the current code:

| Endpoint | Method | Planned Functionality | Reason Not Implemented |
| :--- | :--- | :--- | :--- |
| `/api/v1/earth/isro/bhoonidhi/search` | `POST` | ISRO Cartosat / RISAT catalogue search | No public API or API key credentials available for Bhoonidhi. |
| `/api/v1/analyses/{id}/cancel` | `POST` | Cancel in-progress analysis job | Backend jobs run in fast in-process tasks ($\approx 1\text{s}$–$2\text{s}$); cancellation hook not wired. |
| `/api/v1/analyses/batch` | `POST` | Batch multi-scene queueing | UI only submits single, pair, or temporal jobs. |
| `/api/v1/auth/tokens/refresh` | `POST` | Explicit token rotation | Handled client-side directly by Firebase Web SDK. |
