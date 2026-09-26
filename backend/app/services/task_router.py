import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class TaskRouter:
    """Classifies user intent and routes queries and imagery to the appropriate specialist model."""

    SUPPORTED_TASKS = [
        "Single-Image VQA",
        "Scene Description",
        "Grounding",
        "Bi-Temporal Change",
        "Optical + SAR Fusion",
        "Segmentation",
        "Classification",
        "Unsupported Request",
        "Needs Clarification"
    ]

    @staticmethod
    def route_task(
        mode: str,
        query: str,
        has_temporal_pair: bool = False,
        has_optical_sar_pair: bool = False
    ) -> Tuple[str, str, str]:
        """
        Determines task type, execution engine, and specialist tools required.
        Returns:
            (task_name, model_pipeline, task_code)
        """
        q = query.strip().lower()

        if not q:
            return "Scene Description", "VQA Specialist", "scene_description"

        # Mode overrides and intent analysis
        if mode == "fusion" or has_optical_sar_pair or any(k in q for k in ["sar", "optical and sar", "fusion", "radar", "backscatter"]):
            return "Optical + SAR Fusion", "Optical Encoder · SAR Encoder · Fusion", "optical_sar_analysis"

        if (mode == "temporal" or has_temporal_pair or any(k in q for k in ["change", "between these two", "increased", "decreased", "growth", "before and after"])) and not has_optical_sar_pair:
            return "Bi-Temporal Change", "Change Understanding · Grounding", "bi_temporal_change"

        if any(k in q for k in ["highlight", "locate", "where is", "bounding box", "find the", "point out", "delineate"]):
            return "Grounding", "Grounding · Localization Specialist", "grounding"

        if any(k in q for k in ["segment", "mask", "delineate boundaries"]):
            return "Grounding", "Grounding · Spectral Segmentation", "segmentation"

        if any(k in q for k in ["classify", "type of terrain", "which class"]):
            return "Single-Image VQA", "Classification Specialist · VQA", "classification"

        if any(k in q for k in ["describe", "what is visible", "overview", "types visible", "land cover", "objects"]):
            return "Single-Image VQA", "Single-Image VQA · Remote Sensing Understanding", "single_image_vqa"

        # General query default
        return "Single-Image VQA", "Single-Image VQA · Grounding", "single_image_vqa"

task_router = TaskRouter()
