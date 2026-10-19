import math
import numpy as np
from model.ideal_adc import LSB


def static_metrics(transition_v):
    t = np.asarray(transition_v, dtype=float)
    if t.shape != (255,) or not np.all(np.isfinite(t)):
        raise ValueError("Supply 255 finite transition estimates")
    # Endpoint fit uses transition 1 and transition 255. Rail-code widths excluded.
    fitted_lsb = (t[-1] - t[0]) / 254
    if fitted_lsb <= 0:
        raise ValueError("Transition span must be positive")
    ideal_fit = t[0] + np.arange(255) * fitted_lsb
    dnl = np.diff(t) / fitted_lsb - 1
    inl = (t - ideal_fit) / fitted_lsb
    return dict(dnl_lsb=dnl.tolist(), inl_lsb=inl.tolist(),
                max_abs_dnl_lsb=float(np.max(np.abs(dnl))),
                max_abs_inl_lsb=float(np.max(np.abs(inl))),
                missing_interior_codes=int(np.sum(np.diff(t) <= 0)),
                monotonic=bool(np.all(np.diff(t) > 0)),
                offset_lsb=float((t[0] - (-.5 + LSB)) / LSB),
                gain_error_percent=float(100 * (fitted_lsb / LSB - 1)),
                fitted_lsb_v=float(fitted_lsb),
                convention="Signed DNL of 254 interior widths; endpoint INL over 255 transitions; rail widths excluded")


def spectral_metrics(values, sample_rate_hz, fundamental_bin, amplitude_dbfs=-.5):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 32 or not np.all(np.isfinite(x)):
        raise ValueError("Supply a finite uniform sample record")
    n = len(x)
    k = int(fundamental_bin)
    if not 0 < k < n // 2:
        raise ValueError("Fundamental bin must be inside Nyquist")
    p = np.abs(np.fft.rfft(x - np.mean(x))) ** 2
    p[1:-1] *= 2
    p /= n * n
    signal = p[k]
    harmonic_bins = set()
    for h in range(2, 6):
        b = (h * k) % n
        b = min(b, n - b)
        if b not in (0, k):
            harmonic_bins.add(b)
    distortion = float(sum(p[b] for b in harmonic_bins))
    noise_distortion = max(float(np.sum(p[1:]) - signal), 1e-300)
    noise = max(noise_distortion - distortion, 1e-300)
    spurs = p.copy();spurs[0] = 0;spurs[k] = 0
    def ratio(a, b):
        return float(10 * math.log10(max(float(a), 1e-300) / max(float(b), 1e-300)))
    sinad = ratio(signal, noise_distortion)
    return dict(snr_db=ratio(signal, noise), sinad_db=sinad,
                thd_db=ratio(distortion, signal), sfdr_db=ratio(signal, np.max(spurs)),
                enob=(sinad - 1.76) / 6.02, input_dbfs=amplitude_dbfs,
                amplitude_corrected_enob=(sinad - amplitude_dbfs - 1.76) / 6.02,
                samples=n, sample_rate_hz=sample_rate_hz,
                input_hz=k * sample_rate_hz / n, fundamental_bin=k,
                harmonic_bins=sorted(harmonic_bins), window="rectangular; coherent sampling required",
                spectrum_dbfs=(10 * np.log10(np.maximum(p / .125, 1e-30))).tolist())
