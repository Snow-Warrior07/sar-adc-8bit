"""Analytical quantizer, deliberately independent of SAR bit sequencing."""
import numpy as np

BITS = 8
LEVELS = 1 << BITS
FS = 1.0
LSB = FS / LEVELS


def quantize(vdiff):
    x = np.asarray(vdiff, dtype=float)
    if not np.all(np.isfinite(x)):
        raise ValueError("ADC input must be finite")
    q = np.clip(np.floor((x + FS / 2) / LSB), 0, LEVELS - 1).astype(int)
    return int(q) if q.ndim == 0 else q


def reconstruct(code):
    q = np.asarray(code)
    if np.any((q < 0) | (q > 255) | (q != np.floor(q))):
        raise ValueError("Code must be an integer from 0 to 255")
    y = -FS / 2 + (q + .5) * LSB
    return float(y) if y.ndim == 0 else y


def transitions():
    return -.5 + np.arange(1, 256) * LSB
