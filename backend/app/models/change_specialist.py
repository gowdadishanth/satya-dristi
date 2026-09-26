from typing import Dict, Any, List, Optional
from app.models.change_adapter import change_adapter

class ChangeSpecialist:
    """
    Specialist model interface for bi-temporal remote-sensing change detection and classification.
    Delegates to the deep Siamese change reasoner foundation model adapter.
    """

    def __init__(self):
        self.model_name = change_adapter.get_model_name()

    def analyze_change(
        self,
        before_image_path: str,
        after_image_path: str,
        query: str,
        geo_bbox: Optional[List[float]] = None,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes bi-temporal change reasoning over the paired AOI rasters.
        """
        findings = change_adapter.analyze_change(
            before_raster_path=before_image_path,
            after_raster_path=after_image_path,
            query=query,
            geo_bbox=geo_bbox,
            analysis_id=analysis_id
        )

        res = findings.to_analysis_dict()
        metrics = findings.raw_model_metrics
        res["change_pct"] = metrics.get("change_pct", 0.0)
        res["built_up_change_pct"] = metrics.get("built_up_change_pct", 0.0)
        res["water_change_pct"] = metrics.get("water_change_pct", 0.0)
        res["evidence_image_path"] = findings.evidence_path
        res["evidence_filename"] = findings.evidence_filename
        return res

change_specialist = ChangeSpecialist()
