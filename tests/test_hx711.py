# -*- coding: utf-8 -*-
"""Unit tests for sensors/hx711_sensor.py.

These tests avoid real hardware entirely by monkeypatching the
internal `_hx` handle with a fake object, so they run on any machine
(CI, laptop) without a Raspberry Pi or HX711 attached.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from sensors.hx711_sensor import HX711Sensor
from utils.calibration import load_calibration, save_calibration


class FakeHX711:
    """Minimal stand-in for the `hx711.HX711` class."""

    def __init__(self) -> None:
        self.ratio = 1.0
        self.offset = 0.0
        self._weight_values = [100.0]

    def reset(self) -> None:
        pass

    def zero(self) -> None:
        self.offset = 12345.6

    def set_offset(self, offset: float) -> None:
        self.offset = offset

    def get_offset(self) -> float:
        return self.offset

    def set_scale_ratio(self, ratio: float) -> None:
        self.ratio = ratio

    def get_weight_mean(self, samples: int) -> float:
        return self._weight_values[0]

    def get_value_mean(self, samples: int) -> float:
        return 50000.0


class TestHX711Sensor(unittest.TestCase):
    def setUp(self) -> None:
        self.sensor = HX711Sensor.__new__(HX711Sensor)  # bypass __init__ hardware probing
        self.sensor._notify = MagicMock()
        self.sensor._hx = FakeHX711()

    def test_read_weight_robust_returns_zero_without_hardware(self) -> None:
        sensor = HX711Sensor.__new__(HX711Sensor)
        sensor._hx = None
        self.assertEqual(sensor.read_weight_robust(), 0.0)

    def test_read_weight_robust_clamps_and_rounds(self) -> None:
        self.sensor._hx._weight_values = [10000.0]  # far above WEIGHT_MAX_VALID
        weight = self.sensor.read_weight_robust(samples=5)
        self.assertLessEqual(weight, 5000.0)

    def test_read_weight_robust_normal_range(self) -> None:
        self.sensor._hx._weight_values = [212.34]
        weight = self.sensor.read_weight_robust(samples=5)
        self.assertAlmostEqual(weight, 212.34, places=2)

    def test_perform_tare_and_apply_saved_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cal_file = Path(tmpdir) / "test_calibration.json"

            def test_load():
                return load_calibration(path=tmp_cal_file)

            def test_save(weight_g, scale_ratio, owner_name="System", owner_id=None, offset=0.0, path=None):
                return save_calibration(weight_g, scale_ratio, owner_name, owner_id, offset, path=tmp_cal_file)

            with patch("sensors.hx711_sensor.load_calibration", side_effect=test_load), \
                 patch("sensors.hx711_sensor.save_calibration", side_effect=test_save):

                # Perform tare should zero hardware and save offset
                cal_data = self.sensor.perform_tare("TestUser", 123)
                self.assertAlmostEqual(cal_data.offset, 12345.6)
                self.assertAlmostEqual(self.sensor._hx.offset, 12345.6)

                # Verify disk content via test_load
                loaded = test_load()
                self.assertAlmostEqual(loaded.offset, 12345.6)
                self.assertEqual(loaded.owner_name, "TestUser")

                # Modify hardware offset and verify apply_saved_calibration restores it
                self.sensor._hx.offset = 0.0
                applied_cal = self.sensor.apply_saved_calibration()
                self.assertAlmostEqual(self.sensor._hx.offset, 12345.6)
                self.assertAlmostEqual(applied_cal.offset, 12345.6)


if __name__ == "__main__":
    unittest.main()
