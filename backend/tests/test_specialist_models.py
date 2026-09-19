import os
import pytest
import numpy as np
from PIL import Image

from app.models.grounding_specialist import grounding_specialist
from app.models.change_specialist import change_specialist
from app.models.optical_sar_specialist import optical_sar_specialist
from app.models.vqa_specialist import vqa_specialist
from app.core.config import settings

@pytest.fixture
def sample_test_images(tmp_path):
    img1_path = tmp_path / "scene1.png"
    img2_path = tmp_path / "scene2.png"
    sar_path = tmp_path / "sar.png"

    # Create synthetic remote sensing image with water and vegetation
    arr1 = np.full((128, 128, 3), [60, 110, 40], dtype=np.uint8) # green vegetation
    arr1[40:80, 40:80] = [30, 70, 130] # central water reservoir
    Image.fromarray(arr1).save(img1_path)

    # Second temporal image with urban growth in south
    arr2 = arr1.copy()
    arr2[90:120, 20:80] = [180, 180, 175] # new built-up area
    Image.fromarray(arr2).save(img2_path)

    # SAR image with double bounce in urban and dark water
    sar_arr = np.full((128, 128), 100, dtype=np.uint8)
    sar_arr[40:80, 40:80] = 35 # low radar backscatter for water
    sar_arr[90:120, 20:80] = 210 # high radar backscatter for urban
    Image.fromarray(sar_arr).save(sar_path)

    return str(img1_path), str(img2_path), str(sar_path)

def test_grounding_specialist(sample_test_images):
    img1, _, _ = sample_test_images
    res = grounding_specialist.ground_feature(
        image_path=img1,
        query="Highlight the water body",
        geo_bbox=[78.4, 17.3, 78.5, 17.4]
    )
    assert res["task"] == "Grounding"
    assert res["target"] == "water_body"
    assert len(res["boxes"]) > 0
    box = res["primary_box"]
    assert "x" in box and "y" in box and "w" in box and "h" in box
    assert "geo_bbox" in box
    assert res["confidence"] > 0.5
    assert os.path.exists(res["mask_path"])

def test_change_specialist(sample_test_images):
    img1, img2, _ = sample_test_images
    res = change_specialist.analyze_change(
        before_image_path=img1,
        after_image_path=img2,
        query="What changed between these two dates?"
    )
    assert res["task"] == "Bi-Temporal Change"
    assert res["change_pct"] > 0
    assert "built-up expansion" in res["answer"].lower() or "change" in res["answer"].lower()
    assert os.path.exists(res["evidence_image_path"])

def test_optical_sar_specialist(sample_test_images):
    img1, img2, sar = sample_test_images
    # 1. Partial agreement pair (optical natural water with SAR radar urban response)
    res = optical_sar_specialist.fuse_and_analyze(
        optical_path=img1,
        sar_path=sar,
        query="Use optical and SAR together to identify water and built-up"
    )
    assert res["task"] == "Optical + SAR Fusion"
    assert res["confidence"] in ["Moderate", "High"]
    assert len(res["agreements"]) == 3
    assert os.path.exists(res["fused_evidence_path"])

    # 2. Complete agreement pair (both optical and SAR feature both water and urban)
    res2 = optical_sar_specialist.fuse_and_analyze(
        optical_path=img2,
        sar_path=sar,
        query="Use optical and SAR together to identify water and built-up"
    )
    assert res2["confidence"] == "High"
    assert res2["agreements"][2]["state"] == "agree"

def test_vqa_specialist(sample_test_images):
    img1, _, _ = sample_test_images
    res = vqa_specialist.answer_query(
        image_path=img1,
        query="Describe the major land-cover types visible in this image."
    )
    assert res["task"] == "Single-Image VQA"
    assert len(res["answer"]) > 20
    assert "vegetation_pct" in res["spectral_breakdown"]
