# -*- coding: utf-8 -*-
"""
audio/filters.py
==================
Signal-conditioning helpers applied before FFT: DC-offset removal,
windowing, and a noise gate. Kept separate from fft.py so each
concern is independently testable.
"""

from __future__ import annotations

import numpy as np


def remove_dc_offset(samples: np.ndarray) -> np.ndarray:
    """Subtract the mean to remove DC bias from the raw audio buffer."""
    return samples - np.mean(samples)


def apply_window(samples: np.ndarray, window: str = "hann") -> np.ndarray:
    """Apply a windowing function to reduce spectral leakage before FFT."""
    n = len(samples)
    if n == 0:
        return samples
    if window == "hann":
        w = np.hanning(n)
    elif window == "hamming":
        w = np.hamming(n)
    elif window == "blackman":
        w = np.blackman(n)
    else:
        w = np.ones(n)
    return samples * w


def is_silent(samples: np.ndarray, noise_gate: float) -> bool:
    """Return True if the peak amplitude is below the noise gate,
    meaning the buffer is effectively silence/noise and should not be
    analyzed further."""
    if samples.size == 0:
        return True
    return bool(np.max(np.abs(samples)) < noise_gate)


def condition_signal(samples: np.ndarray, window: str = "hann") -> np.ndarray:
    """Full conditioning pipeline: DC removal followed by windowing."""
    return apply_window(remove_dc_offset(samples), window=window)
