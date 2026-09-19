from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AnalysisCreateRequest(BaseModel):
    mode: str = Field("single", description="'single', 'temporal', or 'fusion'")
    query: str = Field(..., min_length=2, description="Natural language remote-sensing query")
    scene_id: Optional[str] = None
    aoi: Optional[Dict[str, Any]] = None
    before_scene_id: Optional[str] = None
    after_scene_id: Optional[str] = None
    optical_scene_id: Optional[str] = None
    sar_scene_id: Optional[str] = None

class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: str
    current_stage: str
    progress_pct: int
    error: Optional[str] = None

class AnalysisDetailResponse(BaseModel):
    analysis_id: str
    uid: str
    query: str
    task: str
    input: str
    date: str
    time: str
    confidence: str
    confidence_score: Optional[float] = None
    agreements: List[Dict[str, Any]] = []
    status: str
    answer: str
    observed_evidence: Optional[str] = None
    model_interpretation: Optional[str] = None
    model_used: Optional[str] = None
    device_used: Optional[str] = None
    primary_image_path: Optional[str] = None
    before_image_path: Optional[str] = None
    sar_image_path: Optional[str] = None
    evidence_path: Optional[str] = None
    boxes: List[Dict[str, Any]] = []
    aoi: Optional[Dict[str, Any]] = None
    execution_trace: List[Dict[str, Any]] = []
    created_at: str
    completed_at: Optional[str] = None
