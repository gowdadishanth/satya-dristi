import os
import gc
import psutil
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ModelResourceManager:
    """Manages memory-aware model loading, device selection, and GPU telemetry for GTX 1650 / CPU."""

    def __init__(self):
        self._loaded_models: Dict[str, Any] = {}
        self.device = self._detect_optimal_device()

    def _detect_optimal_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                total_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
                logger.info("CUDA detected: %s with %.1f MiB VRAM", name, total_mb)
                return "cuda:0"
        except Exception as e:
            logger.warning("GPU detection note: %s", e)
        return "cpu"

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Returns real live hardware telemetry: GPU, VRAM, CPU, and RAM."""
        gpu_available = False
        gpu_name = "N/A"
        vram_total_mb = 0
        vram_alloc_mb = 0
        vram_free_mb = 0
        cuda_version = "None"

        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                vram_total_mb = round(props.total_memory / (1024 * 1024), 1)
                alloc_bytes = torch.cuda.memory_allocated(0)
                vram_alloc_mb = round(alloc_bytes / (1024 * 1024), 1)
                vram_free_mb = max(0.0, round(vram_total_mb - vram_alloc_mb, 1))
                cuda_version = getattr(torch.version, "cuda", "Available")
        except Exception as e:
            logger.debug("Telemetry error: %s", e)

        # CPU & RAM
        cpu_pct = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()

        return {
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "vram_total_mb": vram_total_mb,
            "vram_allocated_mb": vram_alloc_mb,
            "vram_free_mb": vram_free_mb,
            "cuda_version": cuda_version,
            "preferred_device": self.device,
            "cpu_usage_pct": cpu_pct,
            "ram_total_mb": round(ram.total / (1024 * 1024), 1),
            "ram_available_mb": round(ram.available / (1024 * 1024), 1),
            "loaded_models": list(self._loaded_models.keys())
        }

    def select_device_for_task(self, estimated_vram_mb: int = 600) -> str:
        """Selects cuda if sufficient VRAM is free, otherwise falls back gracefully to CPU."""
        telemetry = self.get_hardware_telemetry()
        if telemetry["gpu_available"] and telemetry["vram_free_mb"] > estimated_vram_mb:
            return "cuda:0"
        return "cpu"

    def register_model(self, key: str, model_instance: Any):
        self._loaded_models[key] = model_instance

    def get_model(self, key: str) -> Optional[Any]:
        return self._loaded_models.get(key)

    def evict_model(self, key: str):
        if key in self._loaded_models:
            del self._loaded_models[key]
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            logger.info("Evicted model '%s' from memory.", key)

resource_manager = ModelResourceManager()
