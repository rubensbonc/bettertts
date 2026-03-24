import subprocess
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Get the real app directory whether running frozen (PyInstaller) or as a script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def _detect_gpu_name_powershell() -> str:
    """Use PowerShell to get the GPU name (works on modern Windows 10/11)."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command",
                "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            capture_output=True, text=True, timeout=15,
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        # Return the most relevant GPU (prefer NVIDIA > AMD > Intel > first)
        for line in lines:
            if "nvidia" in line.lower() or "geforce" in line.lower():
                return line
        for line in lines:
            if "radeon" in line.lower() or "amd" in line.lower():
                return line
        for line in lines:
            if "intel" in line.lower() and "arc" in line.lower():
                return line
        return lines[0] if lines else "Unknown"
    except Exception:
        return "Unknown"


def _read_gpu_type_file() -> str:
    """Read the GPU type saved by setup."""
    gpu_file = get_base_dir() / ".gpu_type"
    if gpu_file.exists():
        return gpu_file.read_text().strip().lower()
    return ""


def _get_vram_gb(props) -> float:
    """Safely get VRAM from CUDA device properties (attribute name varies by PyTorch version)."""
    for attr in ("total_memory", "total_mem"):
        val = getattr(props, attr, None)
        if val is not None:
            return round(val / (1024 ** 3), 1)
    return 0.0


def get_gpu_info() -> dict:
    """
    Detect GPU availability across all backends: CUDA (NVIDIA), DirectML (AMD/Intel), or CPU.
    Returns a dict with: available, name, vram_gb, backend, backend_version.
    """
    # Try CUDA first (NVIDIA)
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "available": True,
                "name": props.name,
                "vram_gb": _get_vram_gb(props),
                "backend": "CUDA",
                "backend_version": torch.version.cuda or "Unknown",
            }
    except Exception:
        pass

    # Try DirectML (AMD / Intel Arc)
    try:
        import torch_directml
        gpu_name = _detect_gpu_name_powershell()
        return {
            "available": True,
            "name": gpu_name,
            "vram_gb": 0.0,
            "backend": "DirectML",
            "backend_version": getattr(torch_directml, "__version__", "Unknown"),
        }
    except Exception:
        pass

    # CPU fallback — still detect GPU name so the user knows what they have
    gpu_name = _detect_gpu_name_powershell()
    saved_type = _read_gpu_type_file()

    # If setup detected NVIDIA but torch.cuda isn't available,
    # show the GPU name but note CUDA isn't working
    backend_note = "CPU"
    if saved_type == "nvidia" and gpu_name != "Unknown":
        backend_note = "CPU (CUDA unavailable — try re-running setup)"

    return {
        "available": False,
        "name": gpu_name if gpu_name != "Unknown" else "None",
        "vram_gb": 0.0,
        "backend": backend_note,
        "backend_version": "N/A",
    }


def get_torch_device() -> str:
    """Get the best available torch device string."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:
        pass

    try:
        import torch_directml
        return str(torch_directml.device())
    except Exception:
        pass

    return "cpu"