# -*- coding: utf-8 -*-
"""Unit tests for the INMP441 audio pipeline (audio/filters.py,
audio/fft.py, sensors/inmp441_sensor.py) using synthetic signals so no
real microphone hardware is required."""

from __future__ import annotations

import unittest

import numpy as np

from audio import fft as fft_module
from audio.filters import apply_window, condition_signal, is_silent, remove_dc_offset
from sensors.inmp441_sensor import Inmp441Sensor
from audio.capture import MicrophoneUnavailableError


class TestFilters(unittest.TestCase):
    def test_remove_dc_offset_zeros_mean(self) -> None:
        samples = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = remove_dc_offset(samples)
        self.assertAlmostEqual(float(np.mean(result)), 0.0, places=6)

    def test_apply_window_preserves_length(self) -> None:
        samples = np.ones(256)
        windowed = apply_window(samples, window="hann")
        self.assertEqual(len(windowed), 256)

    def test_is_silent_detects_low_amplitude(self) -> None:
        quiet = np.full(100, 0.001)
        self.assertTrue(is_silent(quiet, noise_gate=0.01))

    def test_is_silent_detects_loud_signal(self) -> None:
        loud = np.full(100, 0.5)
        self.assertFalse(is_silent(loud, noise_gate=0.01))

    def test_condition_signal_runs_end_to_end(self) -> None:
        samples = np.sin(np.linspace(0, 10, 512)) + 3.0  # with DC offset
        conditioned = condition_signal(samples)
        self.assertEqual(len(conditioned), 512)


class TestFft(unittest.TestCase):
    def test_analyze_detects_known_tone(self) -> None:
        sample_rate = 8000.0
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        tone_hz = 250.0
        signal = 0.8 * np.sin(2 * np.pi * tone_hz * t)

        result = fft_module.analyze(signal, sample_rate, band_low=100, band_high=800, noise_gate=0.01)

        self.assertFalse(result.is_silent)
        self.assertAlmostEqual(result.dominant_freq_hz, tone_hz, delta=5.0)

    def test_analyze_silent_buffer_returns_zero(self) -> None:
        samples = np.zeros(1000)
        result = fft_module.analyze(samples, 8000.0)
        self.assertTrue(result.is_silent)
        self.assertEqual(result.dominant_freq_hz, 0.0)

    def test_analyze_empty_buffer_is_safe(self) -> None:
        result = fft_module.analyze(np.array([]), 8000.0)
        self.assertEqual(result.dominant_freq_hz, 0.0)


class TestInmp441SensorFacade(unittest.TestCase):
    def test_read_degrades_gracefully_when_capture_unavailable(self) -> None:
        sensor = Inmp441Sensor.__new__(Inmp441Sensor)

        class RaisingCapture:
            sample_rate = 44100

            def capture(self, duration_s: float):  # noqa: ANN001
                raise MicrophoneUnavailableError("no device")

        sensor._capture = RaisingCapture()
        reading = sensor.read(duration_s=0.1)
        self.assertFalse(reading.available)
        self.assertTrue(reading.silent)
        self.assertEqual(reading.dominant_freq_hz, 0.0)


if __name__ == "__main__":
    unittest.main()
