#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_mpu6050.py
======================
Live hardware diagnostic for the MPU6050 accelerometer/gyroscope.
Reads real I2C data from address 0x68 and prints it every second.
Accel Z should read ~1.0 g when the Pi is sitting flat.

Wiring (I2C):
    MPU6050 SDA  ->  GPIO 2  (Physical Pin 3)
    MPU6050 SCL  ->  GPIO 3  (Physical Pin 5)
    MPU6050 VCC  ->  3.3V    (Physical Pin 1)
    MPU6050 GND  ->  GND     (Physical Pin 6)
    MPU6050 AD0  ->  GND     (sets I2C address to 0x68)

Run:
    python3 tests/test_mpu6050.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import time
from config import MPU6050_I2C_BUS, MPU6050_ADDR

print("=" * 65)
print("  BeeHive | MPU6050 Accelerometer / Gyroscope Diagnostic")
print(f"  I2C Bus  : {MPU6050_I2C_BUS}")
print(f"  Address  : 0x{MPU6050_ADDR:02X}  (AD0 -> GND = 0x68)")
print("=" * 65)

try:
    import smbus2
    bus = smbus2.SMBus(MPU6050_I2C_BUS)
    # Wake up MPU6050 (write 0 to PWR_MGMT_1 register 0x6B)
    bus.write_byte_data(MPU6050_ADDR, 0x6B, 0)
    time.sleep(0.1)
    print("  smbus2   : OK")
    print(f"  MPU6050  : Detected at 0x{MPU6050_ADDR:02X}  OK")
except ImportError:
    print("  ERROR: smbus2 not installed.  Run:  pip install smbus2")
    sys.exit(1)
except OSError as e:
    print(f"  ERROR: Cannot reach MPU6050 at 0x{MPU6050_ADDR:02X} on bus {MPU6050_I2C_BUS}")
    print(f"  Detail: {e}")
    print("  Troubleshooting:")
    print("    1. Run:  sudo i2cdetect -y 1  (should show 68)")
    print("    2. Check SDA/SCL wiring.")
    print("    3. Run:  sudo raspi-config -> Interface Options -> I2C -> Enable")
    sys.exit(1)

def read_word_signed(reg: int) -> int:
    high = bus.read_byte_data(MPU6050_ADDR, reg)
    low  = bus.read_byte_data(MPU6050_ADDR, reg + 1)
    val  = (high << 8) | low
    return val - 65536 if val >= 32768 else val

print()
print("  Live readings (Ctrl+C to stop)   |   Accel Z should be ~1.0 g when flat")
print()
print(f"  {'#':>4}  {'Ax':>7}  {'Ay':>7}  {'Az':>7}  {'Gx':>8}  {'Gy':>8}  {'Gz':>8}  {'Temp':>7}")
print(f"  {'':>4}  {'(g)':>7}  {'(g)':>7}  {'(g)':>7}  {'(dps)':>8}  {'(dps)':>8}  {'(dps)':>8}  {'(C)':>7}")
print(f"  {'-'*4}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*7}")

ACCEL_SCALE = 16384.0   # ±2g default
GYRO_SCALE  = 131.0     # ±250 dps default

count = 0
try:
    while True:
        count += 1

        ax = read_word_signed(0x3B) / ACCEL_SCALE
        ay = read_word_signed(0x3D) / ACCEL_SCALE
        az = read_word_signed(0x3F) / ACCEL_SCALE
        gx = read_word_signed(0x43) / GYRO_SCALE
        gy = read_word_signed(0x45) / GYRO_SCALE
        gz = read_word_signed(0x47) / GYRO_SCALE
        raw_temp = read_word_signed(0x41)
        temp_c   = raw_temp / 340.0 + 36.53

        # Flag if the hive is tilted
        accel_mag = (ax**2 + ay**2 + az**2) ** 0.5
        status = "OK" if abs(accel_mag - 1.0) < 0.3 else "WARN: Tilt/Shock!"

        print(f"  {count:>4}  {ax:>7.3f}  {ay:>7.3f}  {az:>7.3f}  "
              f"{gx:>8.2f}  {gy:>8.2f}  {gz:>8.2f}  {temp_c:>6.1f}C  {status}")

        time.sleep(1.0)

except KeyboardInterrupt:
    bus.close()
    print()
    print(f"  Stopped after {count} readings.")
    print("=" * 65)
