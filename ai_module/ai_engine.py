# -*- coding: utf-8 -*-
"""
ai_module/ai_engine.py
=======================
Edge AI acoustic inference engine for the BeeHive Monitor.

Loads a TensorFlow Lite model (``bee_acoustic_model.tflite``) and
classifies a raw audio buffer as **Normal** or **Triggered / Panic**
using 40 Mel-Frequency Cepstral Coefficients (MFCCs) extracted after
a 100–800 Hz SciPy bandpass filter.

Falls back gracefully when the model file or TFLite runtime is absent,
allowing the caller (``Inmp441Sensor``) to revert to the legacy FFT
peak-frequency analyser transparently.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.signal import butter, sosfilt

from config import (
    AI_CONFIDENCE_THRESHOLD,
    AI_MFCC_COEFFICIENTS,
    AI_MODEL_PATH,
    FFT_BAND_HIGH_HZ,
    FFT_BAND_LOW_HZ,
    FFT_NOISE_GATE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TFLite runtime import — prefer the lightweight ``tflite_runtime`` package
# (recommended on Raspberry Pi) but accept the full TensorFlow fallback.
# ---------------------------------------------------------------------------
_Interpreter = None  # type: ignore[assignment]
try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore[no-redef]
except ImportError:
    try:
        from tensorflow.lite import Interpreter as _Interpreter  # type: ignore[no-redef]
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# Librosa import (for MFCC extraction)
# ---------------------------------------------------------------------------
try:
    import librosa  # type: ignore[import-untyped]
except ImportError:
    librosa = None  # type: ignore[assignment]


# ======================================================================
# Bandpass filter utility
# ======================================================================
def bandpass_filter(
    samples: np.ndarray,
    sample_rate: float,
    low_hz: float = FFT_BAND_LOW_HZ,
    high_hz: float = FFT_BAND_HIGH_HZ,
    order: int = 5,
) -> np.ndarray:
    """Apply a Butterworth bandpass filter to isolate bee acoustics."""
    nyquist = sample_rate / 2.0
    low = max(low_hz / nyquist, 1e-5)
    high = min(high_hz / nyquist, 1.0 - 1e-5)
    sos = butter(order, [low, high], btype="band", output="sos")
    return sosfilt(sos, samples).astype(np.float32)


# ======================================================================
# MFCC extraction utility
# ======================================================================
def extract_mfcc(
    samples: np.ndarray,
    sample_rate: float,
    n_mfcc: int = AI_MFCC_COEFFICIENTS,
) -> np.ndarray:
    """Compute mean MFCCs across time for a mono audio buffer.

    Returns a 1-D array of shape ``(n_mfcc,)``.
    """
    if librosa is None:
        raise RuntimeError("librosa is not installed — cannot extract MFCCs")

    audio = samples.astype(np.float32)
    mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=n_mfcc)
    return np.mean(mfccs, axis=1).astype(np.float32)  # (n_mfcc,)


# ======================================================================
# AIAcousticEngine
# ======================================================================
class AIAcousticEngine:
    """TFLite inference wrapper for bee acoustic classification.

    If the model file is missing, or the TFLite runtime / librosa are
    not installed, construction succeeds but ``available`` is ``False``
    and every call to ``predict_acoustic_state`` will raise
    ``RuntimeError`` so the caller can fall back to legacy FFT.
    """

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self._model_path = Path(model_path or AI_MODEL_PATH)
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self.available = False

        if _Interpreter is None:
            logger.warning("TFLite runtime not installed — AI engine disabled")
            return
        if librosa is None:
            logger.warning("librosa not installed — AI engine disabled")
            return
        if not self._model_path.is_file():
            logger.warning(
                "AI model not found at %s — AI engine disabled (FFT fallback active)",
                self._model_path,
            )
            return

        try:
            self._interpreter = _Interpreter(model_path=str(self._model_path))
            self._interpreter.allocate_tensors()
            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()
            self.available = True
            logger.info("AI acoustic engine loaded: %s", self._model_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load AI model: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def predict_acoustic_state(
        self,
        samples: np.ndarray,
        sample_rate: float,
    ) -> dict:
        """Classify an audio buffer.

        Returns a dict with keys:
            ``behavior``   – human-readable status label
            ``confidence`` – float in [0, 1]
            ``is_silent``  – True when the buffer is below the noise gate
        """
        if not self.available:
            raise RuntimeError("AI engine is not available")

        # ---- Noise gate (same threshold used by the FFT analyser) ----
        peak = float(np.max(np.abs(samples)))
        if peak < FFT_NOISE_GATE:
            return {"behavior": "Silence", "confidence": 1.0, "is_silent": True}

        # ---- Pre-processing ------------------------------------------
        filtered = bandpass_filter(samples, sample_rate)
        mfcc_features = extract_mfcc(filtered, sample_rate)
        input_data = mfcc_features.reshape(1, -1).astype(np.float32)

        # ---- TFLite inference ----------------------------------------
        self._interpreter.set_tensor(self._input_details[0]["index"], input_data)
        self._interpreter.invoke()
        prediction = float(
            self._interpreter.get_tensor(self._output_details[0]["index"])[0][0]
        )

        # ---- Decision ------------------------------------------------
        if prediction > AI_CONFIDENCE_THRESHOLD:
            return {
                "behavior": "⚔️ Triggered / Panic",
                "confidence": prediction,
                "is_silent": False,
            }
        return {
            "behavior": "🟢 Normal / Active",
            "confidence": 1.0 - prediction,
            "is_silent": False,
        }
