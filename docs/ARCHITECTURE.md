# Satya Dristi · System Architecture Document

**System Name**: Satya Dristi  
**Descriptor**: Multimodal Earth Observation Intelligence  
**Architecture Classification**: Client-Server Geospatial Intelligence Platform (SPA + Asynchronous REST Backend)  
**Target Operating Environment**: Local Dev / On-Premise GPU Workstation / Cloud VM (Docker-Ready)

---

## 1. System Overview

Satya Dristi integrates public satellite Earth observation data streams (Sentinel-2 MSI Optical and Sentinel-1 SAR GRD) with remote-sensing analysis engines, multi-layer visual evidence rendering, and auditable publication reporting.

```mermaid
graph TB
    subgraph Client ["Frontend Single Page App (React 19 + Vite + Leaflet)"]
        UI[User Interface · Shell & Pages]
        Map[Global Earth Observation Explorer]
        Controls[Left Control Panel · Modes & Queries]
        EvidenceView[Visual Evidence Canvas & Overlays]
        TraceView[Observable Execution Trace & Pipeline]
    end

    subgraph API ["FastAPI Service Layer (Python 3.11)"]
        RouterAuth["/api/v1/auth"]
        RouterEarth["/api/v1/earth"]
        RouterAnalyses["/api/v1/analyses"]
        RouterHistory["/api/v1/history"]
        RouterReports["/api/v1/reports"]
        RouterSystem["/api/v1/system"]
        AsyncQueue[Asynchronous Job Manager]
    end

    subgraph Geo ["Geospatial & Ingestion Infrastructure"]
        STACService[STAC Service Client]
        GeoProcessor[Shapely / PyProj Engine]
        ImageRetrieval[Image Retrieval & AOI Clipper]
    end

    subgraph AI ["Specialist Model & Inference Registry"]
        TaskRouter[Deterministic Intent Router]
        VQASpec[VQA Specialist · Spectral Decomp]
        GroundSpec[Grounding Specialist · Contour Localization]
        ChangeSpec[Change Specialist · CVA & Structural]
        FusionSpec[Optical-SAR Specialist · Radiometric Fusion]
        ConfEngine[Confidence Engine]
        ResManager[Hardware Resource Manager · PyTorch CUDA]
    end

    subgraph Storage ["Persistence & Storage Layer"]
        Firestore[Google Cloud Firestore / SQLite Local Store]
        ReportLab[ReportLab PDF Engine]
        DiskEvidence["data/evidence/*.png"]
        DiskReports["data/reports/*.pdf, *.json"]
        DiskCache["data/cache/*"]
    end

    subgraph Providers ["External Data Providers"]
        AWSEarth[AWS Earth Search STAC]
        Copernicus[Copernicus Data Space STAC]
        Esri[Esri World Imagery Basemap]
        OSM[OpenStreetMap Nominatim]
    end

    UI --> RouterAuth
    UI --> RouterEarth
    UI --> RouterAnalyses
    UI --> RouterHistory
    UI --> RouterReports
    UI --> RouterSystem

    RouterEarth --> STACService
    RouterEarth --> GeoProcessor
    STACService --> AWSEarth
    STACService --> Copernicus
    Map --> Esri
    Map --> OSM

    RouterAnalyses --> AsyncQueue
    AsyncQueue --> TaskRouter
    AsyncQueue --> ImageRetrieval
    ImageRetrieval --> DiskCache

    TaskRouter --> VQASpec
    TaskRouter --> GroundSpec
    TaskRouter --> ChangeSpec
    TaskRouter --> FusionSpec

    VQASpec --> ConfEngine
    GroundSpec --> ConfEngine
    ChangeSpec --> ConfEngine
    FusionSpec --> ConfEngine

    AsyncQueue --> DiskEvidence
    AsyncQueue --> Firestore
    RouterReports --> ReportLab
    ReportLab --> DiskReports
    Firestore -.-> RouterHistory
```

---

## 2. Component Architecture

### 2.1 Frontend Subsystem (`src/`)
* **Technology**: React 19, TypeScript 5.7, Vite 8, Tailwind CSS v4, Leaflet 1.9.4.
* **Component Hierarchy**:
  - `src/App.tsx`: Global route router and theme provider wrapper.
  - `src/components/Shell.tsx`: Navigation sidebar, header with live hardware telemetry pill, and user profile badge.
  - `src/pages/Analyze.tsx`: Core analytical workspace using a disciplined 3-column desktop layout:
    - **Left Column (~300px)**: Control panel (Input source, Analysis mode, Selected scene compact card, Question textarea, Example chips, Run Analysis primary action).
    - **Center Column (~700–800px)**: Global Earth Observation Explorer (Map context bar, 2-row uncramped search/filters, 460px Leaflet satellite map, GIS toolbar, available scene result cards *below* the map; transitions to Visual Evidence Viewer and Answer Panel upon completion).
    - **Right Column (~280px)**: Supporting Analysis Pipeline (compact 18px numbered circles, confidence rating, collapsible execution trace, and official PDF report download).
  - `src/components/GlobalMap.tsx`: Interactive Leaflet map, geocoding search, year/cloud filters, AOI drag-to-draw rectangle, and STAC scene catalogue renderer.
  - `src/components/SatImage.tsx`: High-resolution canvas rendering with interactive layer toggles (Optical, SAR, Change detection, Grounding bounding boxes, Grid reference), opacity controls, and temporal swipe/side-by-side comparison.
  - `src/components/Uploader.tsx`: Drag-and-drop file uploader for manual satellite imagery (GeoTIFF/PNG/JPEG).
  - `src/lib/api.ts`: Centralized HTTP client communicating with `/api/v1` endpoints with bearer token injection and error handling.
  - `src/lib/firebase.ts`: Authentication service managing analyst session, Google Sign-In state, and local storage tokens.

### 2.2 Backend Subsystem (`backend/app/`)
* **Technology**: FastAPI 0.115, Uvicorn, Pydantic 2.8, Python 3.11.
* **Service Layer**:
  - `stac_service.py`: Queries AWS Earth Search and Copernicus Data Space STAC APIs. Normalizes raw features into consistent `SceneResponse` schemas with verified preview URLs.
  - `geospatial_processor.py`: Uses Shapely and PyProj to validate geometries, compute geodesic areas in EPSG:6933, verify scene footprint overlaps, and evaluate cross-scene spatial compatibility.
  - `image_retrieval.py`: Downloads preview imagery, clips raster arrays to exact AOI coordinates using normalized bbox ratios, applies radar logarithmic dB transforms for SAR, and caches assets locally.
  - `async_queue.py`: Background task executor managing analysis job states (`queued` → `validating` → `query_classification` → `retrieving_scene` → `model_inference` → `evidence_generation` → `confidence_calculation` → `report_generation` → `completed`), capturing observable step timings in execution traces.
  - `report_generator.py`: ReportLab Platypus engine generating vector PDF reports and structured JSON exports embedding scene coordinates, spectral findings, and satellite imagery.
  - `db.py`: Dual-mode storage engine connecting to Google Cloud Firestore or falling back to a thread-safe SQLite document database (`data/satya_dristi_store.db`).
  - `firebase.py`: Verifies Firebase JWT ID tokens via `firebase-admin` or decodes developer session tokens in development mode.

---

## 3. Comprehensive Sequence Flows

### 3.1 Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as User / Analyst
    participant Client as Frontend (firebase.ts)
    participant API as FastAPI (/api/v1/auth/me)
    participant FB as Firebase Admin / Local DB

    Analyst->>Client: Click "Sign in with Google" or Launch App
    Client->>Client: Load or generate session token (dev-token-<uid>)
    Client->>API: GET /api/v1/auth/me (Authorization: Bearer <TOKEN>)
    API->>FB: Verify token with Firebase Admin SDK
    alt In Development Mode & dev-token
        FB-->>API: Decode local analyst claims (uid, name, email)
    else Live Firebase Token
        FB-->>API: Verify RSA signature against Google public certs
    end
    API->>FB: Save / update user in Firestore or SQLite
    API-->>Client: 200 OK (UserProfile JSON)
    Client-->>Analyst: Authenticated state rendered in UI Shell
```

---

### 3.2 Satellite Discovery & AOI Flow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Analyst
    participant UI as GlobalMap.tsx
    participant API as /api/v1/earth
    participant STAC as STAC Service
    participant Geo as Geospatial Processor
    participant Ext as AWS & Copernicus STAC

    Analyst->>UI: Enter Place Name "Hyderabad" & Year "2024"
    UI->>UI: Geocode place via Nominatim → Lat: 17.424, Lon: 78.474
    Analyst->>UI: Drag mouse on map to define Area of Interest
    UI->>API: POST /api/v1/earth/aoi/preview { bbox: [...] }
    API->>Geo: Validate bounds & project to EPSG:6933
    Geo-->>API: Area: 88.7 km², Centroid: [78.47, 17.42]
    API-->>UI: 200 OK (AOIPreview)
    UI-->>Analyst: Render telemetry pill & gold bounding box on map

    Analyst->>UI: Click "Search Satellite Scenes"
    UI->>API: POST /api/v1/earth/scenes/search { bbox, year: 2024, sensor: "optical" }
    API->>STAC: Execute search with temporal & cloud filters
    STAC->>Ext: Query Earth Search STAC API
    Ext-->>STAC: Return STAC GeoJSON features
    STAC->>STAC: Normalize assets & preview URLs
    STAC-->>API: List[SceneResponse]
    API-->>UI: 200 OK
    UI-->>Analyst: Display readable Scene Result Cards beneath map
```

---

### 3.3 Analysis Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Analyst
    participant UI as Analyze.tsx
    participant API as /api/v1/analyses
    participant Queue as Async Job Manager
    participant Router as Task Router
    participant Retrieval as Image Retrieval
    participant Specialist as Specialist Models
    participant Evidence as Evidence & Confidence
    participant DB as Firestore / SQLite

    Analyst->>UI: Select Scene + Enter Question + Click "Run Analysis"
    UI->>API: POST /api/v1/analyses { mode, query, scene_id, aoi }
    API->>Queue: Generate analysis_id & start background asyncio task
    API-->>UI: 200 OK { analysis_id, status: "queued" }

    loop Poll Status Every 600ms
        UI->>API: GET /api/v1/analyses/{id}/status
        API-->>UI: { status, current_stage, progress_pct }
    end

    Queue->>Queue: Stage: "validating" (Verify AOI & CRS)
    Queue->>Router: Stage: "query_classification" (Route intent)
    Router-->>Queue: Task: "Single-Image VQA" / Specialist: VQASpecialist
    Queue->>Retrieval: Stage: "retrieving_scene" (Download & clip to AOI)
    Retrieval-->>Queue: Cached cropped raster (data/cache/*.png)
    Queue->>Specialist: Stage: "model_inference" (Execute spectral analysis)
    Specialist-->>Queue: Answer text, land-cover percentages
    Queue->>Evidence: Stage: "evidence_generation" (Generate masks/boxes)
    Evidence-->>Queue: Grounding boxes & PNG masks
    Queue->>Evidence: Stage: "confidence_calculation" (Compute multi-signal score)
    Evidence-->>Queue: Confidence: "High" (0.88)
    Queue->>DB: Save complete AnalysisRecord to database
    Queue->>Queue: Mark job "completed" (progress: 100%)

    UI->>API: GET /api/v1/analyses/{id}
    API-->>UI: 200 OK (Full AnalysisRecord JSON)
    UI-->>Analyst: Render Visual Evidence, Grounding Boxes, Answer, Trace
```

---

### 3.4 Bi-Temporal Change Detection Flow

```mermaid
sequenceDiagram
    autonumber
    participant UI as Analyze.tsx (Before + After Mode)
    participant Queue as Async Queue
    participant Geo as Geospatial Processor
    participant Change as ChangeSpecialist
    participant Disk as data/evidence/

    UI->>Queue: Submit Baseline Scene (2022) + Target Scene (2024)
    Queue->>Geo: Check scenes spatial overlap & CRS alignment
    Geo-->>Queue: Overlap: 94.2% (Compatible)
    Queue->>Change: analyze_change(before_path, after_path, query)
    Change->>Change: Resample images to identical dimensions
    Change->>Change: Compute Change Vector Analysis (CVA) magnitude
    Change->>Change: Compute grayscale structural difference (OpenCV absdiff)
    Change->>Change: Adaptive 82nd percentile thresholding
    Change->>Change: Categorize: Built-up expansion vs Water extent shift
    Change->>Disk: Save RGBA colored change map (change_map_*.png)
    Change-->>Queue: change_pct: 12.4%, built_pct: 4.8%, water_pct: 2.1%
    Queue-->>UI: Render Swipe / Side-by-side viewer with change overlay
```

---

### 3.5 Optical + SAR Cross-Modal Fusion Flow

```mermaid
sequenceDiagram
    autonumber
    participant UI as Analyze.tsx (Optical + SAR Mode)
    participant Queue as Async Queue
    participant Fusion as OpticalSARSpecialist
    participant Disk as data/evidence/

    UI->>Queue: Submit Sentinel-2 Optical + Sentinel-1 SAR Pair
    Queue->>Fusion: fuse_and_analyze(optical_path, sar_path, query)
    Fusion->>Fusion: Resample SAR grid to optical dimensions
    Fusion->>Fusion: Optical: Extract vegetation & urban brightness/variance
    Fusion->>Fusion: SAR: Logarithmic dB calibration
    Fusion->>Fusion: SAR: Detect double bounce (>165 DN) & specular (<60 DN)
    Fusion->>Fusion: Boolean Cross-Agreement (Optical Urban ∧ SAR Double Bounce)
    Fusion->>Fusion: Boolean Cross-Agreement (Optical Water ∧ SAR Specular)
    Fusion->>Disk: Generate fused highlight overlay (fused_*.png)
    Fusion-->>Queue: Confirmed urban %, water %, agreement indicators
    Queue-->>UI: Render dual-modality layers with verified agreement
```

---

### 3.6 Report Generation & Download Flow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Analyst
    participant UI as Reports.tsx / Analyze.tsx
    participant API as /api/v1/reports/{id}/download
    participant Gen as ReportGeneratorService
    participant Disk as data/reports/

    Analyst->>UI: Click "Download PDF"
    UI->>API: GET /api/v1/reports/{analysis_id}/download
    API->>Gen: generate_report_artifacts(analysis_record)
    Gen->>Gen: Build ReportLab Platypus document (Title, Styles, Tables)
    Gen->>Gen: Embed observed evidence, model interpretation, execution trace
    Gen->>Gen: Embed satellite and evidence PNG images
    Gen->>Disk: Write SatyaDristi_Analysis_REP-*.pdf
    Gen->>Disk: Write SatyaDristi_Analysis_REP-*.json
    API-->>UI: FileResponse (Content-Type: application/pdf, Content-Disposition: attachment)
    UI-->>Analyst: Browser downloads vector PDF report
```

---

## 4. Data Schema & Entity Relationships

The data model is structured around users, remote-sensing observations, analysis jobs, visual evidence, and generated reports:

```mermaid
erDiagram
    USER ||--o{ ANALYSIS : submits
    USER ||--o{ REPORT : owns
    SCENE ||--o{ ANALYSIS : referenced_in
    AOI ||--|| ANALYSIS : defines_bounds
    ANALYSIS ||--o{ EVIDENCE_OVERLAY : generates
    ANALYSIS ||--|| EXECUTION_TRACE : logs
    ANALYSIS ||--o{ CONFIDENCE_AGREEMENT : computes
    ANALYSIS ||--|| REPORT : exported_as

    USER {
        string uid PK
        string email
        string name
        string picture
        boolean is_dev
        timestamp created_at
    }

    SCENE {
        string scene_id PK
        string collection
        string provider
        string platform
        string sensor
        timestamp acquisition_datetime
        float cloud_cover
        float_array bbox
        string preview_url
    }

    AOI {
        float_array bbox
        float_array centroid
        float area_sq_km
        geojson geometry
    }

    ANALYSIS {
        string analysis_id PK
        string uid FK
        string mode
        string query
        string task
        string status
        string answer
        string confidence
        float confidence_score
        string confidence_basis
        string observed_evidence
        string model_interpretation
        string model_used
        string device_used
        string primary_image_path
        string evidence_path
        timestamp created_at
        timestamp completed_at
    }

    EVIDENCE_OVERLAY {
        string overlay_id PK
        string file_path
        string format
        string classification_type
        float opacity_default
    }

    EXECUTION_TRACE {
        string step_name
        string detail
        string duration
        string status
    }

    CONFIDENCE_AGREEMENT {
        string label
        string state
    }

    REPORT {
        string report_id PK
        string analysis_id FK
        string uid FK
        string pdf_path
        string json_path
        string pdf_filename
        timestamp generated_at
    }
```

---

## 5. Security Architecture

### 5.1 Authentication and Identity Verification
* **Production**: The application verifies cryptographically signed JWT ID tokens issued by Firebase Authentication using the Google public keys through `firebase_admin.auth.verify_id_token`.
* **Development Isolation**: When `ENVIRONMENT="development"`, local development tokens (`dev-token-<uid>`) bypass RSA signature checks to allow offline developer testing and evaluation without active GCP credentials.
* **User Data Scoping**: All database queries for analyses and reports filter on the verified `uid`, preventing unauthorized cross-user data access.

### 5.2 File and Upload Security
* **Filename Sanitization**: Uploaded files are cleaned using `pathlib.Path(filename).name` to prevent directory traversal (`../`) attacks.
* **Size Limits**: Form data uploads enforce a 100MB ceiling.
* **Storage Segregation**: User uploads are segregated in `data/uploads/`, system cache in `data/cache/`, generated evidence in `data/evidence/`, and reports in `data/reports/`.
* **GeoJSON Bounds Checks**: All user AOI inputs are strictly validated against WGS84 range limits ($[-180, 180]$ longitude, $[-90, 90]$ latitude).

---

## 6. Deployment & Hardware Execution

```mermaid
graph LR
    subgraph Host ["Host Workstation / Cloud VM"]
        subgraph FrontendServer ["Frontend (Port 8443)"]
            ViteDev["Vite 8 Dev / Static Preview Server"]
        end

        subgraph BackendServer ["Backend (Port 8000)"]
            Uvicorn["Uvicorn ASGI Server"]
            FastAPI["FastAPI 0.115 Application"]
        end

        subgraph Hardware ["Hardware Layer"]
            CPU["Multi-Core Host CPU (psutil)"]
            RAM["Host System RAM"]
            GPU["NVIDIA GPU (GTX 1650 / CUDA) [Optional]"]
        end

        subgraph StorageDir ["Local Persistent Directory (data/)"]
            DBFile["satya_dristi_store.db (SQLite)"]
            EvidenceDir["data/evidence/"]
            ReportsDir["data/reports/"]
            CacheDir["data/cache/"]
        end
    end

    ViteDev -- "Reverse Proxy /api/v1" --> Uvicorn
    Uvicorn --> FastAPI
    FastAPI --> Hardware
    FastAPI --> StorageDir
```

* **Frontend Port**: `8443` (Vite dev server with `/api/v1` and `/static` reverse proxy).
* **Backend Port**: `8000` (Uvicorn ASGI server).
* **Hardware Adaptation**: Automatically detects NVIDIA CUDA via PyTorch. If CUDA VRAM is $\ge 600\text{MB}$, operations are hardware-accelerated on `cuda:0`; otherwise, operations execute on CPU without throwing errors.
