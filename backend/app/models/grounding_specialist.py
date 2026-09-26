from typing import Dict, Any, List, Optional
from app.models.grounding_adapter import grounding_adapter

class GroundingSpecialist:
    """
    Specialist model interface for remote-sensing feature and object grounding.
    Delegates to the OWLv2 open-vocabulary transformer foundation model adapter.
    """

    def __init__(self):
        self.model_name = grounding_adapter.get_model_name()

    def ground_feature(
        self,
        image_path: str,
        query: str,
        geo_bbox: Optional[List[float]] = None,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Locates features referred to in natural-language query within the real satellite raster
        using the OWLv2 open-vocabulary transformer grounding adapter.
        """
        findings = grounding_adapter.ground_raster(
            raster_path=image_path,
            query=query,
            geo_bbox=geo_bbox,
            analysis_id=analysis_id
        )

        res = findings.to_analysis_dict()

        # Map detected objects to legacy boxes list format for full backward compatibility
        q_low = query.lower()
        if any(w in q_low for w in ["water", "lake", "reservoir", "river", "pond", "canal"]):
            target = "water_body"
        elif any(w in q_low for w in ["built", "building", "urban", "structure", "city", "settlement"]):
            target = "built_up"
        elif any(w in q_low for w in ["vegetation", "forest", "tree", "crop", "canopy"]):
            target = "vegetation"
        elif any(w in q_low for w in ["road", "highway", "corridor"]):
            target = "road"
        else:
            target = "salient_feature"

        res["target"] = target

        boxes = []
        for obj in findings.objects:
            x, y, w, h = obj.bbox_norm
            boxes.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "confidence": obj.confidence,
                "class_name": obj.label.lower(),
                "geo_bbox": obj.bbox_geo,
                "bbox_geo": obj.bbox_geo,
                "area_sq_km": obj.area_sq_km,
                "pixel_box": [int(x), int(y), int(w), int(h)]
            })

        primary_box = boxes[0] if boxes else None
        res["boxes"] = boxes
        res["primary_box"] = primary_box
        res["mask_path"] = findings.evidence_path
        res["evidence_image_path"] = findings.evidence_path
        res["evidence_path"] = findings.evidence_path
        res["confidence"] = primary_box["confidence"] if primary_box else findings.confidence_score
        return res

grounding_specialist = GroundingSpecialist()
