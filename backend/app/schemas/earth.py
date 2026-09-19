from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SceneSearchRequest(BaseModel):
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry polygon")
    year: Optional[int] = Field(None, description="Year (e.g. 2016-2026)")
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD or ISO-8601")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD or ISO-8601")
    sensor: str = Field("optical", description="'optical' (Sentinel-2) or 'sar' (Sentinel-1)")
    cloud_cover_max: Optional[float] = Field(30.0, description="Max cloud cover percentage for optical")
    limit: int = Field(12, ge=1, le=50)

class SceneResponse(BaseModel):
    scene_id: str
    collection: str
    provider: str
    platform: str
    instrument: str
    sensor: str
    processing_level: str
    acquisition_datetime: str
    cloud_cover: Optional[float]
    bbox: List[float]
    geometry: Dict[str, Any]
    preview_url: Optional[str]
    available_bands: List[str]
    assets: Dict[str, Any]

class AOIPreviewRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None

class AOIPreviewResponse(BaseModel):
    geometry: Dict[str, Any]
    bbox: List[float]
    centroid: List[float]
    area_sq_km: float

class CompatibilityRequest(BaseModel):
    scene_a: Dict[str, Any]
    scene_b: Dict[str, Any]

class CompatibilityResponse(BaseModel):
    compatible: bool
    overlap_percentage: float
    spatial_crs: str
    sensor_a: str
    sensor_b: str
    date_a: str
    date_b: str
