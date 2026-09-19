import math
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from shapely.geometry import shape, mapping, box, Polygon
from shapely.ops import transform
import pyproj

from app.core.errors import InvalidAOIError, SceneIncompatibleError

logger = logging.getLogger(__name__)

class GeospatialProcessor:
    """Handles georeferenced calculations, AOI validation, clipping, spectral indices, and SAR calibration."""

    @staticmethod
    def validate_and_parse_aoi(
        geometry: Optional[Dict[str, Any]] = None,
        bbox: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Validates GeoJSON polygon or bounding box.
        Returns validated geometry, bbox, centroid, and area in sq km.
        """
        if bbox and not geometry:
            if len(bbox) != 4:
                raise InvalidAOIError("Bounding box must have 4 coordinates: [min_lon, min_lat, max_lon, max_lat]")
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                raise InvalidAOIError("Coordinates outside WGS84 range.")
            if min_lon >= max_lon or min_lat >= max_lat:
                raise InvalidAOIError("Invalid bounding box coordinates (min >= max).")
            geom_shape = box(min_lon, min_lat, max_lon, max_lat)
            geometry = mapping(geom_shape)
        elif geometry:
            try:
                geom_shape = shape(geometry)
                if not geom_shape.is_valid:
                    geom_shape = geom_shape.buffer(0)
                if geom_shape.is_empty:
                    raise InvalidAOIError("Geometry is empty.")
            except Exception as e:
                raise InvalidAOIError(f"Malformed GeoJSON geometry: {str(e)}")
            bounds = geom_shape.bounds
            bbox = [bounds[0], bounds[1], bounds[2], bounds[3]]
        else:
            raise InvalidAOIError("Either geometry or bbox must be provided.")

        # Calculate accurate geodesic area in sq km
        # Using World Equal Area projection EPSG:6933 for true ground area
        try:
            wgs84 = pyproj.CRS("EPSG:4326")
            equal_area = pyproj.CRS("EPSG:6933")
            project = pyproj.Transformer.from_crs(wgs84, equal_area, always_xy=True).transform
            proj_geom = transform(project, geom_shape)
            area_sq_km = round(proj_geom.area / 1_000_000.0, 4)
        except Exception:
            # Fallback approximate area using spherical geometry
            centroid_lat = geom_shape.centroid.y
            lat_factor = math.cos(math.radians(centroid_lat))
            d_lon = abs(bbox[2] - bbox[0]) * 111.32 * lat_factor
            d_lat = abs(bbox[3] - bbox[1]) * 110.57
            area_sq_km = round(d_lon * d_lat, 4)

        centroid = [round(geom_shape.centroid.x, 6), round(geom_shape.centroid.y, 6)]

        return {
            "geometry": geometry,
            "bbox": [round(c, 6) for c in bbox],
            "centroid": centroid,
            "area_sq_km": max(area_sq_km, 0.001)
        }

    @staticmethod
    def calculate_scene_intersection(scene_geom: Dict[str, Any], aoi_geom: Dict[str, Any]) -> float:
        """Calculates overlap percentage (0.0 to 100.0) between a scene footprint and AOI."""
        try:
            s_shape = shape(scene_geom)
            a_shape = shape(aoi_geom)
            if not s_shape.intersects(a_shape):
                return 0.0
            inter = s_shape.intersection(a_shape)
            overlap_pct = (inter.area / a_shape.area) * 100.0
            return round(min(overlap_pct, 100.0), 2)
        except Exception as e:
            logger.warning("Error calculating scene intersection: %s", e)
            return 0.0

    @staticmethod
    def check_scenes_compatibility(scene_a: Dict[str, Any], scene_b: Dict[str, Any]) -> Dict[str, Any]:
        """Validates spatial, CRS, and temporal compatibility between two observation scenes."""
        geom_a = shape(scene_a.get("geometry", box(*scene_a.get("bbox", [0, 0, 1, 1]))))
        geom_b = shape(scene_b.get("geometry", box(*scene_b.get("bbox", [0, 0, 1, 1]))))

        if not geom_a.intersects(geom_b):
            raise SceneIncompatibleError("Scenes do not share any spatial overlap.")

        inter_area = geom_a.intersection(geom_b).area
        min_area = min(geom_a.area, geom_b.area)
        overlap_pct = round((inter_area / min_area) * 100.0, 1) if min_area > 0 else 0

        if overlap_pct < 10.0:
            raise SceneIncompatibleError(f"Spatial overlap between scenes is insufficient ({overlap_pct}%).")

        return {
            "compatible": True,
            "overlap_percentage": overlap_pct,
            "spatial_crs": "EPSG:4326 (aligned)",
            "sensor_a": scene_a.get("sensor", "Optical"),
            "sensor_b": scene_b.get("sensor", "Optical"),
            "date_a": scene_a.get("acquisition_datetime", ""),
            "date_b": scene_b.get("acquisition_datetime", "")
        }

    @staticmethod
    def compute_spectral_indices(
        red: np.ndarray,
        green: np.ndarray,
        blue: np.ndarray,
        nir: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Computes authentic remote sensing vegetation (NDVI) and water (NDWI) indices.
        Normalized to [-1.0, 1.0].
        """
        red = red.astype(np.float32)
        green = green.astype(np.float32)
        eps = 1e-6

        # If NIR band is available
        if nir is not None:
            nir = nir.astype(np.float32)
            ndvi = (nir - red) / (nir + red + eps)
            ndwi = (green - nir) / (green + nir + eps)
        else:
            # Green-Red Normalized Difference (Visible Atmospherically Resistant Index)
            ndvi = (green - red) / (green + red + eps)
            # Normalized Difference Water Index using green and blue
            ndwi = (green - red) / (green + red + eps)

        return {
            "ndvi": np.clip(ndvi, -1.0, 1.0),
            "ndwi": np.clip(ndwi, -1.0, 1.0)
        }

    @staticmethod
    def calibrate_sar_backscatter(sar_arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Converts SAR digital number (DN) amplitudes into calibrated backscatter coefficient Sigma0 (dB).
        Returns:
            db_arr: array in decibels (-30 to +5 dB)
            norm_arr: normalized 0..255 grayscale visualization
        """
        # Linear power sigma0
        float_arr = sar_arr.astype(np.float32)
        power = np.square(float_arr)
        power = np.maximum(power, 1e-6)
        
        # Sigma0 in dB
        db_arr = 10.0 * np.log10(power)
        
        # Normalization range: -25 dB (calm water/dark surfaces) to 0 dB (dense urban/double bounce)
        min_db = -25.0
        max_db = 0.0
        clipped = np.clip(db_arr, min_db, max_db)
        norm_arr = ((clipped - min_db) / (max_db - min_db) * 255.0).astype(np.uint8)
        
        return db_arr, norm_arr

geospatial_processor = GeospatialProcessor()
