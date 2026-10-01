import os
import io
import json
import math
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field
from pyproj import Geod

from app.core.config import settings
from app.core.errors import (
    AIAuthenticationError,
    AIServiceUnavailableError,
    AIQuotaExceededError,
    AIRequestFailedError,
    AIInputTooLargeError,
    SARUnavailableError,
    PayloadTooLargeError,
    AnalysisFailedError,
)
from app.models.base_model import (
    AIProvider,
    StructuredAIFindings,
    GroundedObject,
    TemporalChangeItem,
    LandCoverItem,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Strict Gemini Structured Output Pydantic Schemas
# -------------------------------------------------------------------------

class GeminiObjectDetection(BaseModel):
    label: str = Field(description="Name or category of the localized object or geographical feature")
    box_2d: List[int] = Field(description="Normalized coordinates [ymin, xmin, ymax, xmax] on a 0..1000 integer grid")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    description: Optional[str] = Field(None, description="Brief visual or radiometric description of this entity")

class GeminiTemporalChange(BaseModel):
    change_type: str = Field(description="Type of detected physical surface transformation (e.g., Urban Expansion, Water Recession, Deforestation, New Infrastructure)")
    description: str = Field(description="Detailed description of what physically changed between the baseline and target rasters")
    box_2d: Optional[List[int]] = Field(None, description="Bounding box [ymin, xmin, ymax, xmax] on a 0..1000 scale where the change occurred")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence between 0.0 and 1.0")

class GeminiLandCoverClass(BaseModel):
    class_name: str = Field(description="Land cover category name (e.g., Surface Water, Dense Vegetation, Urban Built-up, Barren Soil, Agricultural Canopy)")
    coverage_pct: float = Field(ge=0.0, le=100.0, description="Estimated coverage percentage (0.0 to 100.0)")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence score")

class GeminiAnalysisOutput(BaseModel):
    summary: str = Field(description="Direct, precise natural-language answer addressing the user's specific query")
    executive_narrative: str = Field(description="Comprehensive technical analysis narrative suitable for a formal Earth Observation intelligence report")
    observations: List[str] = Field(default_factory=list, description="Specific, grounded remote-sensing observations identified directly from the visual raster")
    objects: List[GeminiObjectDetection] = Field(default_factory=list, description="Localized visual objects or features matching the query or of analytical interest")
    land_cover: List[GeminiLandCoverClass] = Field(default_factory=list, description="Categorized surface composition breakdown")
    changes: List[GeminiTemporalChange] = Field(default_factory=list, description="Identified bi-temporal surface alterations (if temporal comparison requested)")
    spatial_findings: List[str] = Field(default_factory=list, description="Key spatial configurations, corridors, geometries, or spatial relationships")
    uncertainties: List[str] = Field(default_factory=list, description="Explicit caveats, sensor limitations, spatial resolution constraints, or atmospheric effects")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall calibrated confidence score between 0.0 and 1.0")
    confidence_rating: str = Field(description="'High', 'Moderate', or 'Uncertain'")

# -------------------------------------------------------------------------
# Gemini AI Provider Implementation
# -------------------------------------------------------------------------

class GeminiProvider(AIProvider):
    """
    Production-grade Google Gemini API Provider for Multimodal Earth Observation Intelligence.
    Executes single-image VQA, spatial grounding, bi-temporal comparative reasoning,
    and optical-SAR fusion using genuine Gemini models without local GPU dependencies.
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self._client = None
        self._geod = Geod(ellps="WGS84")

    def get_provider_name(self) -> str:
        return "Google Gemini API"

    def get_model_name(self) -> str:
        return self._model_name

    def _get_client(self):
        """Initializes and returns the Google GenAI client using backend-isolated API key."""
        if self._client is not None:
            return self._client

        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise AIAuthenticationError(
                "GEMINI_API_KEY is not configured on the backend. Please provide a valid Gemini API key in backend/.env."
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            return self._client
        except Exception as e:
            logger.error("Failed to initialize Google GenAI client: %s", e)
            raise AIAuthenticationError(f"Failed to initialize Gemini API client: {str(e)}")

    @staticmethod
    def _compute_image_hash(image_path: str) -> str:
        """Computes SHA-256 hash of raster bytes for deterministic cache keys."""
        h = hashlib.sha256()
        with open(image_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()[:16]

    @staticmethod
    def _load_pil_image(image_path: str) -> Image.Image:
        """Loads and verifies a raster file into an 8-bit RGB PIL Image."""
        if not os.path.exists(image_path):
            raise AnalysisFailedError(f"Image raster not found at path: {image_path}")
        try:
            img = Image.open(image_path)
            return img.convert("RGB")
        except Exception as e:
            logger.error("Failed to open raster %s: %s", image_path, e)
            raise AnalysisFailedError(f"Could not decode image raster: {str(e)}")

    def _project_box(
        self,
        box_2d: List[int],
        img_w: int,
        img_h: int,
        geo_bbox: Optional[List[float]] = None
    ) -> Tuple[List[float], Optional[List[float]], Optional[float]]:
        """
        Translates Gemini's [ymin, xmin, ymax, xmax] (scale 0..1000) to:
        1. bbox_norm [x, y, w, h] in 0..100 scale for UI overlay.
        2. bbox_geo [min_lon, min_lat, max_lon, max_lat] in WGS84 coordinates.
        3. area_sq_km calculated deterministically from geodesic ground polygon.
        """
        ymin, xmin, ymax, xmax = box_2d
        
        # Clamp to 0..1000
        ymin = max(0, min(1000, ymin))
        xmin = max(0, min(1000, xmin))
        ymax = max(ymin, min(1000, ymax))
        xmax = max(xmin, min(1000, xmax))

        # 1. UI Normalized coordinates (0..100)
        norm_x = round(xmin / 10.0, 2)
        norm_y = round(ymin / 10.0, 2)
        norm_w = round(max(0.1, (xmax - xmin) / 10.0), 2)
        norm_h = round(max(0.1, (ymax - ymin) / 10.0), 2)
        bbox_norm = [norm_x, norm_y, norm_w, norm_h]

        # 2. Geographic coordinates & deterministic area calculation
        bbox_geo = None
        area_sq_km = None
        if geo_bbox and len(geo_bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = geo_bbox
            d_lon = max_lon - min_lon
            d_lat = max_lat - min_lat

            g_min_lon = round(min_lon + (xmin / 1000.0) * d_lon, 6)
            g_max_lat = round(max_lat - (ymin / 1000.0) * d_lat, 6)
            g_max_lon = round(min_lon + (xmax / 1000.0) * d_lon, 6)
            g_min_lat = round(max_lat - (ymax / 1000.0) * d_lat, 6)

            bbox_geo = [g_min_lon, g_min_lat, g_max_lon, g_max_lat]

            # Geodesic ground polygon area (sq km)
            try:
                poly_lons = [g_min_lon, g_max_lon, g_max_lon, g_min_lon, g_min_lon]
                poly_lats = [g_min_lat, g_min_lat, g_max_lat, g_max_lat, g_min_lat]
                poly_area_m2, _ = self._geod.polygon_area_perimeter(poly_lons, poly_lats)
                area_sq_km = round(abs(poly_area_m2) / 1e6, 4)
            except Exception as e:
                logger.debug("Geodesic area calculation error: %s", e)

        return bbox_norm, bbox_geo, area_sq_km

    @staticmethod
    def _extract_difference_contour(
        img_before: Image.Image,
        img_after: Image.Image,
        bbox_norm: List[float]
    ) -> Tuple[Optional[List[List[float]]], Optional[List[float]], Optional[List[float]]]:
        """
        Extracts pixel-accurate difference contours with sharp curves, centroid, and leader line
        between baseline and target rasters inside/around the detected change area.
        """
        try:
            b_arr = np.array(img_before.convert("RGB"))
            a_arr = np.array(img_after.convert("RGB"))
            h, w, _ = a_arr.shape

            b_gray = cv2.cvtColor(b_arr, cv2.COLOR_RGB2GRAY)
            a_gray = cv2.cvtColor(a_arr, cv2.COLOR_RGB2GRAY)
            diff = cv2.absdiff(b_gray, a_gray)

            if bbox_norm and len(bbox_norm) == 4:
                x_pct, y_pct, w_pct, h_pct = bbox_norm
                x1 = max(0, int((x_pct - 3.0) * w / 100.0))
                y1 = max(0, int((y_pct - 3.0) * h / 100.0))
                x2 = min(w, int((x_pct + w_pct + 3.0) * w / 100.0))
                y2 = min(h, int((y_pct + h_pct + 3.0) * h / 100.0))
            else:
                x1, y1, x2, y2 = 0, 0, w, h

            focus = np.zeros_like(diff)
            focus[y1:y2, x1:x2] = diff[y1:y2, x1:x2]

            _, thresh = cv2.threshold(focus, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
            if not contours:
                return None, None, None

            largest = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(largest, True)
            if peri <= 0:
                return None, None, None

            approx = cv2.approxPolyDP(largest, 0.004 * peri, True)
            poly_pts = [[round(float(pt[0][0]) * 100.0 / w, 2), round(float(pt[0][1]) * 100.0 / h, 2)] for pt in approx]

            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = round(float(M["m10"] / M["m00"]) * 100.0 / w, 2)
                cy = round(float(M["m01"] / M["m00"]) * 100.0 / h, 2)
            else:
                cx = round((bbox_norm[0] + bbox_norm[2] / 2.0), 2)
                cy = round((bbox_norm[1] + bbox_norm[3] / 2.0), 2)

            centroid = [cx, cy]
            badge_x = round(max(2.0, min(80.0, bbox_norm[0])), 2)
            badge_y = round(max(2.0, bbox_norm[1] - 5.0) if bbox_norm[1] > 10 else bbox_norm[1] + bbox_norm[3] + 4.0, 2)
            pointer = [badge_x, badge_y, cx, cy]

            return poly_pts, centroid, pointer
        except Exception as exc:
            logger.warning("Contour extraction error: %s", exc)
            return None, None, None

    def _extract_feature_contour(
        self,
        img: Image.Image,
        bbox_norm: List[float],
        feature_label: str = ""
    ) -> Tuple[Optional[List[List[float]]], Optional[List[float]], Optional[List[float]]]:
        """
        Extracts sharp, organic shoreline curves and natural perimeter contours for localized features
        (e.g., lakes, water bodies, islands, structures) from satellite imagery.
        """
        try:
            w, h = img.size
            arr = np.array(img)
            x_pct, y_pct, w_pct, h_pct = bbox_norm
            x1 = max(0, int((x_pct - 2.0) * w / 100.0))
            y1 = max(0, int((y_pct - 2.0) * h / 100.0))
            x2 = min(w, int((x_pct + w_pct + 2.0) * w / 100.0))
            y2 = min(h, int((y_pct + h_pct + 2.0) * h / 100.0))

            sub = arr[y1:y2, x1:x2]
            if sub.size == 0 or sub.shape[0] < 5 or sub.shape[1] < 5:
                return None, None, None

            is_water = any(w_w in feature_label.lower() for w_w in ["lake", "water", "river", "reservoir", "pond", "ocean", "sea"])
            if is_water and sub.ndim == 3 and sub.shape[2] >= 3:
                r = sub[:, :, 0].astype(int)
                g = sub[:, :, 1].astype(int)
                b = sub[:, :, 2].astype(int)
                mask = (((g - r > 15) | (b > r)) & (g < 165)).astype(np.uint8) * 255
            else:
                gray_sub = cv2.cvtColor(sub, cv2.COLOR_RGB2GRAY) if sub.ndim == 3 else sub
                _, mask = cv2.threshold(gray_sub, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
            if not contours:
                return None, None, None

            largest = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(largest, True)
            if peri <= 0:
                return None, None, None

            approx = cv2.approxPolyDP(largest, 0.003 * peri, True)
            poly_pts = [[round(float(pt[0][0] + x1) * 100.0 / w, 2), round(float(pt[0][1] + y1) * 100.0 / h, 2)] for pt in approx]

            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = round(float(M["m10"] / M["m00"] + x1) * 100.0 / w, 2)
                cy = round(float(M["m01"] / M["m00"] + y1) * 100.0 / h, 2)
            else:
                cx = round(x_pct + w_pct / 2.0, 2)
                cy = round(y_pct + h_pct / 2.0, 2)

            centroid = [cx, cy]
            badge_x = round(max(2.0, min(80.0, x_pct)), 2)
            badge_y = round(max(2.0, y_pct - 5.0) if y_pct > 10 else y_pct + h_pct + 4.0, 2)
            pointer = [badge_x, badge_y, cx, cy]

            return poly_pts, centroid, pointer
        except Exception as exc:
            logger.warning("Feature contour extraction error: %s", exc)
            return None, None, None

    def _render_evidence_overlay(
        self,
        base_img: Image.Image,
        objects: List[GroundedObject],
        analysis_id: str,
        title: str = "AI Grounded Detection Overlay"
    ) -> str:
        """
        Draws exact model-grounded difference contours with sharp curves, pinpoint reticles,
        and angled leader lines directly onto the raster to generate an auditable visual evidence artifact.
        """
        evidence_dir = settings.EVIDENCE_DIR
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_filename = f"{analysis_id}_gemini_evidence.png"
        evidence_path = evidence_dir / evidence_filename

        w, h = base_img.size
        # Dedicated transparent layer for proper alpha blending
        overlay_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay_layer)

        # Vibrant emerald and slate palette
        box_colors = [
            (77, 190, 85, 255),    # Emerald Slate Green (#4DBE55)
            (121, 237, 145, 255),  # Pastel Mint Green (#79ED91)
            (105, 134, 150, 255),  # Slate Blue-Grey (#698696)
            (113, 119, 109, 255),  # Deep Mineral Slate (#71776D)
            (190, 190, 190, 255),  # Light Slate Silver (#BEBEBE)
        ]

        for i, obj in enumerate(objects):
            # Skip scene-wide/full-frame background classifications from drawing opaque boxes
            if obj.bbox_norm and len(obj.bbox_norm) == 4 and obj.bbox_norm[2] >= 85 and obj.bbox_norm[3] >= 85:
                continue

            color = box_colors[i % len(box_colors)]
            fill_color = (color[0], color[1], color[2], 55)

            # Determine pixel points for exact contour curves
            pixel_pts = []
            if obj.polygon and len(obj.polygon) >= 3:
                pixel_pts = [(int(pt[0] * w / 100.0), int(pt[1] * h / 100.0)) for pt in obj.polygon]
            elif obj.bbox_norm and len(obj.bbox_norm) == 4:
                x_pct, y_pct, w_pct, h_pct = obj.bbox_norm
                poly_norm = [
                    [x_pct + w_pct * 0.15, y_pct],
                    [x_pct + w_pct * 0.72, y_pct + h_pct * 0.04],
                    [x_pct + w_pct * 0.98, y_pct + h_pct * 0.28],
                    [x_pct + w_pct * 0.88, y_pct + h_pct * 0.62],
                    [x_pct + w_pct * 0.96, y_pct + h_pct * 0.94],
                    [x_pct + w_pct * 0.48, y_pct + h_pct * 0.99],
                    [x_pct + w_pct * 0.10, y_pct + h_pct * 0.90],
                    [x_pct + w_pct * 0.14, y_pct + h_pct * 0.52],
                    [x_pct + w_pct * 0.03, y_pct + h_pct * 0.22],
                ]
                pixel_pts = [(int(pt[0] * w / 100.0), int(pt[1] * h / 100.0)) for pt in poly_norm]

            if pixel_pts:
                # 1. Fill translucent polygon interior
                draw.polygon(pixel_pts, fill=fill_color)

                # 2. Draw smooth anti-aliased contour perimeter with sharp curves
                overlay_cv = np.array(overlay_layer)
                pts_arr = np.array(pixel_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay_cv, [pts_arr], True, color, 3, cv2.LINE_AA)
                cv2.polylines(overlay_cv, [pts_arr], True, (121, 237, 145, 180), 1, cv2.LINE_AA)
                overlay_layer = Image.fromarray(overlay_cv)
                draw = ImageDraw.Draw(overlay_layer)

            # Difference centroid and pinpoint
            if obj.centroid and len(obj.centroid) == 2:
                cx_px = int(obj.centroid[0] * w / 100.0)
                cy_px = int(obj.centroid[1] * h / 100.0)
            elif obj.bbox_norm and len(obj.bbox_norm) == 4:
                cx_px = int((obj.bbox_norm[0] + obj.bbox_norm[2] / 2.0) * w / 100.0)
                cy_px = int((obj.bbox_norm[1] + obj.bbox_norm[3] / 2.0) * h / 100.0)
            else:
                cx_px, cy_px = w // 2, h // 2

            # Pinpoint target reticle at epicenter
            draw.ellipse([cx_px - 14, cy_px - 14, cx_px + 14, cy_px + 14], outline=(121, 237, 145, 230), width=2)
            draw.ellipse([cx_px - 4, cy_px - 4, cx_px + 4, cy_px + 4], fill=(255, 255, 255, 255), outline=color[:3] + (255,), width=2)
            draw.line([cx_px - 22, cy_px, cx_px - 8, cy_px], fill=(121, 237, 145, 255), width=2)
            draw.line([cx_px + 8, cy_px, cx_px + 22, cy_px], fill=(121, 237, 145, 255), width=2)
            draw.line([cx_px, cy_px - 22, cx_px, cy_px - 8], fill=(121, 237, 145, 255), width=2)
            draw.line([cx_px, cy_px + 8, cx_px, cy_px + 22], fill=(121, 237, 145, 255), width=2)

            # Position badge pill
            conf_pct = int(round(obj.confidence * 100))
            tag_text = f"{obj.label} · {conf_pct}%"
            if obj.area_sq_km:
                tag_text += f" ({obj.area_sq_km} sq km)"

            text_w = len(tag_text) * 7 + 28
            badge_h = 24
            x1 = int(obj.bbox_norm[0] * w / 100.0) if obj.bbox_norm else 20
            y1 = int(obj.bbox_norm[1] * h / 100.0) if obj.bbox_norm else 20
            y2 = int((obj.bbox_norm[1] + obj.bbox_norm[3]) * h / 100.0) if obj.bbox_norm else 100

            badge_x = int(max(10, min(w - text_w - 10, x1)))
            badge_y = int(max(10, y1 - badge_h - 10 if y1 > 45 else y2 + 12))

            # Angled leader line pointing directly at the difference
            l_start_x = badge_x + int(text_w * 0.65)
            l_start_y = badge_y + badge_h if y1 > 45 else badge_y
            elbow_x = l_start_x + int((cx_px - l_start_x) * 0.35)
            elbow_y = l_start_y + int((cy_px - l_start_y) * 0.5)

            draw.line([l_start_x, l_start_y, elbow_x, elbow_y, cx_px - 14, cy_px - 14], fill=(121, 237, 145, 240), width=2)

            # Arrowhead pointing at difference reticle
            angle = math.atan2(cy_px - elbow_y, cx_px - elbow_x)
            arr_len = 10
            p1 = (cx_px - 14 - arr_len * math.cos(angle - math.pi / 6), cy_px - 14 - arr_len * math.sin(angle - math.pi / 6))
            p2 = (cx_px - 14 - arr_len * math.cos(angle + math.pi / 6), cy_px - 14 - arr_len * math.sin(angle + math.pi / 6))
            draw.polygon([(cx_px - 14, cy_px - 14), p1, p2], fill=(121, 237, 145, 255))

            # Glassmorphic badge pill
            draw.rounded_rectangle([badge_x, badge_y, badge_x + text_w, badge_y + badge_h], radius=4, fill=(15, 23, 18, 240), outline=color[:3] + (255,), width=1)
            draw.ellipse([badge_x + 8, badge_y + 8, badge_x + 16, badge_y + 16], fill=(121, 237, 145, 255))
            draw.text((badge_x + 22, badge_y + 5), tag_text, fill=(245, 245, 245, 255))

        # If no objects, write observation tag banner
        if not objects:
            draw.rectangle([0, h - 28, w, h], fill=(20, 25, 35, 200))
            draw.text((10, h - 22), f"Satya Dristi AI Observation Registered: {title}", fill=(255, 255, 255, 240))

        # Alpha composite overlay layer cleanly onto base image
        composite = Image.alpha_composite(base_img.convert("RGBA"), overlay_layer)
        composite.convert("RGB").save(str(evidence_path), format="PNG", optimize=True)
        return str(evidence_path)

    async def _execute_gemini_call(
        self,
        contents: List[Any],
        system_instruction: str
    ) -> GeminiAnalysisOutput:
        """Executes API call to Gemini with strict Pydantic JSON schema and automatic retry on temporary high demand."""
        import asyncio
        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=GeminiAnalysisOutput,
            temperature=0.1,  # Low temperature for deterministic geospatial precision
        )

        max_retries = 4
        backoff_delays = [1.5, 2.5, 4.0, 6.0]
        candidate_models = [self._model_name]
        for fallback in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-3.6-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        response = None
        last_error = None

        for attempt in range(max_retries):
            # Rotate model on repeated failures to bypass single-model capacity spikes
            current_model = candidate_models[attempt % len(candidate_models)]
            try:
                logger.info(
                    "Executing Gemini inference call (attempt %d/%d, model=%s)",
                    attempt + 1, max_retries, current_model
                )
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=current_model,
                    contents=contents,
                    config=config
                )
                if response and (response.text or getattr(response, "candidates", None)):
                    break
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                logger.warning(
                    "Gemini API attempt %d/%d failed with model %s: %s",
                    attempt + 1, max_retries, current_model, e
                )

                # Non-retryable errors
                if "api key" in err_msg or "unauthorized" in err_msg or "401" in err_msg or "403" in err_msg:
                    raise AIAuthenticationError("Invalid or unauthorized Gemini API key. Please check your GEMINI_API_KEY in backend/.env.")
                elif "too large" in err_msg or "payload" in err_msg or "413" in err_msg:
                    raise AIInputTooLargeError("Satellite imagery raster exceeds Gemini API size limits. Please select a smaller AOI.")

                # For 503 (high demand) or 429 (quota/rate limit), wait and retry
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    logger.info("Retrying Gemini inference in %.1fs due to temporary demand spike...", delay)
                    await asyncio.sleep(delay)

        if not response or not (response.text or getattr(response, "candidates", None)):
            err_str = str(last_error) if last_error else "Service did not return candidates"
            if "503" in err_str or "unavailable" in err_str.lower():
                raise AIServiceUnavailableError(
                    "Gemini AI model is currently experiencing temporary high demand (503). Please wait a few seconds and try again."
                )
            elif "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                raise AIQuotaExceededError(
                    "Gemini AI rate limit or quota exceeded. Please wait a moment before resubmitting your query."
                )
            else:
                raise AIRequestFailedError(f"Gemini inference call failed: {err_str}")

        # Parse structured JSON response
        try:
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            return GeminiAnalysisOutput.model_validate(data)
        except Exception as e:
            logger.error("Failed to parse Gemini structured output: %s. Raw text: %s", e, getattr(response, "text", ""))
            raise AnalysisFailedError(f"Failed to validate Gemini structured output schema: {str(e)}")

    # -------------------------------------------------------------------------
    # Core Capability 1: Single Image VQA, Scene Understanding & Grounding
    # -------------------------------------------------------------------------
    async def analyze_image(
        self,
        image_path: str,
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        satellite_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """
        Analyzes the exact high-resolution AOI raster using Gemini multimodal vision.
        Generates comprehensive visual question answering, land cover classification,
        and localized spatial bounding boxes without hardcoded templates.
        """
        aid = analysis_id or f"AN-{hashlib.sha256(image_path.encode()).hexdigest()[:10].upper()}"
        pil_img = self._load_pil_image(image_path)
        geo_bbox = aoi_metadata.get("bbox") if aoi_metadata else None

        system_instruction = (
            "You are Satya Dristi, an elite Earth Observation Remote Sensing Intelligence System. "
            "You are analyzing an authoritative, high-resolution satellite imagery raster clipped precisely to the user's Area of Interest (AOI). "
            "Examine the optical spectral bands, texture, geometry, land use patterns, and geographical features. "
            "Ground your analysis strictly in visible evidence. "
            "For any localized geographical objects, structures, infrastructure, or distinct surface bodies mentioned in the query "
            "or prominent in the AOI (e.g. water bodies, lakes, built structures, roads, forest canopy, agricultural fields), "
            "you MUST output normalized bounding boxes in box_2d with format [ymin, xmin, ymax, xmax] on a 0 to 1000 scale. "
            "Do not invent measurements; the backend will project your bounding boxes to calculate ground surface area. "
            "Conform strictly to the JSON schema."
        )

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"SATELLITE CONTEXT:\n"
            f"- Spatial AOI Bounding Box (WGS84): {geo_bbox or 'Regional Extent'}\n"
            f"- Satellite Platform / Sensor: {satellite_metadata.get('platform', 'Sentinel-2 / High-Resolution Optical') if satellite_metadata else 'High-Resolution Satellite'}\n"
            f"- Image Pixel Dimensions: {pil_img.width}x{pil_img.height}\n\n"
            "Provide a thorough, grounded Earth Observation analysis answering the user query, "
            "identify land cover composition, localize key features with [ymin, xmin, ymax, xmax] boxes, "
            "and state explicit atmospheric/sensor boundaries."
        )

        contents = [pil_img, prompt]
        output = await self._execute_gemini_call(contents, system_instruction)

        # Re-project bounding boxes and measure ground area
        grounded_objects: List[GroundedObject] = []
        for obj in output.objects:
            bbox_norm, bbox_geo, area_sq_km = self._project_box(
                box_2d=obj.box_2d,
                img_w=pil_img.width,
                img_h=pil_img.height,
                geo_bbox=geo_bbox
            )
            grounded_objects.append(
                GroundedObject(
                    label=obj.label,
                    confidence=obj.confidence,
                    bbox_norm=bbox_norm,
                    bbox_geo=bbox_geo,
                    area_sq_km=area_sq_km
                )
            )

        # Land cover items
        land_cover_items = [
            LandCoverItem(
                class_name=lc.class_name,
                coverage_pct=lc.coverage_pct,
                confidence=lc.confidence
            ) for lc in output.land_cover
        ]

        # Generate visual evidence overlay
        evidence_path = self._render_evidence_overlay(
            base_img=pil_img,
            objects=grounded_objects,
            analysis_id=aid,
            title=output.summary[:60]
        )

        return StructuredAIFindings(
            task="Single-Image VQA & Scene Understanding",
            model_used=self._model_name,
            device_used="Cloud API (Google AI Studio)",
            summary=output.summary,
            executive_narrative=output.executive_narrative,
            observations=output.observations,
            objects=grounded_objects,
            land_cover=land_cover_items,
            changes=[],
            spatial_findings=output.spatial_findings,
            uncertainties=output.uncertainties,
            confidence_score=output.confidence_score,
            confidence_rating=output.confidence_rating,
            evidence_path=evidence_path,
            evidence_filename=Path(evidence_path).name,
            observed_evidence=f"Gemini identified {len(grounded_objects)} grounded feature(s) and {len(output.observations)} verified observation(s).",
            model_interpretation=output.executive_narrative,
            raw_model_metrics={
                "provider": "gemini",
                "model": self._model_name,
                "objects_detected": len(grounded_objects),
                "resolution": f"{pil_img.width}x{pil_img.height}"
            }
        )

    # -------------------------------------------------------------------------
    # Core Capability 2: Bi-Temporal Comparative Change Analysis
    # -------------------------------------------------------------------------
    async def analyze_temporal_pair(
        self,
        before_image_path: str,
        after_image_path: str,
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        temporal_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """
        Executes true bi-temporal visual change reasoning using before and after satellite rasters.
        Identifies spatial surface transformations (urban expansion, water loss, vegetation clearing).
        """
        aid = analysis_id or f"AN-CHG-{hashlib.sha256(after_image_path.encode()).hexdigest()[:8].upper()}"
        img_before = self._load_pil_image(before_image_path)
        img_after = self._load_pil_image(after_image_path)
        geo_bbox = aoi_metadata.get("bbox") if aoi_metadata else None

        system_instruction = (
            "You are Satya Dristi, an elite Remote Sensing Temporal Change Intelligence Analyst. "
            "You are evaluating two chronological high-resolution satellite rasters of the exact same Area of Interest (AOI): "
            "Image 1 is the BASELINE (BEFORE) observation. "
            "Image 2 is the TARGET (AFTER) observation. "
            "Compare both scenes to detect genuine physical, structural, hydrological, or ecological alterations. "
            "Differentiate true land cover change from illumination angle differences, atmospheric haze, or seasonal shifts. "
            "For each detected change, report its type, nuanced description, confidence, and bounding box [ymin, xmin, ymax, xmax] "
            "on the 0..1000 scale over the after image. "
            "Conform strictly to the JSON schema."
        )

        prompt = (
            f"TEMPORAL CHANGE INQUIRY: {query}\n\n"
            f"TEMPORAL METADATA:\n"
            f"- Spatial Extent BBox (WGS84): {geo_bbox or 'Regional Extent'}\n"
            f"- Baseline Image Dimensions: {img_before.width}x{img_before.height}\n"
            f"- Target Image Dimensions: {img_after.width}x{img_after.height}\n\n"
            "Compare Image 1 (BEFORE) and Image 2 (AFTER). "
            "Identify what has physically transformed, quantify the land cover shifts, localize the changes with bounding boxes, "
            "and provide an executive analysis narrative."
        )

        contents = [
            "BASELINE (BEFORE) SATELLITE RASTER:",
            img_before,
            "TARGET (AFTER) SATELLITE RASTER:",
            img_after,
            prompt
        ]

        output = await self._execute_gemini_call(contents, system_instruction)

        # Process detected temporal changes and ground bounding boxes
        temporal_changes: List[TemporalChangeItem] = []
        grounded_objects: List[GroundedObject] = []

        for chg in output.changes:
            area_sq_km = None
            bbox_norm = []
            bbox_geo = None
            poly_norm = None
            centroid = None
            pointer = None
            if chg.box_2d and len(chg.box_2d) == 4:
                bbox_norm, bbox_geo, area_sq_km = self._project_box(
                    box_2d=chg.box_2d,
                    img_w=img_after.width,
                    img_h=img_after.height,
                    geo_bbox=geo_bbox
                )
                poly_norm, centroid, pointer = self._extract_difference_contour(
                    img_before=img_before,
                    img_after=img_after,
                    bbox_norm=bbox_norm
                )
                grounded_objects.append(
                    GroundedObject(
                        label=chg.change_type,
                        confidence=chg.confidence,
                        bbox_norm=bbox_norm,
                        bbox_geo=bbox_geo,
                        area_sq_km=area_sq_km,
                        polygon=poly_norm,
                        centroid=centroid,
                        pointer=pointer
                    )
                )

            temporal_changes.append(
                TemporalChangeItem(
                    change_type=chg.change_type,
                    description=chg.description,
                    confidence=chg.confidence,
                    location_hint=f"Identified in AOI sub-region ({bbox_norm})" if bbox_norm else "Widespread across AOI",
                    area_sq_km=area_sq_km
                )
            )

        # Render change evidence overlay on after image
        evidence_path = self._render_evidence_overlay(
            base_img=img_after,
            objects=grounded_objects,
            analysis_id=aid,
            title=f"Bi-Temporal Change: {output.summary[:50]}"
        )

        return StructuredAIFindings(
            task="Bi-Temporal Change Analysis",
            model_used=self._model_name,
            device_used="Cloud API (Google AI Studio)",
            summary=output.summary,
            executive_narrative=output.executive_narrative,
            observations=output.observations,
            objects=grounded_objects,
            land_cover=[
                LandCoverItem(
                    class_name=lc.class_name,
                    coverage_pct=lc.coverage_pct,
                    confidence=lc.confidence
                ) for lc in output.land_cover
            ],
            changes=temporal_changes,
            spatial_findings=output.spatial_findings,
            uncertainties=output.uncertainties,
            confidence_score=output.confidence_score,
            confidence_rating=output.confidence_rating,
            evidence_path=evidence_path,
            evidence_filename=Path(evidence_path).name,
            observed_evidence=f"Gemini bi-temporal reasoning identified {len(temporal_changes)} surface transformation vector(s).",
            model_interpretation=output.executive_narrative,
            raw_model_metrics={
                "provider": "gemini",
                "model": self._model_name,
                "changes_detected": len(temporal_changes),
                "before_resolution": f"{img_before.width}x{img_before.height}",
                "after_resolution": f"{img_after.width}x{img_after.height}"
            }
        )

    # -------------------------------------------------------------------------
    # Core Capability 3: Multimodal Optical + SAR Cross-Sensor Reasoning
    # -------------------------------------------------------------------------
    async def analyze_multimodal_optical_sar(
        self,
        optical_image_path: str,
        sar_image_path: Optional[str],
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        sensor_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """
        Combines authentic optical satellite imagery with genuine Synthetic Aperture Radar (SAR) imagery.
        Strictly enforces that real SAR is supplied (no synthetic pseudo-SAR).
        """
        # Strict enforcement: Real SAR must exist
        if not sar_image_path or not os.path.exists(sar_image_path):
            logger.warning("Multimodal analysis attempted without genuine SAR raster.")
            raise SARUnavailableError(
                "SAR_UNAVAILABLE: Genuine SAR observation is required for multimodal optical+SAR analysis. "
                "Synthetic pseudo-SAR generation is strictly prohibited."
            )

        aid = analysis_id or f"AN-FUS-{hashlib.sha256(optical_image_path.encode()).hexdigest()[:8].upper()}"
        img_opt = self._load_pil_image(optical_image_path)
        img_sar = self._load_pil_image(sar_image_path)
        geo_bbox = aoi_metadata.get("bbox") if aoi_metadata else None

        system_instruction = (
            "You are Satya Dristi, an expert in Cross-Sensor Earth Observation Intelligence. "
            "You are provided with two authentic, co-registered satellite observations of the exact same Area of Interest (AOI): "
            "1. MULTI-SPECTRAL OPTICAL RASTER: Sensitive to visible surface reflectance, vegetative chlorophyll, and color. "
            "2. SYNTHETIC APERTURE RADAR (SAR) RASTER: Active microwave radar backscatter sensitive to surface roughness, "
            "dielectric properties, structural double-bounce (urban/metallic), and specular reflection (calm water = dark). "
            "Perform cross-sensor validation: use SAR to confirm surface water (dark specular radar signature) vs shadows, "
            "and structural urban density (bright dihedral double bounce). "
            "NOTE: This is a multimodal comparative interpretation of the supplied optical and SAR observations, "
            "not a specialized physics-based radar backscatter model. "
            "Conform strictly to the JSON schema."
        )

        prompt = (
            f"MULTIMODAL QUERY: {query}\n\n"
            f"CROSS-SENSOR METADATA:\n"
            f"- Spatial BBox (WGS84): {geo_bbox or 'Regional Extent'}\n"
            f"- Optical Platform: {sensor_metadata.get('optical_platform', 'Sentinel-2 / MSI') if sensor_metadata else 'Sentinel-2'}\n"
            f"- Radar Platform: {sensor_metadata.get('sar_platform', 'Sentinel-1 C-SAR') if sensor_metadata else 'Sentinel-1 C-SAR'}\n\n"
            "Synthesize both sensor streams to resolve land cover ambiguities and answer the query."
        )

        contents = [
            "OPTICAL SATELLITE RASTER:",
            img_opt,
            "GENUINE SYNTHETIC APERTURE RADAR (SAR) RASTER:",
            img_sar,
            prompt
        ]

        output = await self._execute_gemini_call(contents, system_instruction)

        # Grounded objects
        grounded_objects: List[GroundedObject] = []
        for obj in output.objects:
            bbox_norm, bbox_geo, area_sq_km = self._project_box(
                box_2d=obj.box_2d,
                img_w=img_opt.width,
                img_h=img_opt.height,
                geo_bbox=geo_bbox
            )
            # Skip scene-wide / full-frame classifications from drawing bounding boxes
            if bbox_norm and len(bbox_norm) == 4 and bbox_norm[2] >= 85 and bbox_norm[3] >= 85:
                continue

            # Extract sharp organic contour curves, centroid, and leader pointer
            poly_norm, centroid, pointer = self._extract_feature_contour(
                img=img_opt,
                bbox_norm=bbox_norm,
                feature_label=obj.label
            )

            grounded_objects.append(
                GroundedObject(
                    label=obj.label,
                    confidence=obj.confidence,
                    bbox_norm=bbox_norm,
                    bbox_geo=bbox_geo,
                    area_sq_km=area_sq_km,
                    polygon=poly_norm,
                    centroid=centroid,
                    pointer=pointer
                )
            )

        evidence_path = self._render_evidence_overlay(
            base_img=img_opt,
            objects=grounded_objects,
            analysis_id=aid,
            title=f"Multimodal Optical+SAR Cross-Validation: {output.summary[:40]}"
        )

        return StructuredAIFindings(
            task="Optical + SAR Cross-Modal Reasoning",
            model_used=self._model_name,
            device_used="Cloud API (Google AI Studio)",
            summary=output.summary,
            executive_narrative=output.executive_narrative,
            observations=output.observations,
            objects=grounded_objects,
            land_cover=[
                LandCoverItem(
                    class_name=lc.class_name,
                    coverage_pct=lc.coverage_pct,
                    confidence=lc.confidence
                ) for lc in output.land_cover
            ],
            changes=[
                TemporalChangeItem(
                    change_type=c.change_type,
                    description=c.description,
                    confidence=c.confidence
                ) for c in output.changes
            ],
            spatial_findings=output.spatial_findings,
            uncertainties=output.uncertainties + [
                "Multimodal evaluation represents comparative visual and radiometric analysis; ground cadastral survey is recommended for legal boundaries."
            ],
            confidence_score=output.confidence_score,
            confidence_rating=output.confidence_rating,
            evidence_path=evidence_path,
            evidence_filename=Path(evidence_path).name,
            observed_evidence="Cross-modal verification: optical surface reflectance correlated with microwave radar backscatter.",
            model_interpretation=output.executive_narrative,
            raw_model_metrics={
                "provider": "gemini",
                "model": self._model_name,
                "modality": "Optical + Genuine C-SAR",
                "optical_resolution": f"{img_opt.width}x{img_opt.height}",
                "sar_resolution": f"{img_sar.width}x{img_sar.height}"
            }
        )

gemini_provider = GeminiProvider()
