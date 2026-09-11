# -*- coding: utf-8 -*-
"""
sensors/relay_actuator.py
=========================
Actuator module using gpiozero for the Raspberry Pi 5 to control
the Oxalic Acid Vaporizer relay.
"""

import time
from config import VAPORIZER_RELAY_PIN, TREATMENT_DURATION_S, COOLDOWN_S
from utils.logger import get_logger

try:
    from gpiozero import OutputDevice
except ImportError:
    OutputDevice = None

logger = get_logger(__name__)

class RelayActuator:
    def __init__(self, pin: int = VAPORIZER_RELAY_PIN):
        self._pin = pin
        self._last_trigger_time = 0.0
        self._relay = None
        
        if OutputDevice is not None:
            try:
                # Active high by default. Some relays might need active_high=False
                self._relay = OutputDevice(self._pin, active_high=True, initial_value=False)
            except Exception as e:
                logger.error("Failed to initialize RelayActuator on pin %d: %s", self._pin, e)
        else:
            logger.warning("gpiozero not installed; RelayActuator will run in mock mode.")

    def trigger_treatment(self) -> bool:
        """
        Triggers the oxalic acid vaporizer relay for TREATMENT_DURATION_S.
        Enforces a COOLDOWN_S period to prevent hardware damage or continuous firing.
        Returns True if triggered successfully, False otherwise (e.g. cooldown).
        """
        now = time.time()
        if (now - self._last_trigger_time) < COOLDOWN_S:
            remaining = int(COOLDOWN_S - (now - self._last_trigger_time))
            logger.warning("Vaporizer trigger ignored (in cooldown: %ds remaining).", remaining)
            return False

        logger.info("Triggering Oxalic Acid Vaporizer for %.1fs...", TREATMENT_DURATION_S)
        self._last_trigger_time = now

        if self._relay is None:
            logger.info("[MOCK] Vaporizer relay ON")
            time.sleep(TREATMENT_DURATION_S)
            logger.info("[MOCK] Vaporizer relay OFF")
            return True

        try:
            self._relay.on()
            time.sleep(TREATMENT_DURATION_S)
        except Exception as e:
            logger.error("Error during vaporizer treatment: %s", e)
            return False
        finally:
            self._relay.off()
            logger.info("Oxalic Acid Vaporizer treatment complete.")
            
        return True
