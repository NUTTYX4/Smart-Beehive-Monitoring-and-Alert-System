# -*- coding: utf-8 -*-
"""
sensors/inmp441_sensor.py
============================
High-level sensor facade around the INMP441 I2S microphone: captures
audio via `audio.capture.Inmp441Capture` and returns the dominant bee
frequency via `audio.fft.analyze`. This is the module `monitor.py`
talks to, keeping the acoustic pipeline internals in `audio/`.
"""

from __future__ import annotations

from dataclasses import dataclass

from audio.capture import Inmp441Capture, MicrophoneUnavailableError
from audio.fft import FrequencyResult, analyze
from config import INMP441_CAPTURE_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AcousticReading:
    dominant_freq_hz: float
    sample_rate_hz: float
    silent: bool
    available: bool


class Inmp441Sensor:
    """Facade combining capture + FFT, with graceful degradation if the
    microphone is disconnected or PortAudio is unavailable."""

    def __init__(self) -> None:
        self._capture = Inmp441Capture()

    def read(self, duration_s: float = INMP441_CAPTURE_SECONDS) -> AcousticReading:
        try:
            samples = self._capture.capture(duration_s=duration_s)
        except MicrophoneUnavailableError as exc:
            logger.warning("INMP441 unavailable this cycle: %s", exc)
            return AcousticReading(0.0, 0.0, silent=True, available=False)

        result: FrequencyResult = analyze(samples, self._capture.sample_rate)
        return AcousticReading(
            dominant_freq_hz=result.dominant_freq_hz,
            sample_rate_hz=result.sample_rate_hz,
            silent=result.is_silent,
            available=True,
        )

    def is_connected(self) -> bool:
        return self._capture.is_available()
