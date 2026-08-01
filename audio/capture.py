# -*- coding: utf-8 -*-
"""
audio/capture.py
=================
Continuous audio capture from the INMP441 I2S MEMS microphone via the
Raspberry Pi's native I2S peripheral, exposed to Python through
`sounddevice` (PortAudio). No SPI/ADC hardware (MCP3008, TL072,
ADS1115) is involved -- the INMP441 outputs digital I2S data directly.

Requires `enable_i2s.sh` to have configured `dtoverlay=googlevoicehat-soundcard`
(or an equivalent I2S microphone overlay) in `/boot/firmware/config.txt`
and the device to appear in `arecord -l` / `sounddevice.query_devices()`.
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
except (ImportError, OSError) as exc:
    # ImportError: the `sounddevice` package itself isn't installed.
    # OSError: the package is installed but PortAudio's shared library
    # is missing/unreachable on this system.
    sd = None  # type: ignore[assignment]
    _IMPORT_ERROR: Optional[Exception] = exc
else:
    _IMPORT_ERROR = None

from config import (
    INMP441_BLOCK_SIZE,
    INMP441_CAPTURE_SECONDS,
    INMP441_CHANNELS,
    INMP441_DEVICE,
    INMP441_DTYPE,
    INMP441_SAMPLE_RATE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class MicrophoneUnavailableError(RuntimeError):
    """Raised when the INMP441 / I2S audio backend cannot be reached."""


class Inmp441Capture:
    """Thread-safe wrapper around a `sounddevice` input stream for the
    INMP441 I2S microphone, providing simple blocking captures that the
    monitor loop can call once per cycle without managing PortAudio
    state itself."""

    def __init__(
        self,
        sample_rate: int = INMP441_SAMPLE_RATE,
        channels: int = INMP441_CHANNELS,
        device: str = INMP441_DEVICE,
        dtype: str = INMP441_DTYPE,
        block_size: int = INMP441_BLOCK_SIZE,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device or None
        self.dtype = dtype
        self.block_size = block_size
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None

    def _ensure_backend(self) -> None:
        if sd is None:
            raise MicrophoneUnavailableError(
                f"sounddevice/PortAudio unavailable: {_IMPORT_ERROR}"
            )

    def is_available(self) -> bool:
        """Best-effort check that the I2S microphone can be opened."""
        try:
            self._ensure_backend()
            with self._lock:
                sd.check_input_settings(
                    device=self.device,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    dtype=self.dtype,
                )
            return True
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            logger.warning("INMP441 microphone unavailable: %s", exc)
            return False

    def capture(self, duration_s: float = INMP441_CAPTURE_SECONDS) -> np.ndarray:
        """Blocking capture of `duration_s` seconds of mono float64 audio,
        normalized to roughly [-1, 1]. Raises MicrophoneUnavailableError
        on failure so callers can decide how to degrade gracefully."""
        self._ensure_backend()
        frames = int(duration_s * self.sample_rate)
        with self._lock:
            try:
                recording = sd.rec(
                    frames,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    device=self.device,
                    blocking=True,
                )
            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                raise MicrophoneUnavailableError(f"INMP441 capture failed: {exc}") from exc

        audio = np.asarray(recording, dtype=np.float64)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)  # downmix to mono

        # Normalize by dtype's full-scale range so gain is consistent
        # regardless of the configured sample format.
        if self.dtype == "int32":
            audio /= float(2**31)
        elif self.dtype == "int16":
            audio /= float(2**15)
        # float32/float64 streams are already roughly in [-1, 1].

        return audio

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
