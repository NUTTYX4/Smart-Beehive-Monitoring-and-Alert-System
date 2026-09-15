#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vaporizer.py
========================
Interactive hardware diagnostic for the Oxalic Acid Vaporizer relay.

Prompts:
    [Y] -- Turns the relay ON for HOLD_SECONDS, then turns it OFF.
    [N] -- Skips without activating.

Safety:
    - DISCONNECT the vaporizer heater before running this test.
    - Only test the relay click (no oxalic acid loaded).
    - Relay is ALWAYS turned off in the finally block, even on crash.

Wiring:
    Relay IN   ->  GPIO 17  (Physical Pin 11)
    Relay VCC  ->  5V       (Physical Pin 2)
    Relay GND  ->  GND      (Physical Pin 6)

Run:
    python3 tests/test_vaporizer.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import time
from config import VAPORIZER_RELAY_PIN

HOLD_SECONDS = 3.0   # How long to keep relay ON during the test

print("=" * 55)
print("  BeeHive | Vaporizer Relay Diagnostic")
print(f"  GPIO Pin    : {VAPORIZER_RELAY_PIN}  (Physical Pin 11)")
print(f"  Hold Time   : {HOLD_SECONDS} s")
print("=" * 55)
print()
print("  ⚠️  SAFETY: Disconnect the heater before proceeding!")
print()

# --- Import GPIO ---
relay = None
try:
    from gpiozero import OutputDevice
    relay = OutputDevice(VAPORIZER_RELAY_PIN, active_high=True, initial_value=False)
    print(f"  gpiozero    : OK")
    print(f"  Relay GPIO  : Initialised on pin {VAPORIZER_RELAY_PIN}  OK")
    print(f"  Relay state : OFF (safe)")
except ImportError:
    print("  ERROR: gpiozero not installed.  Run:  pip install gpiozero RPi.GPIO")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR: Cannot initialise relay on GPIO {VAPORIZER_RELAY_PIN}: {e}")
    sys.exit(1)

print()

# --- Interactive loop ---
run_count = 0
try:
    while True:
        print("-" * 55)
        try:
            answer = input("  Activate relay? [Y=yes / N=no / Q=quit]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if answer == 'q':
            break

        elif answer == 'y':
            run_count += 1
            print()
            print(f"  [{run_count}] RELAY ON  — energising for {HOLD_SECONDS} s ...")
            try:
                relay.on()
                for remaining in range(int(HOLD_SECONDS), 0, -1):
                    print(f"        ... {remaining}s remaining", end="\r")
                    time.sleep(1.0)
                print()
            finally:
                relay.off()
            print(f"  [{run_count}] RELAY OFF — de-energised.")
            print()
            print("  Did you hear/see the relay click ON then OFF? (Y/N)")
            verify = input("  Verify: ").strip().lower()
            if verify == 'y':
                print("  ✅ PASS — relay is working correctly.")
            else:
                print("  ❌ FAIL — check wiring. Relay IN -> GPIO 17, VCC -> 5V, GND -> GND.")

        elif answer == 'n':
            print("  Skipped.")

        else:
            print("  Invalid input. Type Y, N, or Q.")

except Exception as e:
    print(f"\n  ERROR during relay test: {e}")
finally:
    if relay:
        relay.off()    # always leave relay in safe OFF state
        relay.close()

print()
print(f"  Test complete. Relay activated {run_count} time(s).")
print("=" * 55)
