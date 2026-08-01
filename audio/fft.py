# -*- coding: utf-8 -*-
"""
audio/fft.py
=============
FFT-based dominant frequency detection for bee acoustic monitoring,
using SciPy's real FFT and NumPy for peak detection within the bee
acoustic band (default 100-800 Hz, configurable in config.py).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.fft import rfft, rfftfreq

from audio.filters import condition_signal, is_silent
from config import FFT_BAND_HIGH_HZ, FFT_BAND_LOW_HZ, FFT_NOISE_GATE
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FrequencyResult:
    dominant_freq_hz: float
    sample_rate_hz: float
    is_silent: bool
    peak_magnitude: float


def analyze(
    samples: np.ndarray,
    sample_rate: float,
    band_low: float = FFT_BAND_LOW_HZ,
    band_high: float = FFT_BAND_HIGH_HZ,
    noise_gate: float = FFT_NOISE_GATE,
) -> FrequencyResult:
    """Compute the dominant frequency within [band_low, band_high] Hz
    for a captured audio buffer.

    Returns a FrequencyResult with dominant_freq_hz=0.0 when the signal
    is silent/noise-gated or no energy exists in the target band.
    """
    if samples.size == 0 or sample_rate <= 0:
        return FrequencyResult(0.0, sample_rate, True, 0.0)

    if is_silent(samples, noise_gate):
        return FrequencyResult(0.0, sample_rate, True, 0.0)

    conditioned = condition_signal(samples)
    spectrum = np.abs(rfft(conditioned))
    freqs = rfftfreq(len(conditioned), d=1.0 / sample_rate)

    band_mask = (freqs >= band_low) & (freqs <= band_high)
    if not np.any(band_mask):
        return FrequencyResult(0.0, sample_rate, False, 0.0)

    band_freqs = freqs[band_mask]
    band_spectrum = spectrum[band_mask]
    peak_idx = int(np.argmax(band_spectrum))

    return FrequencyResult(
        dominant_freq_hz=float(band_freqs[peak_idx]),
        sample_rate_hz=float(sample_rate),
        is_silent=False,
        peak_magnitude=float(band_spectrum[peak_idx]),
    )
