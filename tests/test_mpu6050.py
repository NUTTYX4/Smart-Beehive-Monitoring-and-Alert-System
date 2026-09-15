# -*- coding: utf-8 -*-
"""Unit tests for sensors/mpu6050_sensor.py using a fake I2C bus."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import unittest

from sensors.mpu6050_sensor import Mpu6050Sensor


class FakeBus:
    def __init__(self) -> None:
        self.written = []

    def write_byte_data(self, addr, reg, value):
        self.written.append((addr, reg, value))

    def read_byte_data(self, addr, reg):
        return 0x01 if reg % 2 == 0 else 0x00


class TestMpu6050Sensor(unittest.TestCase):
    def setUp(self) -> None:
        self.sensor = Mpu6050Sensor.__new__(Mpu6050Sensor)
        self.sensor._bus_number = 1
        self.sensor._address = 0x68
        self.sensor._bus = FakeBus()

    def test_read_word_decodes_big_endian_pair(self) -> None:
        value = self.sensor._read_word(0x3B)
        self.assertEqual(value, 1)

    def test_read_returns_scaled_imu_reading(self) -> None:
        reading = self.sensor.read()
        self.assertIsInstance(reading.accel_x, float)
        self.assertIsInstance(reading.gyro_z, float)

    def test_read_word_handles_missing_bus_gracefully(self) -> None:
        sensor = Mpu6050Sensor.__new__(Mpu6050Sensor)
        sensor._bus_number = 1
        sensor._address = 0x68
        sensor._bus = None
        sensor._connect = lambda: False
        self.assertEqual(sensor._read_word(0x3B), 0)


if __name__ == "__main__":
    unittest.main()
