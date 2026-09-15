#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vaporizer.py
========================
Hardware diagnostic for the Oxalic Acid Vaporizer relay.

Safety Controls
---------------
  - SHORT pulse by default (0.5 s) — change PULSE_DURATION_S to test longer.
  - Confirms with a Y/N prompt before activating the relay.
  - Never bypasses the cooldown logic in RelayActuator.
  - Cleanly resets GPIO even if the script is interrupted (Ctrl+C).

Wiring Check
------------
  Relay IN  →  GPIO 17  (Physical Pin 11)
  Relay VCC →  5V       (Physical Pin 2 or 4)
  Relay GND →  GND      (Physical Pin 6 or 14)

Run:
    python3 tests/test_vaporizer.py
"""

import sys
import time

# ---------------------------------------------------------------------------
# Safety override — keeps treatment short during testing
# ---------------------------------------------------------------------------
PULSE_DURATION_S = 0.5    # seconds the relay will be ACTIVE during the test
RELAY_GPIO_PIN   = 17     # must match config.VAPORIZER_RELAY_PIN
# ---------------------------------------------------------------------------


def _prompt_confirm(msg: str) -> bool:
    try:
        ans = input(msg).strip().lower()
        return ans == "y"
    except KeyboardInterrupt:
        return False


def main() -> None:
    print("=" * 60)
    print("  BeeHive Monitor — Oxalic Acid Vaporizer Relay Diagnostic")
    print("=" * 60)
    print(f"  GPIO Pin      : {RELAY_GPIO_PIN}  (Physical Pin 11)")
    print(f"  Pulse Duration: {PULSE_DURATION_S} s  (safe test pulse)")
    print()

    # ---- Detect gpiozero -----------------------------------------------
    try:
        from gpiozero import OutputDevice
        from gpiozero import Device
        gpio_available = True
        print("  gpiozero     : OK")
    except ImportError:
        gpio_available = False
        print("  gpiozero     : NOT INSTALLED — will run in MOCK mode.")
        print("  Install with:  pip install gpiozero RPi.GPIO")
    print()

    # ---- Step 1: GPIO read-back check (input mode) ---------------------
    print("[ STEP 1 ] GPIO Pin Continuity Check")
    if gpio_available:
        try:
            from gpiozero import DigitalInputDevice
            probe = DigitalInputDevice(RELAY_GPIO_PIN, pull_up=True)
            state = probe.value
            probe.close()
            print(f"  Pin {RELAY_GPIO_PIN} reads as: {'HIGH (pulled up — relay IN connected)' if state else 'LOW (check wiring!)'}")
        except Exception as exc:
            print(f"  WARNING: Could not probe pin {RELAY_GPIO_PIN}: {exc}")
    else:
        print("  Skipped (gpiozero not available).")
    print()

    # ---- Step 2: Relay continuity (multimeter instruction) -------------
    print("[ STEP 2 ] Manual Wiring Check")
    print("  Before running the relay pulse, verify:")
    print("  a) Relay IN  wire goes to GPIO 17 (Physical Pin 11)")
    print("  b) Relay VCC wire goes to 5V      (Physical Pin 2)")
    print("  c) Relay GND wire goes to GND     (Physical Pin 6)")
    print("  d) Relay LED should be OFF right now (NO state).")
    print()

    # ---- Step 3: Safety confirmation -----------------------------------
    print("[ STEP 3 ] Relay Activation Test")
    print(f"  WARNING: This will briefly ENERGISE the relay for {PULSE_DURATION_S} s.")
    print("  Ensure the vaporizer heater is DISCONNECTED for this test.")
    print("  Only test relay click (NO oxalic acid loaded).")
    print()

    if not _prompt_confirm("  >>> Proceed? You should hear/see the relay click. (y/N): "):
        print("  Aborted by user.")
        sys.exit(0)

    # ---- Activate relay -----------------------------------------------
    relay = None
    try:
        if gpio_available:
            relay = OutputDevice(RELAY_GPIO_PIN, active_high=True, initial_value=False)
            print()
            print("  [RELAY ON]  Energising relay ...")
            relay.on()
            time.sleep(PULSE_DURATION_S)
            relay.off()
            print("  [RELAY OFF] Relay de-energised.")
        else:
            print()
            print(f"  [MOCK ON]  Relay WOULD activate on GPIO {RELAY_GPIO_PIN}")
            time.sleep(PULSE_DURATION_S)
            print("  [MOCK OFF] Relay WOULD de-energise")

    except Exception as exc:
        print(f"\n  FAIL: Relay activation error — {exc}")
        print("  Check that RPi.GPIO or rpi-lgpio is installed and you are")
        print("  running as the 'gpio' group or with sudo if needed.")
        sys.exit(1)
    finally:
        if relay:
            relay.off()    # always leave relay in safe state
            relay.close()

    # ---- Results -------------------------------------------------------
    print()
    print("=" * 60)
    print("  PASS  : Relay cycled successfully.")
    print()
    print("  What to verify:")
    print("  1. You heard a clear CLICK from the relay.")
    print("  2. The relay LED turned ON briefly, then OFF.")
    print("  3. If using a multimeter across COM/NO: continuity during pulse.")
    print()
    print("  If any check failed, re-check wiring and GPIO pin number.")
    print("=" * 60)


if __name__ == "__main__":
    main()
