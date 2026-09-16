#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vision.py
=====================
Live hardware diagnostic for the YOLOv8 Nano Varroa Mite detection model.
Uses the USB webcam to run live inference and draws bounding boxes around detected mites.

Run:
    python3 tests/test_vision.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import cv2
from ultralytics import YOLO

# Paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai_module', 'camera_model', 'varroa_nano.onnx')
CAM_INDEX = 0
CAPTURE_W = 1280
CAPTURE_H = 720

def main():
    print("==================================================")
    print("  BeeHive | Live YOLOv8 Mite Detection Test")
    print("==================================================")

    if not os.path.exists(MODEL_PATH):
        print(f"\nERROR: Model not found at {MODEL_PATH}")
        print("Please ensure the training has finished and the model is saved.")
        sys.exit(1)

    print("\nLoading YOLOv8 Nano model...")
    model = YOLO(MODEL_PATH)
    print("Model loaded successfully.")

    print("\nOpening camera (/dev/video0 via V4L2)...")
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        # Fallback for generic USB Cam
        cap = cv2.VideoCapture(CAM_INDEX)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera at index {CAM_INDEX}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("\nLive inference started. Press 'q' or 'ESC' to quit.")

    window_name = "Varroa Mite Detection (Live)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, CAPTURE_W, CAPTURE_H)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Missed frame.")
                continue

            # Run YOLO inference
            # conf=0.5 -> Only show detections with > 50% confidence
            results = model.predict(source=frame, conf=0.5, verbose=False)
            
            # The results object contains the annotated image
            annotated_frame = results[0].plot()

            # Display mite count on screen
            mite_count = len(results[0].boxes)
            cv2.putText(
                annotated_frame, 
                f"Mites detected: {mite_count}", 
                (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1.5, 
                (0, 0, 255), 
                3, 
                cv2.LINE_AA
            )

            cv2.imshow(window_name, annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nTest completed.")

if __name__ == "__main__":
    main()

