import asyncio
import time

import httpx
from fastapi import APIRouter
from app.core.config import settings
from app.core import db as db_module
from app.models.resource_manager import resource_manager
from app.services.async_queue import job_manager

router = APIRouter(prefix="/system", tags=["System Telemetry"])

_provider_cache: tuple[float, dict[str, str]] | None = None
_PROVIDER_CACHE_TTL_SECONDS = 60


async def _probe_stac(name: str, url: str) -> tuple[str, str]:
    """Return an honest, lightweight availability result for a public STAC API."""
    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            response = await client.get(url)
        return name, "reachable" if response.is_success else f"http_{response.status_code}"
    except httpx.HTTPError:
        return name, "unreachable"


async def _get_provider_statuses() -> dict[str, str]:
    global _provider_cache
    now = time.monotonic()
    if _provider_cache and now - _provider_cache[0] < _PROVIDER_CACHE_TTL_SECONDS:
        return _provider_cache[1]

    checked = await asyncio.gather(
        _probe_stac("copernicus_data_space_stac", settings.COPERNICUS_STAC_URL),
        _probe_stac("aws_earth_search_stac", settings.EARTH_SEARCH_STAC_URL),
    )
    statuses = dict(checked)
    # A Gemini inference call can bill the account, so health checks only report
    # whether the service has been configured, not a fabricated availability result.
    statuses["gemini"] = "configured" if settings.GEMINI_API_KEY else "not_configured"
    _provider_cache = (now, statuses)
    return statuses

@router.get("/health")
async def get_system_health():
    """
    Returns real hardware telemetry, GPU status, VRAM usage, model status, and provider health.
    Never fabricates values.
    """
    hw = resource_manager.get_hardware_telemetry()
    
    # Active jobs count
    active_jobs = sum(1 for j in job_manager._jobs.values() if j.get("status") in ["queued", "running"])
    providers = await _get_provider_statuses()
    gemini_ready = providers["gemini"] == "configured"
    database_status = "firestore" if db_module._firestore_client else "local_sqlite"
    app_status = "operational" if (
        gemini_ready
        and all(
            providers[name] == "reachable"
            for name in ("copernicus_data_space_stac", "aws_earth_search_stac")
        )
    ) else "degraded"

    return {
        "status": app_status,
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
            "vqa_engine": "configured" if gemini_ready else "not_configured",
            "grounding_engine": "configured" if gemini_ready else "not_configured",
            "bi_temporal_change_engine": "configured" if gemini_ready else "not_configured",
            "optical_sar_fusion_engine": "configured" if gemini_ready else "not_configured"
        },
        "providers": providers,
        "database_status": database_status
    }
