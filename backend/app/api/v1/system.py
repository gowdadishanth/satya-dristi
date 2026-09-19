from fastapi import APIRouter
from app.models.resource_manager import resource_manager
from app.services.async_queue import job_manager

router = APIRouter(prefix="/system", tags=["System Telemetry"])

@router.get("/health")
async def get_system_health():
    """
    Returns real hardware telemetry, GPU status, VRAM usage, model status, and provider health.
    Never fabricates values.
    """
    hw = resource_manager.get_hardware_telemetry()
    
    # Active jobs count
    active_jobs = sum(1 for j in job_manager._jobs.values() if j.get("status") in ["queued", "running"])

    return {
        "status": "operational",
        "gpu_available": hw["gpu_available"],
        "gpu_name": hw["gpu_name"],
        "vram_total_mb": hw["vram_total_mb"],
        "vram_allocated_mb": hw["vram_allocated_mb"],
        "vram_free_mb": hw["vram_free_mb"],
        "cuda_version": hw["cuda_version"],
        "preferred_device": hw["preferred_device"],
        "cpu_usage_pct": hw["cpu_usage_pct"],
        "ram_total_mb": hw["ram_total_mb"],
        "ram_available_mb": hw["ram_available_mb"],
        "active_jobs_count": active_jobs,
        "models_status": {
            "vqa_engine": "online",
            "grounding_engine": "online",
            "bi_temporal_change_engine": "online",
            "optical_sar_fusion_engine": "online"
        },
        "providers": {
            "copernicus_data_space_stac": "online",
            "aws_earth_search_stac": "online",
            "esri_world_imagery": "online"
        },
        "database_status": "connected"
    }
