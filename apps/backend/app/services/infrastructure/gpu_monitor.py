"""GPU monitoring utilities."""

from __future__ import annotations

import re
import subprocess


def probe_gpu() -> dict:
    """Return basic GPU availability and memory stats.

    Uses nvidia-smi when present. Returns a stable dict shape even if unavailable.
    """
    base = {
        "available": False,
        "name": None,
        "driver_version": None,
        "cuda_version": None,
        "memory_total_mib": None,
        "memory_used_mib": None,
        "utilization_gpu_percent": None,
    }
    try:
        query = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        line = query.stdout.strip().splitlines()[0]
        name, driver, memory_total, memory_used, utilization = [piece.strip() for piece in line.split(",")]
        version_line = subprocess.run(
            ["nvidia-smi"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout
        match = re.search(r"CUDA Version:\s*([0-9.]+)", version_line)
        return {
            "available": True,
            "name": name,
            "driver_version": driver,
            "cuda_version": match.group(1) if match else None,
            "memory_total_mib": int(float(memory_total)),
            "memory_used_mib": int(float(memory_used)),
            "utilization_gpu_percent": int(float(utilization)),
        }
    except (subprocess.SubprocessError, FileNotFoundError, IndexError, ValueError):
        return base


def gpu_has_headroom(required_mib: int = 2048) -> bool:
    info = probe_gpu()
    if not info["available"]:
        return False
    total = int(info["memory_total_mib"] or 0)
    used = int(info["memory_used_mib"] or 0)
    return (total - used) >= required_mib
