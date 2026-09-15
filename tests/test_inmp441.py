#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_inmp441.py
======================
Live hardware diagnostic for the INMP441 I2S microphone.
Captures audio, computes FFT, and displays the dominant frequency
and a live ASCII bar chart of the sound energy in real time.

Wiring (I2S):
    INMP441 WS   ->  GPIO 19  (Physical Pin 35)
    INMP441 SCK  ->  GPIO 18  (Physical Pin 12)
    INMP441 SD   ->  GPIO 20  (Physical Pin 38)
    INMP441 VDD  ->  3.3V
    INMP441 GND  ->  GND
    INMP441 L/R  ->  GND      (selects left channel)

Run:
    python3 tests/test_inmp441.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import time
import numpy as np
from config import INMP441_SAMPLE_RATE, INMP441_CAPTURE_SECONDS

print("=" * 55)
print("  BeeHive | INMP441 Microphone Diagnostic")
print(f"  Sample Rate : {INMP441_SAMPLE_RATE} Hz")
print(f"  Capture Dur : {INMP441_CAPTURE_SECONDS} s per reading")
print("=" * 55)

try:
    import sounddevice as sd
    print("  sounddevice : OK")
except ImportError:
    print("  ERROR: sounddevice not installed.")
    print("  Run:  pip install sounddevice")
    sys.exit(1)

# List available devices so user can confirm the mic is detected
devices = sd.query_devices()
print()
print("  Available audio input devices:")
found_mic = False
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"    [{i}] {dev['name']}  (channels: {dev['max_input_channels']})")
        found_mic = True
if not found_mic:
    print("    NONE FOUND — Is the INMP441 I2S enabled?")
    print("    Check /boot/config.txt for:  dtoverlay=googlevoicehat-soundcard")
    sys.exit(1)

print()
print("  Listening... (make a sound near the mic)  Ctrl+C to stop")
print()
print(f"  {'#':>4}  {'Dominant Freq':>14}  {'Amplitude':>10}  {'Bee State':>22}  Level")
print(f"  {'-'*4}  {'-'*14}  {'-'*10}  {'-'*22}  {'-'*20}")

def classify(freq: float) -> str:
    if freq == 0:    return "Silent / No signal"
    if freq < 100:   return "Dormant / Low activity"
    if freq < 190:   return "Queenless roar"
    if freq < 330:   return "Normal / Active"
    if freq < 450:   return "Queen piping"
    return "Aggressive / Swarming"

count = 0
try:
    while True:
        count += 1
        try:
            audio = sd.rec(
                int(INMP441_SAMPLE_RATE * INMP441_CAPTURE_SECONDS),
                samplerate=INMP441_SAMPLE_RATE,
                channels=1,
                dtype='float32'
            )
            sd.wait()
            samples = audio.flatten()

            amplitude = float(np.abs(samples).mean())

            # FFT analysis within bee-relevant band (100–800 Hz)
            fft_vals = np.abs(np.fft.rfft(samples))
            freqs    = np.fft.rfftfreq(len(samples), 1 / INMP441_SAMPLE_RATE)
            mask     = (freqs >= 100) & (freqs <= 800)
            if mask.any() and fft_vals[mask].max() > 0.001:
                dom_freq = float(freqs[mask][fft_vals[mask].argmax()])
            else:
                dom_freq = 0.0

            state = classify(dom_freq)

            # ASCII level bar (0–20 chars)
            bar_len = min(20, int(amplitude * 400))
            bar     = "█" * bar_len + "░" * (20 - bar_len)

            freq_str = f"{dom_freq:>8.1f} Hz" if dom_freq > 0 else "   Silent   "
            print(f"  {count:>4}  {freq_str:>14}  {amplitude:>10.4f}  {state:>22}  {bar}")

        except Exception as e:
            print(f"  {count:>4}  Read error: {e}")

        time.sleep(0.3)

except KeyboardInterrupt:
    print()
    print(f"  Stopped after {count} readings.")
    print("=" * 55)
