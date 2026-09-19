import pytest
from app.services.stac_service import stac_service

@pytest.mark.asyncio
async def test_stac_sentinel2_search():
    # Real Sentinel-2 search for Hyderabad area in 2024
    scenes = await stac_service.search_scenes(
        bbox=[78.4, 17.3, 78.5, 17.4],
        year=2024,
        sensor="optical",
        cloud_cover_max=30.0,
        limit=3
    )
    assert len(scenes) > 0
    s0 = scenes[0]
    assert s0["collection"] == "sentinel-2-l2a"
    assert "sentinel-2" in s0["platform"].lower()
    assert s0["acquisition_datetime"].startswith("2024")
    assert "B04" in s0["available_bands"] or len(s0["available_bands"]) > 0

@pytest.mark.asyncio
async def test_stac_sentinel1_sar_search():
    # Real Sentinel-1 SAR search for Hyderabad area in 2024
    scenes = await stac_service.search_scenes(
        bbox=[78.4, 17.3, 78.5, 17.4],
        year=2024,
        sensor="sar",
        limit=2
    )
    assert len(scenes) > 0
    s0 = scenes[0]
    assert s0["collection"] == "sentinel-1-grd"
    assert "sentinel-1" in s0["platform"].lower()
    assert s0["acquisition_datetime"].startswith("2024")
    assert s0["cloud_cover"] is None # SAR penetrates clouds
