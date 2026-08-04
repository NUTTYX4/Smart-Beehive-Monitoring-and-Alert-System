# -*- coding: utf-8 -*-
"""
tests/diag_hx711_live.py
========================
Interactive standalone testing, diagnostic, and precision calibration
tool for the HX711 load cell sensor on Raspberry Pi.

Features:
    1. Live Raw Signal Monitor: View unfiltered 24-bit ADC values in
       real time to detect loose jumper wires, timing jitter, or noise spikes.
    2. Precision Guided Calibration: Safely zero out permanent deadweights
       (like an attached ~284g bottle setup) and compute rock-solid scale ratios
       using outlier-rejected sampling.
    3. Post-Calibration Live Feed: Continuously verify linear weight readings
       in real time before starting the monitoring services.

Usage on Raspberry Pi:
    cd ~/BeeHiveMonitor
    python3 -m tests.diag_hx711_live
"""

from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Tuple

# Add repository root to path so we can import config and utils cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

try:
    from config import (
        HX711_DOUT_PIN,
        HX711_SCK_PIN,
        CALIBRATION_FILE,
        WEIGHT_MAX_VALID,
        WEIGHT_MIN_VALID,
    )
    from utils.calibration import load_calibration, save_calibration
except ImportError as exc:
    print(f"❌ Failed to import project config or utils: {exc}")
    sys.exit(1)

# Try importing hardware HX711 library and GPIO; fall back to mock if off-Pi
try:
    import RPi.GPIO as GPIO
    from hx711 import HX711
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    GPIO = None  # type: ignore
    print("⚠️ [WARNING] 'hx711' or RPi.GPIO hardware library not installed. Running in Mock Simulation Mode.")

    class HX711:  # type: ignore
        """Mock HX711 stand-in for off-Pi testing and debugging."""
        def __init__(self, dout_pin: int, pd_sck_pin: int) -> None:
            self.dout = dout_pin
            self.sck = pd_sck_pin
            self.ratio = 1.0
            self.zero_val = 150000.0  # Simulated ~284g deadweight baseline count
            self.sim_weight_g = 0.0
            print(f"   [Mock HX711] Initialized on pins DOUT={dout_pin}, SCK={pd_sck_pin}")

        def reset(self) -> None:
            pass

        def zero(self) -> None:
            pass

        def set_scale_ratio(self, ratio: float) -> None:
            self.ratio = ratio if ratio != 0 else 1.0

        def get_value_mean(self, samples: int = 10) -> float:
            # Simulate ADC output with minor realistic thermal noise
            base = self.zero_val + (self.sim_weight_g * abs(self.ratio))
            noise = np.random.normal(0, 15.0)
            return float(base + noise)

        def get_weight_mean(self, samples: int = 10) -> float:
            val = self.get_value_mean(samples) - self.zero_val
            return float(val / self.ratio) if self.ratio != 0 else 0.0


def clear_screen() -> None:
    """Clear terminal screen for interactive display."""
    os.system("cls" if os.name == "nt" else "clear")


def read_clean_sample(hx: HX711, n_samples: int = 25, raw: bool = True) -> Tuple[float, float]:
    """
    Read n_samples with statistical outlier rejection (trimming top & bottom 10%).
    Returns (median_value, std_deviation).
    """
    vals: List[float] = []
    for _ in range(n_samples):
        try:
            if raw:
                if hasattr(hx, "get_value_mean"):
                    v = hx.get_value_mean(5)
                elif hasattr(hx, "get_raw_data_mean"):
                    v = hx.get_raw_data_mean(5)
                else:
                    v = hx.get_weight_mean(5)
            else:
                v = hx.get_weight_mean(5)
            vals.append(float(v))
        except Exception as exc:
            pass
        time.sleep(0.02)

    if not vals:
        return 0.0, 0.0

    arr = np.array(vals, dtype=float)
    if len(arr) >= 5:
        low, high = np.percentile(arr, [10, 90])
        trimmed = arr[(arr >= low) & (arr <= high)]
        if trimmed.size == 0:
            trimmed = arr
    else:
        trimmed = arr

    return float(np.median(trimmed)), float(np.std(trimmed))


def mode_live_raw_signal(hx: HX711) -> None:
    """Mode 1: Live raw ADC stream & jitter/noise detection."""
    clear_screen()
    print("=" * 66)
    print(" 📡 MODE 1: LIVE RAW SIGNAL & NOISE MONITOR")
    print("=" * 66)
    print("This stream shows the RAW 24-bit integers directly from the ADC.")
    print("Use this mode to check jumper wire connections, soldering, and grounding.")
    print("Press [Ctrl+C] at any time to stop and return to Main Menu.")
    print("-" * 66)
    input("Press ENTER to start the live stream...")

    try:
        last_val = None
        while True:
            median_val, std_val = read_clean_sample(hx, n_samples=7, raw=True)
            jitter_alert = ""
            
            if last_val is not None and abs(last_val) > 1000:
                delta_pct = abs(median_val - last_val) / abs(last_val) * 100.0
                if delta_pct > 3.0:
                    jitter_alert = "⚠️ SPIKE / NOISE DETECTED! Check jumper wires & grounding!"
                elif std_val > 500:
                    jitter_alert = "🟡 Mild vibration or power supply noise"

            last_val = median_val
            sys.stdout.write(f"\rRaw ADC Count: {median_val:12.1f}  |  StdDev: {std_val:6.1f}  {jitter_alert:45}")
            sys.stdout.flush()
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n\n🛑 Live stream stopped by user.")
        time.sleep(1.0)


def mode_guided_calibration(hx: HX711) -> None:
    """Mode 2: Guided precision calibration with deadweight support (~284g)."""
    clear_screen()
    print("=" * 66)
    print(" ⚖️ MODE 2: GUIDED PRECISION CALIBRATION")
    print("=" * 66)
    print("This wizard calibrates your scale cleanly, ignoring attached")
    print("deadweights (such as an existing ~284g bottle assembly).")
    print("-" * 66)

    # Step 1: Zero Baseline (Tare)
    print("\n[Step 1/3] ZERO BASELINE (DEADWEIGHT TARE)")
    print("Please ensure your empty bottle setup is resting undisturbed on the load cell.")
    input("Press ENTER when ready to capture baseline...")
    
    print("⏳ Sampling 30 filtered baseline readings (outlier-rejected)...")
    base_med, base_std = read_clean_sample(hx, n_samples=30, raw=True)
    print(f"✅ Baseline locked: Raw Count = {base_med:.2f} (Jitter StdDev = {base_std:.2f})")

    # Step 2: Known Test Weight
    print("\n[Step 2/3] ADD KNOWN TEST WEIGHT")
    print("Pour water or place a known weight (e.g., 100, 200, or 500 grams) onto the setup.")
    val_str = input("👉 Enter the exact added weight in GRAMS (e.g., 100): ").strip()
    try:
        known_weight = float(val_str)
        if known_weight <= 0:
            raise ValueError
    except ValueError:
        print("❌ Invalid weight input! Aborting calibration.")
        time.sleep(2.0)
        return

    input(f"Press ENTER once exactly {known_weight}g is resting steadily on the scale...")
    
    print("⏳ Sampling 30 filtered loaded readings...")
    load_med, load_std = read_clean_sample(hx, n_samples=30, raw=True)
    print(f"✅ Loaded locked: Raw Count = {load_med:.2f} (Jitter StdDev = {load_std:.2f})")

    # Step 3: Compute & Persist Ratio
    print("\n[Step 3/3] COMPUTING SCALE RATIO")
    raw_delta = load_med - base_med
    if abs(raw_delta) < 1.0:
        print("❌ ERROR: No measurable difference between baseline and loaded weight!")
        print("Check if the load cell is bending freely or if wires are disconnected.")
        time.sleep(3.0)
        return

    computed_ratio = raw_delta / known_weight
    print(f"📊 Delta Count: {raw_delta:.2f}")
    print(f"🎯 Calculated Scale Ratio: {computed_ratio:.6f}")

    save_ans = input("\n💾 Do you want to save this ratio to 'data/calibration.json'? [y/N]: ").strip().lower()
    if save_ans == "y":
        try:
            hx.set_scale_ratio(computed_ratio)
            save_calibration(known_weight, computed_ratio, owner_name="DiagnosticCLI")
            print(f"\n✨ SUCCESS! Ratio {computed_ratio:.6f} saved to {CALIBRATION_FILE}.")
            print("The Telegram bot and monitoring service will now use this calibration!")
        except Exception as exc:
            print(f"❌ Failed to save calibration: {exc}")
    else:
        print("ℹ️ Calibration discarded without saving.")

    input("\nPress ENTER to return to Main Menu...")


def mode_live_calibrated_feed(hx: HX711) -> None:
    """Mode 3: Live feed after calibration to test water pouring / weight steps."""
    clear_screen()
    print("=" * 66)
    print(" 🌊 MODE 3: LIVE CALIBRATED WEIGHT FEED (POST-CALIBRATION)")
    print("=" * 66)
    
    # Load latest ratio from disk
    cal_data = load_calibration()
    ratio = getattr(cal_data, "scale_ratio", 1.0)
    if ratio != 0:
        hx.set_scale_ratio(ratio)
    
    print(f"Loaded Scale Ratio: {ratio:.6f}")
    print("Pour water or place test items to verify smooth, linear gram readings.")
    print("Press [Ctrl+C] to stop live feed.")
    print("-" * 66)
    
    # Perform quick baseline lock before starting feed
    print("⏳ Auto-zeroing current baseline before launching feed...")
    base_raw, _ = read_clean_sample(hx, n_samples=15, raw=True)
    print("✅ Zeroed! Launching stream...\n")
    time.sleep(0.5)

    try:
        while True:
            cur_raw, std_val = read_clean_sample(hx, n_samples=7, raw=True)
            delta_raw = cur_raw - base_raw
            weight_g = delta_raw / ratio if ratio != 0 else 0.0
            
            # Status badge
            if abs(weight_g) > 4000:
                status = "🚨 OFF SCALE OR SIGNAL SPIKE!"
            elif std_val > 500:
                status = "🟡 UNSTABLE / MOVING"
            else:
                status = "🟢 STABLE"

            sys.stdout.write(f"\r⚖️ Weight: {weight_g:8.2f} g   |   Raw Delta: {delta_raw:10.1f}   |   Status: {status:28}")
            sys.stdout.flush()
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n\n🛑 Live calibrated feed stopped.")
        time.sleep(1.0)


def main() -> None:
    """Main terminal menu loop."""
    print(f"⚡ Initializing HX711 Sensor on DOUT={HX711_DOUT_PIN}, SCK={HX711_SCK_PIN}...")
    if HARDWARE_AVAILABLE and GPIO is not None:
        try:
            GPIO.setmode(GPIO.BCM)
            print("   [GPIO] Pin numbering set to BCM mode.")
        except Exception as exc:
            print(f"⚠️ [WARNING] Could not set GPIO mode to BCM: {exc}")
.
        choice = input("👉 Select an option [1-4]: ").strip()
        if choice == "1":
            mode_live_raw_signal(hx)
        elif choice == "2":
            mode_guided_calibration(hx)
        elif choice == "3":
            mode_live_calibrated_feed(hx)
        elif choice == "4" or choice.lower() in ["exit", "q", "quit"]:
            print("\n👋 Exiting Diagnostic Suite. Good luck with your beehive monitoring!")
            break
        else:
            print("❌ Invalid selection. Please enter 1, 2, 3, or 4.")
            time.sleep(1.0)


if __name__ == "__main__":
    main()
