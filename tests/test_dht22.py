#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_dht22.py
====================
Live hardware diagnostic for the DHT22 temperature/humidity sensor.
Reads and prints real sensor data every 2 seconds.

Wiring:
    DHT22 DATA  ->  GPIO 4  (Physical Pin 7)
    DHT22 VCC   ->  3.3V    (Physical Pin 1)
    DHT22 GND   ->  GND     (Physical Pin 6)

Run:
    python3 tests/test_dht22.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import time
from config import DHT22_PIN

print("=" * 50)
print("  BeeHive | DHT22 Sensor Diagnostic")
print(f"  GPIO Pin : {DHT22_PIN}  (Physical Pin 7)")
print("=" * 50)

# Try to import the hardware library
try:
    import board
    import adafruit_dht
    dht = adafruit_dht.DHT22(getattr(board, f"D{DHT22_PIN}"))
    print("  Library  : adafruit-circuitpython-dht  OK")
except ImportError:
    print("  ERROR: adafruit-circuitpython-dht not installed.")
    print("  Run:  pip install adafruit-circuitpython-dht adafruit-blinka")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR initialising DHT22: {e}")
    sys.exit(1)

print()
print("  Reading live sensor data (Ctrl+C to stop)...")
print()
print(f"  {'#':>4}  {'Temperature':>14}  {'Humidity':>10}  {'Status'}")
print(f"  {'-'*4}  {'-'*14}  {'-'*10}  {'-'*20}")

count = 0
errors = 0

try:
    while True:
        count += 1
        try:
            temp = dht.temperature
            humi = dht.humidity

            if temp is None or humi is None:
                raise RuntimeError("Sensor returned None")

            status = "OK"
            if temp > 36:
                status = "WARN: Temp HIGH"
            elif temp < 15:
                status = "WARN: Temp LOW"
            elif humi > 88:
                status = "WARN: Humidity HIGH"
            elif humi < 35:
                status = "WARN: Humidity LOW"

            print(f"  {count:>4}  {temp:>12.1f} C  {humi:>9.1f} %  {status}")

        except RuntimeError as e:
            errors += 1
            print(f"  {count:>4}  {'--':>12}    {'--':>9}    Read error #{errors}: {e}")

        time.sleep(2.0)

except KeyboardInterrupt:
    dht.exit()
    print()
    print(f"  Stopped. {count} readings, {errors} errors.")
    print("=" * 50)
