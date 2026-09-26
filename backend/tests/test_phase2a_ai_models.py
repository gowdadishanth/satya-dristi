import os
import pytest
import numpy as np
from PIL import Image

from app.core.config import settings
from app.models.base_model import StructuredAIFindings
from app.models.router import model_router
from app.models.grounding_adapter import grounding_adapter
from app.models.vqa_adapter import vqa_adapter
from app.models.change_adapter import change_adapter
from app.models.optical_sar_adapter import optical_sar_adapter
from app.models.vqa_specialist import vqa_specialist
from app.models.grounding_specialist import grounding_specialist
from app.models.change_specialist import change_specialist
from app.models.optical_sar_specialist import optical_sar_specialist
from app.services.report_generator import report_generator

@pytest.fixture
def sample_rasters(tmp_path):
    """Creates temporary real RGB and SAR rasters for testing."""
    opt_path = tmp_path / "test_optical.png"
    before_path = tmp_path / "test_before.png"
    sar_path = tmp_path / "test_sar.png"

    # Create realistic test terrain image (256x256)
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:128, :, 1] = 160  # Green canopy
    arr[128:, :128, 0] = 180  # Built-up texture
    arr[128:, :128, 1] = 180
    arr[128:, :128, 2] = 180
    arr[128:, 128:, 2] = 190  # Water body
    arr[128:, 128:, 1] = 100
    Image.fromarray(arr).save(str(opt_path))

    # Create baseline image (slightly different for change detection)
    arr_b = arr.copy()
    arr_b[128:, :128, :] = [80, 140, 60]  # Was vegetation before, now built-up
    Image.fromarray(arr_b).save(str(before_path))

    # Create SAR grayscale image
    sar_arr = np.full((256, 256), 110, dtype=np.uint8)
    sar_arr[128:, :128] = 220  # High double bounce on urban
    sar_arr[128:, 128:] = 25   # Low specular backscatter on water
    Image.fromarray(sar_arr).save(str(sar_path))

    return {
        "optical": str(opt_path),
        "before": str(before_path),
        "sar": str(sar_path),
        "geo_bbox": [77.54, 13.00, 77.55, 13.01]
    }

def test_vqa_adapter_inference(sample_rasters):
    findings = vqa_adapter.analyze_raster(
        raster_path=sample_rasters["optical"],
        query="Describe the land cover and water bodies.",
        aoi_metadata={"bbox": sample_rasters["geo_bbox"]},
        analysis_id="TEST-VQA-01"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Single-Image VQA"
    assert len(findings.observations) >= 1
    assert len(findings.land_cover) >= 3
    assert findings.confidence_score >= 0.5
    assert os.path.exists(findings.evidence_path)

    # Verify backward-compatible specialist wrapper
    res = vqa_specialist.answer_query(
        image_path=sample_rasters["optical"],
        query="Describe land cover"
    )
    assert "answer" in res
    assert "confidence" in res
    assert "spectral_breakdown" in res

def test_grounding_adapter_inference(sample_rasters):
    findings = grounding_adapter.ground_raster(
        raster_path=sample_rasters["optical"],
        query="Highlight the water body",
        geo_bbox=sample_rasters["geo_bbox"],
        analysis_id="TEST-GROUND-01"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Grounding"
    assert os.path.exists(findings.evidence_path)
    assert findings.confidence_score >= 0.0

    # Verify specialist wrapper returns legacy box format
    res = grounding_specialist.ground_feature(
        image_path=sample_rasters["optical"],
        query="water body",
        geo_bbox=sample_rasters["geo_bbox"]
    )
    assert "boxes" in res
    assert "evidence_path" in res

def test_change_adapter_inference(sample_rasters):
    findings = change_adapter.analyze_change(
        before_raster_path=sample_rasters["before"],
        after_raster_path=sample_rasters["optical"],
        query="What changed between baseline and target?",
        geo_bbox=sample_rasters["geo_bbox"],
        analysis_id="TEST-CHANGE-01"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Bi-Temporal Change"
    assert os.path.exists(findings.evidence_path)
    assert "change_pct" in findings.raw_model_metrics

    # Verify specialist wrapper
    res = change_specialist.analyze_change(
        before_image_path=sample_rasters["before"],
        after_image_path=sample_rasters["optical"],
        query="What changed?",
        geo_bbox=sample_rasters["geo_bbox"]
    )
    assert "change_pct" in res
    assert "built_up_change_pct" in res
    assert "water_change_pct" in res

def test_optical_sar_adapter_inference(sample_rasters):
    findings = optical_sar_adapter.analyze_fusion(
        optical_raster_path=sample_rasters["optical"],
        sar_raster_path=sample_rasters["sar"],
        query="Assess surface moisture and urban structures.",
        analysis_id="TEST-SAR-01"
    )

    assert isinstance(findings, StructuredAIFindings)
    assert findings.task == "Optical-SAR Fusion"
    assert os.path.exists(findings.evidence_path)
    assert findings.confidence_score >= 0.70

    # Verify specialist wrapper
    res = optical_sar_specialist.fuse_and_analyze(
        optical_path=sample_rasters["optical"],
        sar_path=sample_rasters["sar"],
        query="Analyze multi-modal consensus"
    )
    assert "agreements" in res
    assert "fused_evidence_path" in res

def test_model_router_dispatch(sample_rasters):
    # 1. Route Grounding
    f_g = model_router.route_and_execute(
        task="Grounding",
        primary_image_path=sample_rasters["optical"],
        query="Where are the buildings?",
        aoi={"bbox": sample_rasters["geo_bbox"]},
        analysis_id="TEST-ROUTE-G"
    )
    assert f_g.task == "Grounding"

    # 2. Route Temporal Change
    f_c = model_router.route_and_execute(
        task="Bi-Temporal Change",
        primary_image_path=sample_rasters["optical"],
        before_image_path=sample_rasters["before"],
        query="What changed?",
        aoi={"bbox": sample_rasters["geo_bbox"]},
        analysis_id="TEST-ROUTE-C"
    )
    assert f_c.task == "Bi-Temporal Change"

    # 3. Route Optical SAR
    f_s = model_router.route_and_execute(
        task="Optical + SAR Fusion",
        primary_image_path=sample_rasters["optical"],
        sar_image_path=sample_rasters["sar"],
        query="Correlate radar backscatter",
        aoi={"bbox": sample_rasters["geo_bbox"]},
        analysis_id="TEST-ROUTE-S"
    )
    assert f_s.task == "Optical-SAR Fusion"

    # 4. Route Single Image VQA
    f_v = model_router.route_and_execute(
        task="Single-Image VQA",
        primary_image_path=sample_rasters["optical"],
        query="Describe the terrain",
        aoi={"bbox": sample_rasters["geo_bbox"]},
        analysis_id="TEST-ROUTE-V"
    )
    assert f_v.task == "Single-Image VQA"

def test_pdf_report_with_ai_findings(sample_rasters):
    analysis_dict = {
        "analysis_id": "AN-AI-REPORT-TEST",
        "task": "Single-Image VQA",
        "input": "Single image",
        "query": "Identify major terrain features and surface water bodies.",
        "answer": "Deep visual embeddings confirm predominant agricultural canopy with distinct open water reservoirs in the south-east quadrant.",
        "date": "2026-09-20",
        "time": "19:45",
        "confidence": "High",
        "confidence_score": 0.89,
        "model_used": "RemoteSensing Vision-Language Feature Reasoner",
        "device_used": "cpu",
        "primary_image_path": sample_rasters["optical"],
        "evidence_path": sample_rasters["optical"],
        "observations": [
            "Dominant canopy signature detected across 48.5% of visual extent.",
            "Water absorption boundary clearly delineated in south-east sector."
        ],
        "uncertainties": [
            "Minor cloud shadow at northern perimeter may affect local spectral contrast."
        ],
        "aoi": {
            "bbox": sample_rasters["geo_bbox"],
            "area_sq_km": 1.25
        },
        "execution_trace": [
            {"name": "Input validation", "detail": "CRS verified", "duration": "0.10s"},
            {"name": "AI Model Inference", "detail": "ResNet-ViT deep features extracted", "duration": "0.45s"},
            {"name": "Evidence generation", "detail": "Visual evidence map generated", "duration": "0.05s"}
        ]
    }

    report = report_generator.generate_report_artifacts(analysis_dict)
    assert report is not None
    pdf_path = report.get("pdf_path")
    assert pdf_path and os.path.exists(pdf_path)
    assert report_generator.is_valid_pdf_file(pdf_path)
    assert os.path.getsize(pdf_path) > 5000
