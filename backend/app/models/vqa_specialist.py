from typing import Dict, Any, Optional
from app.models.vqa_adapter import vqa_adapter

class VQASpecialist:
    """
    Specialist model interface for remote-sensing Visual Question Answering and Scene Understanding.
    Delegates to the deep VQAAdapter foundation model.
    """

    def __init__(self):
        self.model_name = vqa_adapter.get_model_name()

    def answer_query(
        self,
        image_path: str,
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs deep visual feature representation and scene reasoning on the authoritative AOI raster.
        """
        findings = vqa_adapter.analyze_raster(
            raster_path=image_path,
            query=query,
            aoi_metadata=aoi_metadata,
            analysis_id=analysis_id
        )

        res = findings.to_analysis_dict()
        # Maintain backward-compatible spectral_breakdown mapping for legacy callers
        breakdown = {
            "vegetation_pct": 0.0,
            "urban_pct": 0.0,
            "water_pct": 0.0,
            "barren_pct": 0.0,
        }
        for lc in findings.land_cover:
            name = lc.class_name.lower()
            if "vegetation" in name or "crop" in name or "forest" in name:
                breakdown["vegetation_pct"] = max(breakdown["vegetation_pct"], lc.coverage_pct)
            if "built" in name or "urban" in name or "structure" in name:
                breakdown["urban_pct"] = max(breakdown["urban_pct"], lc.coverage_pct)
            if "water" in name:
                breakdown["water_pct"] = max(breakdown["water_pct"], lc.coverage_pct)
            if "barren" in name or "open" in name or "soil" in name:
                breakdown["barren_pct"] = max(breakdown["barren_pct"], lc.coverage_pct)
            key = lc.class_name.lower().replace(" ", "_").replace("&", "").replace("/", "_")
            breakdown[f"{key}_pct"] = lc.coverage_pct
        res["spectral_breakdown"] = breakdown
        return res

vqa_specialist = VQASpecialist()
