from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, Depends
from app.core.firebase import get_current_user
from app.services.stac_service import stac_service
from app.services.geospatial_processor import geospatial_processor
from app.services.image_retrieval import image_retrieval_service
from app.schemas.earth import (
    SceneSearchRequest, SceneResponse,
    AOIPreviewRequest, AOIPreviewResponse,
    CompatibilityRequest, CompatibilityResponse
)

router = APIRouter(prefix="/earth", tags=["Earth Observation"])

@router.post("/scenes/search", response_model=List[SceneResponse])
async def search_satellite_scenes(
    req: SceneSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search real public Sentinel-2 (optical) or Sentinel-1 (SAR) scenes from 2016 to 2026.
    Uses Copernicus Data Space and AWS Earth Search STAC catalogues.
    """
    return await stac_service.search_scenes(
        bbox=req.bbox,
        geometry=req.geometry,
        year=req.year,
        start_date=req.start_date,
        end_date=req.end_date,
        sensor=req.sensor,
        cloud_cover_max=req.cloud_cover_max,
        limit=req.limit
    )

@router.get("/scenes/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetch complete metadata for a satellite scene by ID."""
    return await stac_service.get_scene_details(scene_id)

@router.post("/aoi/preview", response_model=AOIPreviewResponse)
async def validate_aoi(
    req: AOIPreviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate user-selected Area of Interest (Rectangle, Polygon, or Bounding Box).
    Calculates geographic area in sq km, centroid, and WGS84 bounding coordinates.
    """
    return geospatial_processor.validate_and_parse_aoi(
        geometry=req.geometry,
        bbox=req.bbox
    )

@router.post("/compatibility", response_model=CompatibilityResponse)
async def check_scene_compatibility(
    req: CompatibilityRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validates spatial overlap, coordinate reference system, and temporal alignment between two observation scenes.
    """
    return geospatial_processor.check_scenes_compatibility(
        scene_a=req.scene_a,
        scene_b=req.scene_b
    )

@router.post("/imagery")
async def retrieve_imagery(
    scene_id: str = Query(...),
    treatment: str = Query("optical"),
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves and caches authentic Earth observation imagery for a scene and AOI.
    """
    aoi_bbox = [float(x) for x in bbox.split(",")] if bbox else None
    scene = await stac_service.get_scene_details(scene_id)
    path, meta = await image_retrieval_service.retrieve_scene_image(scene, aoi_bbox=aoi_bbox, treatment=treatment)
    return {
        "scene_id": scene_id,
        "image_path": path,
        "treatment": treatment,
        "metadata": meta
    }
