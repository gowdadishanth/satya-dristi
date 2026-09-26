from typing import Dict, Any, Optional
from app.models.optical_sar_adapter import optical_sar_adapter

class OpticalSARSpecialist:
    """
    Specialist model interface for multimodal Sentinel-2 (Optical) and Sentinel-1 (SAR) fusion.
    Delegates to the multimodal cross-sensor radiometric fusion foundation model adapter.
    """

    def __init__(self):
        self.model_name = optical_sar_adapter.get_model_name()

    def fuse_and_analyze(
        self,
        optical_path: str,
        sar_path: str,
        query: str,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Multimodal joint analysis of Sentinel-2 optical reflectance and Sentinel-1 SAR backscatter.
        """
        findings = optical_sar_adapter.analyze_fusion(
            optical_raster_path=optical_path,
            sar_raster_path=sar_path,
            query=query,
            analysis_id=analysis_id
        )

        res = findings.to_analysis_dict()
        res["task"] = "Optical + SAR Fusion"
        res["confidence"] = findings.confidence_rating
        metrics = findings.raw_model_metrics
        water_pct = metrics.get("water_pct", 0.0)
        urban_pct = metrics.get("urban_pct", 0.0)

        res["agreements"] = [
            {"label": "Optical Spectral", "state": metrics.get("optical_state", "agree")},
            {"label": "SAR Backscatter", "state": metrics.get("sar_state", "agree")},
            {"label": "Cross-Modal Fusion", "state": metrics.get("fusion_state", "agree")}
        ]
        res["confidence_score"] = findings.confidence_score
        res["optical_summary"] = f"Optical reflectance shows multi-spectral land cover with {water_pct}% verified open water bodies."
        res["sar_summary"] = f"SAR C-band backscatter highlights double-bounce corner reflectors ({urban_pct}% urban footprint) and specular absorption."
        res["fused_evidence_path"] = findings.evidence_path
        res["evidence_filename"] = findings.evidence_filename
        return res

optical_sar_specialist = OpticalSARSpecialist()
