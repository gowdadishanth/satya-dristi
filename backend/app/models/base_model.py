from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class GroundedObject(BaseModel):
    """Represents an object or feature localized by an AI grounding model."""
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    # Normalized coordinates 0..100 for UI overlay: [x, y, w, h]
    bbox_norm: List[float] = Field(default_factory=list)
    # Geographic coordinates [min_lon, min_lat, max_lon, max_lat]
    bbox_geo: Optional[List[float]] = None
    # Physical ground area in square kilometers
    area_sq_km: Optional[float] = None
    # Precise contour polygon normalized coordinates 0..100: [[x1, y1], [x2, y2], ...]
    polygon: Optional[List[List[float]]] = None
    # Hotspot / centroid pin pointing directly to the difference: [x, y]
    centroid: Optional[List[float]] = None
    # Pointer line coordinates: [start_x, start_y, target_x, target_y]
    pointer: Optional[List[float]] = None

class TemporalChangeItem(BaseModel):
    """Represents a specific physical surface alteration detected by AI."""
    change_type: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    location_hint: Optional[str] = None
    area_sq_km: Optional[float] = None

class LandCoverItem(BaseModel):
    """Represents a classified land cover constituent from AI visual features."""
    class_name: str
    coverage_pct: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)

class StructuredAIFindings(BaseModel):
    """
    Standardized, authoritative output schema produced by Remote-Sensing Foundation Models.
    Completely replaces static rule-based templates.
    """
    task: str
    model_used: str
    device_used: str
    summary: str
    executive_narrative: Optional[str] = None
    observations: List[str] = Field(default_factory=list)
    objects: List[GroundedObject] = Field(default_factory=list)
    land_cover: List[LandCoverItem] = Field(default_factory=list)
    changes: List[TemporalChangeItem] = Field(default_factory=list)
    spatial_findings: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_rating: str  # "High", "Moderate", "Uncertain"
    evidence_path: Optional[str] = None
    evidence_filename: Optional[str] = None
    observed_evidence: Optional[str] = None
    model_interpretation: Optional[str] = None
    raw_model_metrics: Dict[str, Any] = Field(default_factory=dict)

    def to_analysis_dict(self) -> Dict[str, Any]:
        """Converts structured findings to standard dictionary format for API responses and database storage."""
        data = self.model_dump()
        data["answer"] = self.summary
        data["confidence"] = self.confidence_rating
        if self.executive_narrative and not data.get("model_interpretation"):
            data["model_interpretation"] = self.executive_narrative
        return data

class BaseEOModel(ABC):
    """Abstract interface for all Earth Observation AI model adapters."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the canonical model name and version."""
        pass

    @abstractmethod
    def get_device(self) -> str:
        """Returns the hardware execution device (cuda:0 or cpu)."""
        pass

class AIProvider(ABC):
    """
    Abstract interface for multimodal Earth Observation AI providers.
    Ensures the application is completely decoupled from any single API or local library.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the canonical name of the AI provider (e.g. 'Google Gemini API')."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the specific model identifier (e.g. 'gemini-2.5-flash')."""
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_path: str,
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        satellite_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """Executes multimodal visual reasoning, Q&A, scene understanding, and spatial grounding on a single image."""
        pass

    @abstractmethod
    async def analyze_temporal_pair(
        self,
        before_image_path: str,
        after_image_path: str,
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        temporal_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """Executes comparative temporal reasoning on baseline and target rasters."""
        pass

    @abstractmethod
    async def analyze_multimodal_optical_sar(
        self,
        optical_image_path: str,
        sar_image_path: Optional[str],
        query: str,
        aoi_metadata: Optional[Dict[str, Any]] = None,
        sensor_metadata: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> StructuredAIFindings:
        """Executes cross-modal reasoning combining optical and genuine radar (SAR) rasters."""
        pass
