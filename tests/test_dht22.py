# -*- coding: utf-8 -*-
"""Unit tests for sensors/dht22_sensor.py using a fake read backend."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from sensors.dht22_sensor import Dht22Sensor


class TestDht22Sensor(unittest.TestCase):
    def setUp(self) -> None:
        self.sensor = Dht22Sensor.__new__(Dht22Sensor)
        self.sensor._pin = 4
        self.sensor._device = None

    def test_read_median_all_failures_returns_zero(self) -> None:
        with patch.object(Dht22Sensor, "_read_once", return_value=(None, None)):
            reading = self.sensor.read_median(samples=3, delay_s=0.0)
        self.assertEqual(reading.temperature_c, 0.0)
        self.assertEqual(reading.humidity_pct, 0.0)

    def test_read_median_computes_median_of_valid_samples(self) -> None:
        values = iter([(20.0, 50.0), (22.0, 52.0), (21.0, 51.0)])
        with patch.object(Dht22Sensor, "_read_once", side_effect=lambda: next(values)):
            reading = self.sensor.read_median(samples=3, delay_s=0.0)
        self.assertAlmostEqual(reading.temperature_c, 21.0, places=1)
        self.assertAlmostEqual(reading.humidity_pct, 51.0, places=1)

    def test_read_median_discards_partial_failures(self) -> None:
        values = iter([(None, None), (24.0, 60.0), (26.0, 62.0)])
        with patch.object(Dht22Sensor, "_read_once", side_effect=lambda: next(values)):
            reading = self.sensor.read_median(samples=3, delay_s=0.0)
        self.assertAlmostEqual(reading.temperature_c, 25.0, places=1)


if __name__ == "__main__":
    unittest.main()
