# -*- coding: utf-8 -*-
"""Unit tests for sensors/hx711_sensor.py.

These tests avoid real hardware entirely by monkeypatching the
internal `_hx` handle with a fake object, so they run on any machine
(CI, laptop) without a Raspberry Pi or HX711 attached.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from sensors.hx711_sensor import HX711Sensor


class FakeHX711:
    """Minimal stand-in for the `hx711.HX711` class."""

    def __init__(self) -> None:
        self.ratio = 1.0
        self._weight_values = [100.0]

    def reset(self) -> None:
        pass

    def zero(self) -> None:
        pass

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


if __name__ == "__main__":
    unittest.main()
