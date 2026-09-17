#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_all_sensors.py
===================
Diagnostic script to test all hardware sensors connected to the Raspberry Pi.
Run this via:
  source venv/bin/activate
  python3 test_all_sensors.py
"""

import time
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

print("==================================================")
print("🐝 SMART BEEHIVE SENSOR DIAGNOSTICS")
print("==================================================")
print("Loading drivers... please wait.")

try:
    from sensors.dht22_sensor import Dht22Sensor
    from sensors.hx711_sensor import HX711Sensor
    from sensors.inmp441_sensor import Inmp441Sensor
    from sensors.mpu6050_sensor import Mpu6050Sensor
    from sensors.relay_actuator import RelayActuator
    import cv2
except Exception as e:
    print(f"\n❌ Error loading sensor libraries: {e}")
    sys.exit(1)


# 1. Test DHT22 Climate Sensor
print("\n[1/5] Testing DHT22 (Temperature & Humidity)...")
try:
    dht = Dht22Sensor()
    reading = dht.read_median(samples=3)
    if reading.temperature_c == 0.0 and reading.humidity_pct == 0.0:
        print("  ⚠️ DHT22 returned 0.0. Check wiring (Data pin GPIO 4).")
    else:
        print(f"  ✅ Temp: {reading.temperature_c:.1f} °C, Humidity: {reading.humidity_pct:.1f}%")
except Exception as e:
    print(f"  ❌ DHT22 Error: {e}")


# 2. Test HX711 Scale
print("\n[2/5] Testing HX711 (Load Cell Weight)...")
try:
    # Dummy notify function
    hx = HX711Sensor(notify=lambda msg: None)
    # Apply standard ratio if available, otherwise just use default 1.0
    try:
        hx.apply_saved_calibration()
    except:
        pass
    weight = hx.read_weight_robust(samples=5)
    print(f"  ✅ Current Net Weight: {weight:.2f} g")
except Exception as e:
    print(f"  ❌ HX711 Error: {e}")


# 3. Test MPU6050 IMU
print("\n[3/5] Testing MPU6050 (Accelerometer & Gyroscope)...")
try:
    mpu = Mpu6050Sensor()
    imu = mpu.read()
    print(f"  ✅ Accel (g) : X={imu.accel_x:.2f}, Y={imu.accel_y:.2f}, Z={imu.accel_z:.2f}")
    print(f"  ✅ Gyro (dps): X={imu.gyro_x:.2f}, Y={imu.gyro_y:.2f}, Z={imu.gyro_z:.2f}")
except Exception as e:
    print(f"  ❌ MPU6050 Error: {e}. Check I2C wiring (SDA/SCL) and run 'i2cdetect -y 1'.")


# 4. Test INMP441 Microphone
print("\n[4/5] Testing INMP441 (I2S Microphone)...")
try:
    mic = Inmp441Sensor()
    acoustic = mic.read()
    if acoustic.available:
        print(f"  ✅ Dominant Frequency: {acoustic.dominant_freq_hz:.2f} Hz")
        print(f"  ✅ AI Behavior: {acoustic.behavior} (Confidence: {acoustic.confidence:.0%})")
    else:
        print("  ⚠️ Mic unavailable or reading failed. Check I2S overlay and 'arecord -l'.")
except Exception as e:
    print(f"  ❌ INMP441 Error: {e}")


# 5. Test Camera (V4L2)
print("\n[5/5] Testing V4L2 USB Camera (Varroa Monitor)...")
try:
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        print("  ⚠️ Camera failed to open via V4L2. Trying default backend...")
        cap = cv2.VideoCapture(0)
        
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"  ✅ Camera OK. Captured frame size: {frame.shape[1]}x{frame.shape[0]}")
        else:
            print("  ⚠️ Camera opened but failed to capture a frame.")
        cap.release()
    else:
        print("  ❌ Camera not found. Is it plugged in?")
except Exception as e:
    print(f"  ❌ Camera Error: {e}")

print("\n==================================================")
print("Diagnostics Complete!")
print("==================================================")
