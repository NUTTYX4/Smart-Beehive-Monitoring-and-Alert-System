#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_model_raspi.py
===================
Standalone script for testing the newly trained YOLOv8 ONNX model 
directly on the Raspberry Pi with the USB webcam.

Includes robust USB webcam discovery, Wayland/XCB window fixes,
and live mite counting!
"""

import cv2
import os
import time
from ultralytics import YOLO

def main():
    # Fix for Raspberry Pi Wayland + OpenCV Qt backend crashes
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    
    # Path to model (one directory up since we are in test/ folder)
    model_path = os.path.join(os.path.dirname(__file__), "..", "varroa_nano_v2.onnx")
    print(f"Loading model from {model_path}...")
    
    try:
        model = YOLO(model_path, task="detect")
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("Starting USB Webcam...")
    
    # Auto-detect USB webcam index (sometimes it's not 0 on Pi)
    cap = None
    for cam_idx in range(5):
        print(f"Trying camera index {cam_idx} with V4L2...")
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
        if cap.isOpened():
            # Test if we can actually read a frame
            ret, _ = cap.read()
            if ret:
                print(f"Successfully opened camera at index {cam_idx}")
                break
            else:
                cap.release()
                
    if cap is None or not cap.isOpened():
        print("Error: Could not open any camera. Please check your USB connection.")
        return
        
    # Standard resolution for inference testing
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("Starting live inference feed. Press 'q' in the window to quit.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Failed to grab frame.")
                time.sleep(0.1)
                continue
                
            # Run YOLO inference
            results = model(frame, verbose=False)
            
            # Count the number of detected mites
            mite_count = len(results[0].boxes)
            
            # Draw bounding boxes and labels
            annotated_frame = results[0].plot()
            
            # Overlay the mite count on the top-left corner
            text = f"Mites Detected: {mite_count}"
            cv2.putText(annotated_frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.putText(annotated_frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Print count to terminal to keep track without looking at video
            if mite_count > 0:
                print(f"[{time.strftime('%H:%M:%S')}] Alert: {mite_count} Varroa Mites detected!")
            
            # Show live feed
            cv2.imshow("Varroa V2 Live Test - Press Q to quit", annotated_frame)
            
            # Wait for 1ms, check for 'q' key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: # q or Esc
                break
                
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released and windows closed.")

if __name__ == "__main__":
    main()
