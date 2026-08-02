# -*- coding: utf-8 -*-
"""
sensors/inmp441_sensor.py
============================
High-level sensor facade around the INMP441 I2S microphone: captures
audio via ``audio.capture.Inmp441Capture``, runs Edge AI inference when
the TFLite model is available, and falls back transparently to the
legacy ``audio.fft.analyze`` FFT peak analyser otherwise.

This is the module ``monitor.py`` talks to, keeping the acoustic
pipeline internals (audio capture, AI, FFT) behind a single ``.read()``
call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from audio.capture import Inmp441Capture, MicrophoneUnavailableError
from audio.fft import FrequencyResult, analyze
from config import INMP441_CAPTURE_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Try to import the AI engine — if it is missing (ai_module/ deleted or
# dependencies not installed), the sensor silently degrades to FFT-only.
# ---------------------------------------------------------------------------
_ai_engine_instance = None  # type: ignore[assignment]
_ai_import_failed = False

try:
    from ai_module.ai_engine import AIAcousticEngine

    _ai_engine_instance = AIAcousticEngine()
    if not _ai_engine_instance.available:
        _ai_engine_instance = None
        logger.info("AI engine not available — using legacy FFT analyser")
except Exception as exc:  # noqa: BLE001
    _ai_import_failed = True
    logger.info("AI module not loaded (%s) — using legacy FFT analyser", exc)


@dataclass
class AcousticReading:
    dominant_freq_hz: float
    sample_rate_hz: float
    silent: bool
    available: bool
    behavior: str = ""
    confidence: float = 0.0


class Inmp441Sensor:
    """Facade combining capture + AI/FFT, with graceful degradation if the
    microphone is disconnected or PortAudio is unavailable."""

    def __init__(self) -> None:
        self._capture = Inmp441Capture()

    def read(self, duration_s: float = INMP441_CAPTURE_SECONDS) -> AcousticReading:
        try:
            samples = self._capture.capture(duration_s=duration_s)
        except MicrophoneUnavailableError as exc:
            logger.warning("INMP441 unavailable this cycle: %s", exc)
            return AcousticReading(
                0.0, 0.0, silent=True, available=False,
                behavior="⚪ Mic Unavailable", confidence=0.0,
            )

        # ------------------------------------------------------------------
        # Primary path: Edge AI inference
        # ------------------------------------------------------------------
        if _ai_engine_instance is not None:
            try:
                ai_result = _ai_engine_instance.predict_acoustic_state(
                    samples, self._capture.sample_rate,
                )

                # Also run FFT to get dominant_freq for telemetry/ThingSpeak
                fft_result: FrequencyResult = analyze(samples, self._capture.sample_rate)

                return AcousticReading(
                    dominant_freq_hz=fft_result.dominant_freq_hz,
                    sample_rate_hz=fft_result.sample_rate_hz,
                    silent=ai_result["is_silent"],
                    available=True,
                    behavior=ai_result["behavior"],
                    confidence=ai_result["confidence"],
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI inference failed, falling back to FFT: %s", exc)

        # ------------------------------------------------------------------
        # Fallback: legacy FFT peak frequency analyser
        # ------------------------------------------------------------------
        result: FrequencyResult = analyze(samples, self._capture.sample_rate)
        return AcousticReading(
            dominant_freq_hz=result.dominant_freq_hz,
            sample_rate_hz=result.sample_rate_hz,
            silent=result.is_silent,
            available=True,
            behavior="",       # empty → monitor.py uses classify_behavior()
            confidence=0.0,
        )

    def is_connected(self) -> bool:
        return self._capture.is_available()
