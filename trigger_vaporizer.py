import RPi.GPIO as GPIO
import time
from config import VAPORIZER_RELAY_PIN, MITE_THRESHOLD, TREATMENT_DURATION_S

def trigger_treatment(mite_count):
    if mite_count <= MITE_THRESHOLD:
        print(f"Mite count ({mite_count}) is below threshold ({MITE_THRESHOLD}). No treatment needed.")
        return

    print(f"CRITICAL: Mite count ({mite_count}) exceeded threshold ({MITE_THRESHOLD})!")
    print(f"Triggering Oxalic Acid Vaporizer on GPIO {VAPORIZER_RELAY_PIN} for {TREATMENT_DURATION_S} seconds...")
    
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(VAPORIZER_RELAY_PIN, GPIO.OUT)
    
    try:
        # Turn ON relay (Assuming active HIGH. If active LOW, use GPIO.LOW)
        GPIO.output(VAPORIZER_RELAY_PIN, GPIO.HIGH)
        print("Vaporizer is ON. Treating hive...")
        
        time.sleep(TREATMENT_DURATION_S)
        
    finally:
        # Turn OFF relay
        GPIO.output(VAPORIZER_RELAY_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("Vaporizer is OFF. Treatment complete.")

if __name__ == '__main__':
    # Test script: Simulating a mite detection
    simulated_mite_count = int(input("Enter simulated mite count: "))
    trigger_treatment(simulated_mite_count)
