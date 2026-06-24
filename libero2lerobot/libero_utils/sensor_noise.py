"""Sensor-noise corruption for the LIBERO-Plus regeneration.

Thin wrapper that REUSES the fork's own blur kernels (do NOT re-implement them). The fork
applies these natively to `agentview_image` only inside `ControlEnv.step`; for the additional
camera set (frontview + sideview) we call the same kernels here so the extra views get an
equivalent corruption.

Severity is 1-50, mirroring `ControlEnv` exactly: ten severity levels per kernel, in bands of
10 -> motion (1-10), gaussian (11-20), zoom (21-30), fog (31-40), glass (41-50).
"""

import numpy as np
from PIL import Image

# Imported from the fork; only available inside the `libero_plus` conda env.
from libero.libero.envs.env_wrapper import (
    fog,
    gaussian_blur,
    glass_blur,
    motion_blur,
    zoom_blur,
)

NUM_SEVERITIES = 50


def apply_noise(img_uint8: np.ndarray, severity: int) -> np.ndarray:
    """Apply one of the five fork blur kernels to an HxWx3 uint8 image.

    `severity` selects the kernel + intensity exactly as `ControlEnv` does (bands of 10).
    Returns a uint8 image of the same shape.
    """
    if not (1 <= severity <= NUM_SEVERITIES):
        raise ValueError(f"severity must be in [1, {NUM_SEVERITIES}], got {severity}")

    pil_image = Image.fromarray(img_uint8)
    if severity <= 10:
        out = motion_blur(pil_image, severity=severity)
    elif severity <= 20:
        out = gaussian_blur(pil_image, severity=severity - 10)
    elif severity <= 30:
        out = zoom_blur(pil_image, severity=severity - 20)
    elif severity <= 40:
        out = fog(pil_image, severity=severity - 30)
    else:
        out = glass_blur(pil_image, severity=severity - 40)

    return np.clip(out, 0, 255).astype(np.uint8)


def kernel_name(severity: int) -> str:
    """Human-readable kernel name for a severity (for provenance logging)."""
    return ["motion", "gaussian", "zoom", "fog", "glass"][(severity - 1) // 10]
