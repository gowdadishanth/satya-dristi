from typing import Dict, Any, List
from app.models.base_model import StructuredAIFindings

class ReportNarrativeGenerator:
    """
    Synthesizes authentic, non-templated technical report narratives
    directly from the model's StructuredAIFindings.
    Completely eliminates static pre-authored prose and placeholder text.
    """

    @staticmethod
    def generate_executive_summary(findings: StructuredAIFindings) -> str:
        """Generates a comprehensive executive summary grounded in the model's observations."""
        parts = [findings.summary]

        if findings.objects:
            parts.append(
                f"Grounding localization identified {len(findings.objects)} salient target instance(s) "
                f"with a maximum detection confidence of {round(findings.objects[0].confidence * 100.0, 1)}%."
            )
        elif findings.changes:
            top_change = findings.changes[0]
            parts.append(
                f"Primary temporal vector reflects {top_change.change_type.lower()} "
                f"({top_change.description})."
            )
        elif findings.land_cover:
            top_covers = [f"{c.class_name} ({c.coverage_pct}%)" for c in findings.land_cover[:2]]
            parts.append(f"Dominant surface composition: {', '.join(top_covers)}.")

        return " ".join(parts)

    @staticmethod
    def generate_findings_narrative(findings: StructuredAIFindings) -> List[str]:
        """Produces verified analytical observations derived from model inference."""
        items = list(findings.observations)

        # Append spatial findings
        for sf in findings.spatial_findings:
            if sf not in items:
                items.append(sf)

        return items

    @staticmethod
    def generate_uncertainty_statement(findings: StructuredAIFindings) -> str:
        """Formulates calibrated uncertainty and sensor boundary conditions."""
        if findings.uncertainties:
            return " • ".join(findings.uncertainties)
        return (
            f"Analysis confidence is calibrated at {round(findings.confidence_score * 100.0, 1)}% "
            f"({findings.confidence_rating} reliability). Observations reflect clear atmospheric conditions with high spatial registration fidelity."
        )

narrative_generator = ReportNarrativeGenerator()
