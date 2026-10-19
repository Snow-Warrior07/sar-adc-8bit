"""Charge-based binary search, independent of the direct quantizer."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Trial:
    bit: int
    trial_code: int
    top_p_v: float
    top_n_v: float
    keep: bool


def top_plates(vdiff, code):
    # 255 weighted units plus one dummy per side. Half-volt reference separation.
    p_charge = sum((1 << bit) * (1.15 if code & (1 << bit) else .65)
                   for bit in range(8)) + .65
    n_charge = sum((1 << bit) * (.65 if code & (1 << bit) else 1.15)
                   for bit in range(8)) + 1.15
    return .9 - (.9 + vdiff / 2) + p_charge / 256, .9 - (.9 - vdiff / 2) + n_charge / 256


def convert(vdiff):
    if not math.isfinite(vdiff):
        raise ValueError("ADC input must be finite")
    code = 0
    trace = []
    for bit in reversed(range(8)):
        trial = code | (1 << bit)
        p, n = top_plates(vdiff, trial)
        # Use the algebraically equivalent exact binary-scaled residual for ties.
        residual = vdiff - (-.5 + trial / 256)
        keep = residual >= 0
        trace.append(Trial(bit, trial, p, n, keep))
        if keep:
            code = trial
    return code, trace
