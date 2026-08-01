# -*- coding: utf-8 -*-
"""
sensors/mpu6050_sensor.py
============================
MPU6050 6-axis accelerometer/gyroscope over I2C, with automatic
recovery if the bus is briefly unavailable (e.g. right after boot).
"""

from __future__ import annotations

from dataclasses import dataclass

from config import MPU6050_ADDR, MPU6050_I2C_BUS
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import smbus2 as smbus
except ImportError:
    try:
        import smbus  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        smbus = None  # type: ignore[assignment]

_PWR_MGMT_1 = 0x6B
_ACCEL_XOUT_H = 0x3B
_GYRO_XOUT_H = 0x43
_ACCEL_CONFIG = 0x1C
_GYRO_CONFIG = 0x1B
_ACCEL_SCALE = 16384.0  # LSB/g at +/-2g full scale
_GYRO_SCALE = 131.0  # LSB/(deg/s) at +/-250 dps full scale


@dataclass
class ImuReading:
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float


class Mpu6050Sensor:
    """MPU6050 wrapper that degrades gracefully (returns zeros) when the
    I2C bus or device is unavailable, and retries initialization on
    each read attempt so the sensor recovers automatically once wiring
    or power is restored."""

    def __init__(self, bus_number: int = MPU6050_I2C_BUS, address: int = MPU6050_ADDR) -> None:
        self._bus_number = bus_number
        self._address = address
        self._bus = None
        self._connect()

    def _connect(self) -> bool:
        if smbus is None:
            return False
        try:
            self._bus = smbus.SMBus(self._bus_number)
            self._bus.write_byte_data(self._address, _PWR_MGMT_1, 0)
            self._bus.write_byte_data(self._address, _ACCEL_CONFIG, 0x00)
            self._bus.write_byte_data(self._address, _GYRO_CONFIG, 0x00)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("MPU6050 not reachable on I2C bus %d: %s", self._bus_number, exc)
            self._bus = None
            return False

    def _read_word(self, addr: int) -> int:
        if self._bus is None and not self._connect():
            return 0
        try:
            high = self._bus.read_byte_data(self._address, addr)
            low = self._bus.read_byte_data(self._address, addr + 1)
            value = (high << 8) | low
            if value > 32768:
                value -= 65536
            return value
        except Exception as exc:  # noqa: BLE001
            logger.debug("MPU6050 read failed, will retry connection next cycle: %s", exc)
            self._bus = None
            return 0

    def read(self) -> ImuReading:
        ax = self._read_word(_ACCEL_XOUT_H) / _ACCEL_SCALE
        ay = self._read_word(_ACCEL_XOUT_H + 2) / _ACCEL_SCALE
        az = self._read_word(_ACCEL_XOUT_H + 4) / _ACCEL_SCALE
        gx = self._read_word(_GYRO_XOUT_H) / _GYRO_SCALE
        gy = self._read_word(_GYRO_XOUT_H + 2) / _GYRO_SCALE
        gz = self._read_word(_GYRO_XOUT_H + 4) / _GYRO_SCALE
        return ImuReading(
            accel_x=round(ax, 2), accel_y=round(ay, 2), accel_z=round(az, 2),
            gyro_x=round(gx, 1), gyro_y=round(gy, 1), gyro_z=round(gz, 1),
        )
