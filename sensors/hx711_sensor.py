# -*- coding: utf-8 -*-
"""
sensors/hx711_sensor.py
=========================
HX711 load-cell weight sensor with accurate calibration, stability
detection, outlier-rejected weight reads, and automatic calibration
persistence/recovery.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from config import (
    CALIBRATION_MAX_ITERATIONS,
    CALIBRATION_TOLERANCE,
    HX711_DOUT_PIN,
    HX711_SCK_PIN,
    STABILITY_WINDOW_S,
    WEIGHT_MAX_VALID,
    WEIGHT_MIN_VALID,
)
from utils.calibration import CalibrationData, load_calibration, save_calibration
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import RPi.GPIO as GPIO
    from hx711 import HX711
except ImportError:  # pragma: no cover - hardware library absent on dev machines
    GPIO = None  # type: ignore[assignment]
    HX711 = None  # type: ignore[assignment,misc]


class HX711Sensor:
    """Wraps the `hx711` library, adding robust weight reads and a
    guided, iterative calibration routine that persists results."""

    def __init__(
        self,
        dout_pin: int = HX711_DOUT_PIN,
        sck_pin: int = HX711_SCK_PIN,
        notify=None,
    ) -> None:
        self._notify = notify or (lambda msg: None)
        self._hx = None
        if HX711 is not None and GPIO is not None:
            try:
                GPIO.setmode(GPIO.BCM)
                self._hx = HX711(dout_pin=dout_pin, pd_sck_pin=sck_pin)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to initialize HX711: %s", exc)
        else:
            logger.warning("hx711 library not available; weight readings will be 0.0")

    # ------------------------------------------------------------------
    # Raw helpers
    # ------------------------------------------------------------------
    def _raw_mean(self, samples: int = 7, inner: int = 30) -> float:
        if self._hx is None:
            return 0.0
        vals = []
        for _ in range(samples):
            try:
                if hasattr(self._hx, "get_value_mean"):
                    vals.append(self._hx.get_value_mean(inner))
                elif hasattr(self._hx, "get_raw_data_mean"):
                    vals.append(self._hx.get_raw_data_mean(inner))
                elif hasattr(self._hx, "read_average"):
                    vals.append(self._hx.read_average(inner))
                else:
                    vals.append(self._hx.get_weight_mean(inner))
            except Exception as exc:  # noqa: BLE001
                logger.debug("HX711 raw read failed: %s", exc)
            time.sleep(0.05)
        return float(np.median(vals)) if vals else 0.0

    def _wait_stable_raw(self, seconds: float = STABILITY_WINDOW_S, inner: int = 20) -> Tuple[float, float]:
        buf = []
        t0 = time.time()
        while time.time() - t0 < seconds:
            buf.append(self._raw_mean(samples=1, inner=inner))
            time.sleep(0.05)
        if not buf:
            return 0.0, float("inf")
        arr = np.array(buf, dtype=float)
        return float(np.median(arr)), float(np.std(arr))

    def read_weight_robust(self, samples: int = 15) -> float:
        """Outlier-rejected, clamped weight read in grams."""
        if self._hx is None:
            return 0.0
        vals = []
        for _ in range(samples):
            try:
                vals.append(self._hx.get_weight_mean(10))
            except Exception as exc:  # noqa: BLE001
                logger.debug("HX711 weight read failed: %s", exc)
                continue
            time.sleep(0.02)
        if not vals:
            return 0.0
        arr = np.array(vals, dtype=float)
        low, high = np.percentile(arr, [10, 90])
        trimmed = arr[(arr >= low) & (arr <= high)]
        if trimmed.size == 0:
            trimmed = arr
        weight = float(np.median(trimmed))
        weight = max(min(weight, WEIGHT_MAX_VALID), WEIGHT_MIN_VALID)
        return round(weight, 2)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    def calibrate(
        self,
        target_weight_g: float,
        owner_name: str = "System",
        owner_id: Optional[int] = None,
    ) -> CalibrationData:
        """Guided calibration:
        1. Tare / reset.
        2. Sample an empty-scale baseline window.
        3. Prompt for the known weight, sample a with-weight window.
        4. Compute ratio = raw_delta / target, auto sign-flip if needed.
        5. Iteratively refine toward the target within tolerance.
        6. Persist and return the resulting CalibrationData.
        """
        if self._hx is None:
            logger.error("Cannot calibrate: HX711 hardware not initialized")
            cal = CalibrationData(weight_g=target_weight_g, scale_ratio=1.0,
                                   owner_name=owner_name, owner_id=owner_id)
            save_calibration(cal.weight_g, cal.scale_ratio, owner_name, owner_id)
            return cal

        self._hx.reset()
        self._hx.zero()
        time.sleep(0.8)

        self._notify("⚙️ Calibration: keep scale empty for 3s...")
        time.sleep(3.0)

        self._notify(f"⚖️ Place calibration weight `{target_weight_g} g` now. Waiting {int(STABILITY_WINDOW_S) + 5}s...")
        time.sleep(STABILITY_WINDOW_S + 5.0)

        baseline_med, _ = self._wait_stable_raw(seconds=STABILITY_WINDOW_S, inner=25)
        weight_med, _ = self._wait_stable_raw(seconds=STABILITY_WINDOW_S, inner=25)

        delta = weight_med - baseline_med
        if abs(delta) < 1e-6:
            delta = 1.0
        ratio = delta / float(target_weight_g)

        self._hx.set_scale_ratio(ratio)
        test_weight = self.read_weight_robust(samples=15)

        if test_weight < 0:
            ratio = -ratio
            self._hx.set_scale_ratio(ratio)
            test_weight = self.read_weight_robust(samples=15)

        target = float(target_weight_g)
        for _ in range(CALIBRATION_MAX_ITERATIONS):
            err = abs(test_weight - target) / max(target, 1e-6)
            if err <= CALIBRATION_TOLERANCE:
                break
            ratio = ratio * (test_weight / target) if test_weight != 0 else ratio
            self._hx.set_scale_ratio(ratio)
            time.sleep(0.2)
            test_weight = self.read_weight_robust(samples=15)

        save_calibration(target_weight_g, ratio, owner_name, owner_id)

        badge = "✅ SUCCESS" if abs(test_weight - target) <= 0.05 * target else "⚠️ CHECK"
        self._notify(
            f"{badge}\nCalibration Done\nRatio: `{ratio:.6f}`\n"
            f"Check Weight: {test_weight:.2f} g (target {target:.2f} g)"
        )
        return CalibrationData(
            weight_g=target_weight_g, scale_ratio=ratio, owner_name=owner_name, owner_id=owner_id
        )

    def apply_saved_calibration(self) -> CalibrationData:
        """Load and apply calibration persisted from a previous run
        (used to recover automatically after a reboot)."""
        cal = load_calibration()
        if self._hx is not None:
            try:
                self._hx.set_scale_ratio(cal.scale_ratio)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to apply saved calibration ratio: %s", exc)
        return cal
