import os
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.core.errors import SARUnavailableError
from app.models.base_model import StructuredAIFindings
from app.models.gemini_provider import gemini_provider

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Intelligent Earth Observation Model & Task Router.
    Routes execution exclusively to the primary cloud AI provider (GeminiProvider).
    Local heuristic adapters have been formally decommissioned.
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
        Asynchronously routes the analysis request to GeminiProvider.
        """
        task_norm = (task or "").lower()
        provider_type = (settings.AI_PROVIDER or "gemini").lower()

        if provider_type != "gemini":
            raise ValueError(
                f"Unsupported AI_PROVIDER '{provider_type}'. Satya Dristi production architecture "
                "operates exclusively with Gemini Cloud AI (AI_PROVIDER='gemini'). Local models are decommissioned."
            )

        logger.info(
            "Routing analysis %s (task='%s', provider='gemini') on primary raster: %s",
            analysis_id, task, primary_image_path
        )

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
        Synchronous routing interface for callers and test fixtures.
        Guarantees that routing executes through the active AI provider without bypassing to local heuristics.
        """
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # In an already running event loop, execute async routing in a worker thread to avoid deadlock
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
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
                return future.result()
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
