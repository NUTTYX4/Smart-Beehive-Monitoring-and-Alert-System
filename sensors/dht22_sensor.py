# -*- coding: utf-8 -*-
"""
sensors/dht22_sensor.py
=========================
DHT22 temperature/humidity sensor with multi-sample median filtering
to reject the occasional bad read the DHT22's one-wire protocol is
prone to.

Uses the actively-maintained `adafruit-circuitpython-dht` library
(imported as `adafruit_dht`) rather than the deprecated `Adafruit_DHT`
package, with a fallback to `Adafruit_DHT` if that is what's installed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from config import DHT22_PIN
from utils.logger import get_logger

logger = get_logger(__name__)

_BACKEND = None
_board = None
_dht_device = None

try:
    import adafruit_dht  # type: ignore
    import board  # type: ignore

    _BACKEND = "adafruit_dht"
    _board = board
except ImportError:
    try:
        import Adafruit_DHT  # type: ignore

        _BACKEND = "Adafruit_DHT"
    except ImportError:  # pragma: no cover
        _BACKEND = None


@dataclass
class ClimateReading:
    temperature_c: float
    humidity_pct: float


class Dht22Sensor:
    """DHT22 wrapper providing a robust, outlier-resistant read."""

    def __init__(self, pin: int = DHT22_PIN) -> None:
        self._pin = pin
        self._device = None
        if _BACKEND == "adafruit_dht":
            try:
                gpio_pin = getattr(_board, f"D{pin}")
                self._device = adafruit_dht.DHT22(gpio_pin, use_pulseio=False)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to initialize adafruit_dht DHT22: %s", exc)
        elif _BACKEND is None:
            logger.warning("No DHT22 library available; readings will be 0.0")

    def _read_once(self) -> Tuple[Optional[float], Optional[float]]:
        if _BACKEND == "adafruit_dht" and self._device is not None:
            try:
                return self._device.temperature, self._device.humidity
            except RuntimeError as exc:
                # DHT22 one-wire glitches are common and expected; log at debug.
                logger.debug("DHT22 transient read error: %s", exc)
                return None, None
            except Exception as exc:  # noqa: BLE001
                logger.warning("DHT22 read failed: %s", exc)
                return None, None
        elif _BACKEND == "Adafruit_DHT":
            try:
                import Adafruit_DHT  # type: ignore

                humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self._pin)
                return temperature, humidity
            except Exception as exc:  # noqa: BLE001
                logger.warning("DHT22 (legacy backend) read failed: %s", exc)
                return None, None
        return None, None

    def read_median(self, samples: int = 3, delay_s: float = 0.2) -> ClimateReading:
        """Take several readings and return the median, discarding
        failed samples. Falls back to 0.0/0.0 if all samples fail."""
        temps: List[float] = []
        hums: List[float] = []
        for _ in range(samples):
            temp, hum = self._read_once()
            if temp is not None and hum is not None:
                temps.append(temp)
                hums.append(hum)
            time.sleep(delay_s)

        temperature = float(np.median(temps)) if temps else 0.0
        humidity = float(np.median(hums)) if hums else 0.0
        return ClimateReading(temperature_c=round(temperature, 2), humidity_pct=round(humidity, 2))
