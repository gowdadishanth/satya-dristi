# Satya Dristi · Model & Specialist Tool Catalog

**Platform**: Satya Dristi · Multimodal Earth Observation Intelligence  
**Scope**: Complete inventory of remote-sensing models, specialist analytical engines, and heuristic inference tools implemented in the codebase.  
**Integrity Rule**: Factual reporting. Classical computer vision, spectral decomposition, and heuristic algorithms are described precisely as implemented and not misrepresented as deep-learning neural network checkpoints.

---

## 1. Catalog Summary

| Engine / Specialist | File Location | Task | Method Category | Primary Modality | Target Device | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **VQASpecialist** | `backend/app/models/vqa_specialist.py` | Single-Image VQA | Spectral-spatial decomposition + Rule-based synthesis | Optical Multispectral | CPU / CUDA | **IMPLEMENTED** (Spectral-Spatial CV) |
| **GroundingSpecialist** | `backend/app/models/grounding_specialist.py` | Feature Localization | Spectral indexing + Morphological contour extraction | Optical Multispectral | CPU / CUDA | **IMPLEMENTED** (Spectral-Spatial CV) |
| **ChangeSpecialist** | `backend/app/models/change_specialist.py` | Bi-Temporal Change | Change Vector Analysis (CVA) + Structural difference | Bi-Temporal Optical | CPU / CUDA | **IMPLEMENTED** (Radiometric & Structural CV) |
| **OpticalSARSpecialist**| `backend/app/models/optical_sar_specialist.py`| Multimodal Fusion | Radiometric cross-modal thresholding & dielectric agreement | Optical + C-band SAR | CPU / CUDA | **IMPLEMENTED** (Cross-Modal Correlation) |
| **TaskRouter** | `backend/app/services/task_router.py` | Intent Routing | Lexical & keyword semantic intent classifier | Natural Language Text | CPU | **IMPLEMENTED** (Deterministic Rule Engine) |
| **ConfidenceEngine** | `backend/app/services/confidence_engine.py`| Confidence Estimation| Multi-signal composite heuristic | Telemetry Signals | CPU | **IMPLEMENTED** (Heuristic Scoring) |
| **ModelResourceManager**| `backend/app/models/resource_manager.py` | Resource Management | PyTorch CUDA telemetry & memory-aware device assignment | Hardware Telemetry | CPU / GPU | **IMPLEMENTED** (System Manager) |

---

## 2. Detailed Model Specifications

### 2.1 VQASpecialist (Visual Question Answering)
* **Identifier**: `RemoteSensing Vision-Language Understanding Engine`
* **Implementation**: `backend/app/models/vqa_specialist.py`
* **Primary Task**: Single-Image Remote Sensing VQA & Land-Cover Scene Characterization
* **Modality**: Optical Multispectral (Sentinel-2 L2A BOA / RGB representation)
* **Input**: 
  - Satellite image file path (`.png` / `.tif`)
  - Natural-language user query string
  - Optional AOI bounding metadata
* **Output**:
  - Structured natural-language answer grounded in observation
  - Quantitative spectral breakdown:
    - Vegetation cover percentage (`veg_pct`)
    - Built-up footprint percentage (`urban_pct`)
    - Surface water percentage (`water_pct`)
    - Barren / fallow ground percentage (`barren_pct`)
  - Observed evidence summary string
  - Model interpretation methodology summary
* **Methodology & Inference**:
  - Quantitative per-pixel spectral inspection across red, green, and blue bands.
  - Visible Atmospherically Resistant Index proxy: $\text{VI} = \frac{\text{Green} - \text{Red}}{\text{Green} + \text{Red} + \epsilon}$.
  - Water absorption heuristic based on green-to-red ratio and low mean luminance ($<120$ DN).
  - High-frequency built-up edge extraction via OpenCV Canny detector ($60, 150$ thresholds) normalized to surface density.
  - Directional quadrant spatial indexing (NW, NE, SW, SE) to pinpoint spatial location of detected features.
  - Dynamic rule-based linguistic template rendering matching query intent.
* **Fine-Tuning / Checkpoints**: None. Uses direct algorithmic spectral decomposition rather than a pretrained Vision-Language Transformer checkpoint.
* **Target Hardware**: CPU (Execution latency $\approx 0.05\text{s}$–$0.15\text{s}$).
* **Limitations**:
  - Answers are constrained to spectral indices and spatial edge density.
  - Highly complex abstract visual queries outside land-cover, water, and urban taxonomy receive generalized spectral summaries.

---

### 2.2 GroundingSpecialist (Spatial Localization)
* **Identifier**: `RemoteSensing Grounding Engine (Spectral-Spatial Localization)`
* **Implementation**: `backend/app/models/grounding_specialist.py`
* **Primary Task**: Natural-Language Grounding & Bounding Box Delineation
* **Modality**: Optical Multispectral (Sentinel-2 L2A / RGB representation)
* **Input**:
  - Image file path
  - Target query string
  - Geographic bounding box `[min_lon, min_lat, max_lon, max_lat]`
* **Output**:
  - List of detected bounding boxes with:
    - Normalized canvas coordinates (`x, y, w, h` in $0..100\%$ scale)
    - Image pixel coordinates (`[bx, by, bw, bh]`)
    - Geographic coordinates (`geo_bbox: [lon_min, lat_min, lon_max, lat_max]`)
    - Detection confidence score ($0.58$–$0.98$)
    - Class name (`water_body`, `built_up`, `vegetation`, or `salient_feature`)
  - Binary/contour evidence mask image saved to `data/evidence/`
* **Methodology & Inference**:
  - Query keyword parsing to extract target semantic class (`water`, `built-up`, `vegetation`).
  - Class-specific spectral thresholding:
    - Water: Normalized difference green-red index $> 0.02$ and brightness $< 160$.
    - Built-up: High luminance ($>130$) and inter-band variance $< 25$.
    - Vegetation: Green dominance ratio $> 0.05$.
  - Morphological noise cleaning via OpenCV `cv2.morphologyEx` using rectangular structural elements ($5\times 5$ kernel).
  - External contour extraction (`cv2.findContours`) and bounding rectangle generation.
  - Coordinate re-projection from image pixel space to geographic WGS84 coordinates using affine interpolation across `geo_bbox`.
* **Fine-Tuning / Checkpoints**: None. Uses algorithmic computer vision and spectral segmentation.
* **Target Hardware**: CPU (Execution latency $\approx 0.08\text{s}$–$0.25\text{s}$).
* **Limitations**:
  - Small objects below the $10\text{m}$ Sentinel-2 pixel resolution cannot be individually delineated.
  - Does not use an attention-based open-vocabulary grounding network (e.g. Grounding DINO).

---

### 2.3 ChangeSpecialist (Bi-Temporal Change Detection)
* **Identifier**: `Bi-Temporal Siamese Spectral-Structural Change Detector`
* **Implementation**: `backend/app/models/change_specialist.py`
* **Primary Task**: Bi-Temporal Surface Change Detection and Classification
* **Modality**: Multi-temporal Optical (Sentinel-2 Pair)
* **Input**:
  - Baseline (Before) image path
  - Target (After) image path
  - Query string
  - Optional geographic bounding box
* **Output**:
  - Natural-language change summary
  - Total change percentage (`change_pct`)
  - Built-up gain percentage (`built_up_change_pct`)
  - Water extent variation percentage (`water_change_pct`)
  - RGBA change overlay mask saved to `data/evidence/change_map_*.png`
  - Confidence rating (`High` or `Moderate`)
* **Methodology & Inference**:
  - Spatial dimension verification and bilinear interpolation alignment.
  - Pixel-wise Change Vector Analysis (CVA) across spectral bands: $\Delta M = \sqrt{\sum_{c} (I_{\text{after}, c} - I_{\text{before}, c})^2}$.
  - Structural difference computation via OpenCV absolute grayscale difference: $|I_{\text{gray, after}} - I_{\text{gray, before}}|$.
  - Adaptive 82nd percentile thresholding applied to change magnitude vector.
  - Directional brightness differential analysis:
    - New built-up footprint: Active change + brightness gain $> +20$ DN.
    - New water accumulation: Active change + brightness drop $< -25$ DN + green/red absorption.
  - Color-coded RGBA evidence map generation:
    - Gold/Amber (`#AB7C2C`, alpha 180): Built-up expansion.
    - Slate Blue (`#4F6F8A`, alpha 200): Water body extent shift.
    - Neutral Silver (`#C2CBD3`, alpha 120): General surface variation.
* **Fine-Tuning / Checkpoints**: None. Classical Change Vector Analysis (CVA) combined with structural differential computer vision.
* **Target Hardware**: CPU (Execution latency $\approx 0.15\text{s}$–$0.35\text{s}$).
* **Limitations**:
  - Sensitive to severe seasonal lighting differentials and residual cloud shadows.
  - Does not execute a learned deep Siamese transformer (e.g., ChangeFormer / BIT).

---

### 2.4 OpticalSARSpecialist (Multimodal Radiometric Fusion)
* **Identifier**: `Optical-SAR Cross-Modal Radiometric Fusion Engine`
* **Implementation**: `backend/app/models/optical_sar_specialist.py`
* **Primary Task**: Multimodal Joint Spectral-Dielectric Analysis
* **Modality**: Optical (Sentinel-2 L2A) + Synthetic Aperture Radar (Sentinel-1 C-SAR GRD)
* **Input**:
  - Optical image path
  - SAR image path
  - Query string
* **Output**:
  - Multimodal natural language answer
  - Cross-modal agreement indicators (`Optical Spectral`, `SAR Backscatter`, `Multimodal Fusion`)
  - Confirmed urban percentage (where high optical texture AND SAR double bounce agree)
  - Confirmed water percentage (where optical absorption AND SAR specular reflection agree)
  - Color-coded fused evidence image saved to `data/evidence/fused_*.png`
* **Methodology & Inference**:
  - Spatial resolution alignment via bilinear resampling.
  - Optical classification: Luminance and variance thresholding.
  - SAR radiometric analysis:
    - Double-bounce corner reflection (urban/structural): Calibrated backscatter $> 165$ DN.
    - Specular reflection (calm water surface): Radar backscatter $< 60$ DN.
  - Cross-modal boolean intersection:
    - $\text{Confirmed Urban} = \text{Optical Urban} \land \text{SAR Double Bounce}$
    - $\text{Confirmed Water} = \text{Optical Water} \land \text{SAR Specular Reflection}$
  - Fused visual overlay synthesis highlighting cross-modal consensus regions in gold (urban) and deep azure (water).
* **Fine-Tuning / Checkpoints**: None. Classical radiometric thresholding and boolean correlation.
* **Target Hardware**: CPU (Execution latency $\approx 0.10\text{s}$–$0.25\text{s}$).
* **Limitations**:
  - Assumes pre-processed co-registered SAR imagery. Extreme radar speckle or steep terrain shadow requires external terrain correction (RTC).

---

### 2.5 TaskRouter (Agentic Intent Classifier)
* **Identifier**: `Deterministic Rule-Based Task Router`
* **Implementation**: `backend/app/services/task_router.py`
* **Primary Task**: Natural Language Query Classification and Specialist Model Dispatch
* **Modality**: Natural Language Text
* **Input**: Query string, analysis mode, presence of temporal/fusion pairs
* **Output**: `(task_name, model_pipeline, task_code)`
* **Methodology**: Deterministic rule-based keyword pattern matching covering 9 supported task categories:
  - `Single-Image VQA`
  - `Scene Description`
  - `Grounding`
  - `Bi-Temporal Change`
  - `Optical + SAR Fusion`
  - `Segmentation`
  - `Classification`
  - `Unsupported Request`
  - `Needs Clarification`
* **Limitations**: Does not use an LLM for agentic reasoning; complex queries with implicit multi-hop goals fall back to single-image VQA or change detection depending on mode.

---

### 2.6 ConfidenceEngine
* **Identifier**: `Multi-Signal Calibrated Confidence Estimator`
* **Implementation**: `backend/app/services/confidence_engine.py`
* **Primary Task**: Multi-Factor Confidence Rating and Agreement Telemetry
* **Input**: Task type, telemetry dictionary (`cloud_cover`, `overlap_pct`, `change_pct`, `optical_agree`, `sar_agree`, `activation_strength`)
* **Output**:
  - Level: `High` ($\ge 0.80$), `Moderate` ($0.60$–$0.79$), or `Low` ($< 0.60$)
  - Bounded score ($0.35$ to $0.96$)
  - Dimension-specific agreements list (`agree` or `partial`)
  - Descriptive basis rationale string
  - List of operational warnings
* **Methodology**: Heuristic scoring engine. Adjusts baseline score ($0.70$) based on empirical remote sensing degradation factors (cloud penalty, spatial overlap ratio, cross-modal agreement).
* **Limitations**: Calibrated heuristically rather than via Bayesian deep ensemble posterior probabilities.

---

### 2.7 ModelResourceManager
* **Identifier**: `Hardware-Aware Model Resource Manager`
* **Implementation**: `backend/app/models/resource_manager.py`
* **Primary Task**: Device Assignment, Memory Management, and Hardware Telemetry
* **Input**: Real system states queried via `psutil` and `torch.cuda`
* **Output**: Hardware status dictionary (GPU availability, device name, VRAM total/allocated/free, CPU usage %, RAM available)
* **Methodology**: Checks CUDA device properties and available free VRAM ($>600\text{MB}$ threshold) to assign tasks to `cuda:0` or fall back to `cpu`. Provides model registration and explicit memory eviction with garbage collection.
