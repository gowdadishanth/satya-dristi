import logging
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

from app.core.config import settings
from app.core.errors import NoSceneFoundError, InvalidLocationError

logger = logging.getLogger(__name__)

class STACService:
    """Queries real public Earth-observation STAC catalogues (Copernicus & Earth Search)."""

    def __init__(self):
        self._scene_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _format_datetime(year: Optional[int], start_date: Optional[str], end_date: Optional[str]) -> str:
        if start_date and end_date:
            s = start_date if "T" in start_date else f"{start_date}T00:00:00Z"
            e = end_date if "T" in end_date else f"{end_date}T23:59:59Z"
            return f"{s}/{e}"
        if year:
            return f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z"
        current_year = datetime.utcnow().year
        return f"{current_year}-01-01T00:00:00Z/{current_year}-12-31T23:59:59Z"

    @staticmethod
    def _normalize_s2_feature(feat: Dict[str, Any], provider: str) -> Dict[str, Any]:
        props = feat.get("properties", {})
        assets = feat.get("assets", {})
        scene_id = feat.get("id", "")
        
        # Resolve full-resolution visual asset URL (COG or high-res TCI)
        visual_url = None
        for key in ["visual", "rendered_preview", "tci", "TCI", "visual-jp2"]:
            if key in assets and assets[key].get("href"):
                href = assets[key]["href"]
                if href.startswith("s3://sentinel-s2-l2a-cogs/"):
                    href = href.replace("s3://sentinel-s2-l2a-cogs/", "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/")
                if href.startswith("http"):
                    visual_url = href
                    break

        # Resolve preview URL (overview or thumbnail)
        preview_url = None
        for key in ["overview", "rendered_preview", "thumbnail", "preview", "visual"]:
            if key in assets and assets[key].get("href"):
                href = assets[key]["href"]
                if href.startswith("s3://sentinel-s2-l2a-cogs/"):
                    href = href.replace("s3://sentinel-s2-l2a-cogs/", "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/")
                if href.startswith("http"):
                    preview_url = href
                    break

        cloud_cover = props.get("eo:cloud_cover") or props.get("cloudCover")
        if cloud_cover is not None:
            cloud_cover = round(float(cloud_cover), 2)

        available_bands = []
        for b in ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12", "TCI"]:
            band_key = next((k for k in assets if b.lower() in k.lower()), None)
            if band_key:
                available_bands.append(b)

        return {
            "scene_id": scene_id,
            "collection": "sentinel-2-l2a",
            "provider": provider,
            "platform": props.get("platform", "Sentinel-2"),
            "instrument": props.get("instruments", ["MSI"])[0] if isinstance(props.get("instruments"), list) else "MSI",
            "sensor": "Multispectral Instrument (MSI)",
            "processing_level": "Level-2A Bottom-Of-Atmosphere (BOA)",
            "acquisition_datetime": props.get("datetime", ""),
            "cloud_cover": cloud_cover,
            "bbox": feat.get("bbox", []),
            "geometry": feat.get("geometry", {}),
            "visual_url": visual_url or preview_url,
            "preview_url": preview_url or visual_url,
            "available_bands": available_bands if available_bands else ["B02", "B03", "B04", "B08", "TCI"],
            "assets": {k: {"href": v.get("href"), "type": v.get("type")} for k, v in assets.items() if v.get("href")}
        }

    @staticmethod
    def _normalize_s1_feature(feat: Dict[str, Any], provider: str) -> Dict[str, Any]:
        props = feat.get("properties", {})
        assets = feat.get("assets", {})
        scene_id = feat.get("id", "")

        visual_url = None
        for key in ["visual", "overview", "preview", "quick-look", "thumbnail"]:
            if key in assets and assets[key].get("href"):
                href = assets[key]["href"]
                if href.startswith("s3://sentinel-s1-l1c/"):
                    href = href.replace("s3://sentinel-s1-l1c/", "https://sentinel-cogs.s3.us-west-2.amazonaws.com/")
                if href.startswith("http"):
                    visual_url = href
                    break

        preview_url = visual_url

        polarizations = props.get("sar:polarizations", ["VV", "VH"])

        return {
            "scene_id": scene_id,
            "collection": "sentinel-1-grd",
            "provider": provider,
            "platform": props.get("platform", "Sentinel-1"),
            "instrument": props.get("instruments", ["C-SAR"])[0] if isinstance(props.get("instruments"), list) else "C-SAR",
            "sensor": "C-band Synthetic Aperture Radar (SAR)",
            "processing_level": "Level-1 Ground Range Detected (GRD)",
            "acquisition_datetime": props.get("datetime", ""),
            "cloud_cover": None,  # SAR is weather and cloud-penetrating
            "bbox": feat.get("bbox", []),
            "geometry": feat.get("geometry", {}),
            "visual_url": visual_url or preview_url,
            "preview_url": preview_url,
            "available_bands": polarizations,
            "assets": {k: {"href": v.get("href"), "type": v.get("type")} for k, v in assets.items() if v.get("href")}
        }

    async def search_scenes(
        self,
        bbox: Optional[List[float]] = None,
        geometry: Optional[Dict[str, Any]] = None,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sensor: str = "optical",
        cloud_cover_max: Optional[float] = 30.0,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Search real public Sentinel-2 (optical) or Sentinel-1 (SAR) scenes from 2016-2026.
        """
        if not bbox and not geometry:
            raise InvalidLocationError("Either bbox or geometry polygon must be provided.")

        datetime_range = self._format_datetime(year, start_date, end_date)
        is_sar = sensor.lower() in ["sar", "sentinel-1", "s1"]
        target_collection = "sentinel-1-grd" if is_sar else "sentinel-2-l2a"

        body: Dict[str, Any] = {
            "collections": [target_collection],
            "datetime": datetime_range,
            "limit": min(limit, 30)
        }
        if bbox:
            body["bbox"] = bbox
        elif geometry:
            body["intersects"] = geometry

        # Add cloud cover filter for optical
        if not is_sar and cloud_cover_max is not None:
            body["query"] = {"eo:cloud_cover": {"lte": cloud_cover_max}}

        scenes: List[Dict[str, Any]] = []

        # 1. Query Earth Search (AWS open data STAC)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.EARTH_SEARCH_STAC_URL}/search",
                    json=body,
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for f in data.get("features", []):
                        if is_sar:
                            scenes.append(self._normalize_s1_feature(f, provider="AWS Open Data"))
                        else:
                            scenes.append(self._normalize_s2_feature(f, provider="AWS Open Data"))
        except Exception as e:
            logger.warning("Earth Search STAC query failed: %s", e)

        # 2. If needed, query Copernicus STAC
        if len(scenes) < 3:
            try:
                cop_body = {
                    "collections": [target_collection],
                    "datetime": datetime_range,
                    "limit": min(limit, 20)
                }
                if bbox:
                    cop_body["bbox"] = bbox
                elif geometry:
                    cop_body["intersects"] = geometry

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{settings.COPERNICUS_STAC_URL}/search",
                        json=cop_body,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for f in data.get("features", []):
                            if not any(s["scene_id"] == f.get("id") for s in scenes):
                                if is_sar:
                                    scenes.append(self._normalize_s1_feature(f, provider="Copernicus Data Space"))
                                else:
                                    scenes.append(self._normalize_s2_feature(f, provider="Copernicus Data Space"))
            except Exception as e:
                logger.warning("Copernicus STAC query error: %s", e)

        if not scenes:
            raise NoSceneFoundError(f"No suitable {target_collection} scenes found for the selected area and date range ({datetime_range}).")

        # Sort by acquisition datetime descending
        scenes.sort(key=lambda s: s.get("acquisition_datetime", ""), reverse=True)
        
        # Cache scenes for instant retrieval
        for s in scenes:
            if s.get("scene_id"):
                self._scene_cache[s["scene_id"]] = s
                
        return scenes[:limit]

    async def get_scene_details(self, scene_id: str) -> Dict[str, Any]:
        """Fetch details for a specific scene by ID."""
        if scene_id in self._scene_cache:
            return self._scene_cache[scene_id]

        is_sar = "s1" in scene_id.lower() or "grd" in scene_id.lower()
        col = "sentinel-1-grd" if is_sar else "sentinel-2-l2a"

        # Query Earth Search by scene ID
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                body = {"ids": [scene_id], "collections": [col]}
                resp = await client.post(f"{settings.EARTH_SEARCH_STAC_URL}/search", json=body)
                if resp.status_code == 200:
                    features = resp.json().get("features", [])
                    if features:
                        f = features[0]
                        sc = self._normalize_s1_feature(f, "AWS Open Data") if is_sar else self._normalize_s2_feature(f, "AWS Open Data")
                        self._scene_cache[scene_id] = sc
                        return sc
        except Exception as e:
            logger.warning("Earth search scene lookup error: %s", e)

        # Fallback to Copernicus
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                body = {"ids": [scene_id], "collections": [col]}
                resp = await client.post(f"{settings.COPERNICUS_STAC_URL}/search", json=body)
                if resp.status_code == 200:
                    features = resp.json().get("features", [])
                    if features:
                        f = features[0]
                        sc = self._normalize_s1_feature(f, "Copernicus Data Space") if is_sar else self._normalize_s2_feature(f, "Copernicus Data Space")
                        self._scene_cache[scene_id] = sc
                        return sc
        except Exception as e:
            logger.warning("Copernicus scene lookup error: %s", e)

        raise NoSceneFoundError(f"Scene with ID '{scene_id}' could not be located in public Earth observation catalogues.")

stac_service = STACService()
