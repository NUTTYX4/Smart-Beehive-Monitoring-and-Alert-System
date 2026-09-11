#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_vision.py
==============
Headless sandbox script to test the varroa mite detection model.
It captures a frame every 2 seconds, runs inference, and prints 
the live mite count to the console.
"""

import time
import sys
from ai_module.vision_engine import VarroaVisionEngine

def main():
    print("Initializing Varroa Vision Engine...")
    engine = VarroaVisionEngine(model_path="ai_module/varroa_nano.pt")
    
    if not engine.available:
        print("Engine unavailable. Ensure OpenCV, Ultralytics, and the model file exist.")
        return
        
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Testing static image: {image_path}")
        t0 = time.time()
        result = engine.detect_mites_from_image(image_path, conf=0.25)
        t1 = time.time()
        
        if result.get("available"):
            count = result.get("mite_count", 0)
            print(f"✅ Mites detected: {count} (took {t1 - t0:.2f}s)")
        else:
            print("❌ Inference failed.")
        return
        
    print("Starting continuous headless inference. Press Ctrl+C to stop.")
    
    try:
        while True:
            print("Capturing frame and running inference...")
            t0 = time.time()
            result = engine.detect_mites(conf=0.25)
            t1 = time.time()
            
            if result.get("available"):
                count = result.get("mite_count", 0)
                print(f"-> Mites detected: {count} (took {t1 - t0:.2f}s)")
            else:
                print("-> Inference failed or camera unavailable.")
                
            print("Waiting 2 seconds...")
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\nTesting stopped by user.")

if __name__ == "__main__":
    main()
