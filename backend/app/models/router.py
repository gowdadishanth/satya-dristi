import os
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.core.errors import SARUnavailableError
from app.models.base_model import StructuredAIFindings
from app.models.gemini_provider import gemini_provider
from app.models.grounding_adapter import grounding_adapter
from app.models.vqa_adapter import vqa_adapter
from app.models.change_adapter import change_adapter
from app.models.optical_sar_adapter import optical_sar_adapter

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Intelligent Earth Observation Model & Task Router.
    Routes execution to the primary cloud AI provider (GeminiProvider)
    while maintaining fallback to local specialist foundation model adapters.
    """

    @staticmethod
    async def route_and_execute_async(
        task: str,
        primary_image_path: str,
        query: str,
        before_image_path: Optional[str] = None,
        sar_image_path: Optional[str] = None,
        aoi: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """
        Asynchronously routes the analysis request to the active AIProvider.
        """
        task_norm = (task or "").lower()
        provider_type = (settings.AI_PROVIDER or "gemini").lower()

        logger.info(
            "Routing analysis %s (task='%s', provider='%s') on primary raster: %s",
            analysis_id, task, provider_type, primary_image_path
        )

        if provider_type == "gemini":
            try:
                # 1. Bi-Temporal Change Detection
                if "change" in task_norm or "temporal" in task_norm or before_image_path:
                    if not before_image_path:
                        raise ValueError("Bi-temporal change analysis requires both baseline (before) and target (after) rasters.")
                    findings = await gemini_provider.analyze_temporal_pair(
                        before_image_path=before_image_path,
                        after_image_path=primary_image_path,
                        query=query,
                        aoi_metadata=aoi,
                        analysis_id=analysis_id
                    )
                    findings.task = "Bi-Temporal Change"
                    return findings

                # 2. Optical + SAR Multimodal Fusion
                elif "sar" in task_norm or "fusion" in task_norm or sar_image_path:
                    if not sar_image_path:
                        raise SARUnavailableError("Optical + SAR fusion analysis requires both optical and genuine SAR rasters.")
                    findings = await gemini_provider.analyze_multimodal_optical_sar(
                        optical_image_path=primary_image_path,
                        sar_image_path=sar_image_path,
                        query=query,
                        aoi_metadata=aoi,
                        analysis_id=analysis_id
                    )
                    findings.task = "Optical-SAR Fusion"
                    return findings

                # 3. Grounding, Referral Localization & Single-Image VQA
                else:
                    findings = await gemini_provider.analyze_image(
                        image_path=primary_image_path,
                        query=query,
                        aoi_metadata=aoi,
                        analysis_id=analysis_id
                    )
                    if "ground" in task_norm or "locate" in task_norm or "detect" in task_norm:
                        findings.task = "Grounding"
                    else:
                        findings.task = "Single-Image VQA"
                    return findings
            except Exception as e:
                logger.warning("Gemini AI provider unavailable (%s), falling back to local specialist model.", e)

        # Fallback to local model adapters (e.g. offline testing or local preference)
        geo_bbox = aoi.get("bbox") if aoi else None
        if "change" in task_norm or "temporal" in task_norm or before_image_path:
            if not before_image_path:
                raise ValueError("Bi-temporal change analysis requires both baseline (before) and target (after) rasters.")
            return change_adapter.analyze_change(
                before_raster_path=before_image_path,
                after_raster_path=primary_image_path,
                query=query,
                geo_bbox=geo_bbox,
                analysis_id=analysis_id
            )
        elif "sar" in task_norm or "fusion" in task_norm or sar_image_path:
            if not sar_image_path:
                raise SARUnavailableError("Optical + SAR fusion analysis requires both optical and SAR rasters.")
            return optical_sar_adapter.analyze_fusion(
                optical_raster_path=primary_image_path,
                sar_raster_path=sar_image_path,
                query=query,
                aoi_metadata=aoi,
                analysis_id=analysis_id
            )
        elif "ground" in task_norm or "locate" in task_norm or "detect" in task_norm:
            return grounding_adapter.ground_raster(
                raster_path=primary_image_path,
                query=query,
                geo_bbox=geo_bbox,
                analysis_id=analysis_id
            )
        else:
            return vqa_adapter.analyze_raster(
                raster_path=primary_image_path,
                query=query,
                aoi_metadata=aoi,
                analysis_id=analysis_id
            )

    @classmethod
    def route_and_execute(
        cls,
        task: str,
        primary_image_path: str,
        query: str,
        before_image_path: Optional[str] = None,
        sar_image_path: Optional[str] = None,
        aoi: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """
        Synchronous routing interface for existing callers and test fixtures.
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # In an already running event loop, execute synchronous fallback adapter to avoid deadlock
            geo_bbox = aoi.get("bbox") if aoi else None
            task_norm = (task or "").lower()
            if "change" in task_norm or before_image_path:
                return change_adapter.analyze_change(
                    before_raster_path=before_image_path,
                    after_raster_path=primary_image_path,
                    query=query,
                    geo_bbox=geo_bbox,
                    analysis_id=analysis_id
                )
            elif "sar" in task_norm or sar_image_path:
                return optical_sar_adapter.analyze_fusion(
                    optical_raster_path=primary_image_path,
                    sar_raster_path=sar_image_path,
                    query=query,
                    aoi_metadata=aoi,
                    analysis_id=analysis_id
                )
            elif "ground" in task_norm or "detect" in task_norm:
                return grounding_adapter.ground_raster(
                    raster_path=primary_image_path,
                    query=query,
                    geo_bbox=geo_bbox,
                    analysis_id=analysis_id
                )
            else:
                return vqa_adapter.analyze_raster(
                    raster_path=primary_image_path,
                    query=query,
                    aoi_metadata=aoi,
                    analysis_id=analysis_id
                )
        else:
            return asyncio.run(
                cls.route_and_execute_async(
                    task=task,
                    primary_image_path=primary_image_path,
                    query=query,
                    before_image_path=before_image_path,
                    sar_image_path=sar_image_path,
                    aoi=aoi,
                    analysis_id=analysis_id
                )
            )

model_router = ModelRouter()
