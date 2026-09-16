#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vision_headless.py
==============================
Diagnostic script to test if the Segmentation Fault is caused by OpenCV GUI (cv2.imshow) 
or the PyTorch model inference itself.

Run:
    python3 tests/test_vision_headless.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import cv2
print("1. OpenCV imported successfully.")

try:
    from ultralytics import YOLO
    print("2. Ultralytics imported successfully.")
except Exception as e:
    print(f"ERROR loading Ultralytics: {e}")
    sys.exit(1)

# Paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai_module', 'camera_model', 'varroa_nano.pt')

def main():
    print("3. Loading YOLOv8 Nano model...")
    try:
        model = YOLO(MODEL_PATH)
        print("   Model loaded successfully.")
    except Exception as e:
        print(f"ERROR loading model: {e}")
        sys.exit(1)

    print("4. Reading one frame from camera...")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("ERROR: Could not read from camera.")
        sys.exit(1)
    
    print("   Frame captured successfully.")

    print("5. Running YOLO inference (THIS IS WHERE PYTORCH MIGHT CRASH)...")
    try:
        # Run inference (no GUI involved here)
        results = model.predict(source=frame, conf=0.5, verbose=False)
        print("   Inference completed successfully!")
        
        mite_count = len(results[0].boxes)
        print(f"   Mites detected: {mite_count}")
        
        # Save output to file instead of imshow
        annotated_frame = results[0].plot()
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_output.jpg')
        cv2.imwrite(out_path, annotated_frame)
        print(f"   Saved annotated image to {out_path}")

    except Exception as e:
        print(f"ERROR during inference: {e}")
        sys.exit(1)

    print("\n✅ SUCCESS: PyTorch and OpenCV are working. The previous crash was caused by the cv2.imshow() GUI window on Raspberry Pi.")

if __name__ == "__main__":
    main()
