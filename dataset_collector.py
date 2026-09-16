#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataset_collector.py
====================
Sandbox utility for capturing raw images from the USB webcam
for YOLO model training.

Shows a live video feed window.
Press 'Enter' in the terminal or 'Space' in the video window to capture.
Press 'q' or 'Esc' to quit.
"""

import cv2
import os
import time
import threading
from pathlib import Path

DATA_DIR = Path("dataset_v2/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Starting USB Webcam... A live feed window will appear.")
    print("Press ENTER in the terminal to capture, or type 'q' to quit.")
    
    # Force V4L2 backend to prevent GStreamer pipeline errors with USB webcams on Pi
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    # Try to set high resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    count = 0
    capture_flag = False
    quit_flag = False
    
    def terminal_input():
        nonlocal capture_flag, quit_flag
        while not quit_flag:
            cmd = input()
            if cmd.lower() == 'q':
                quit_flag = True
                break
            else:
                capture_flag = True
                
    # Run terminal input in a separate thread so it doesn't block cv2.imshow
    input_thread = threading.Thread(target=terminal_input, daemon=True)
    input_thread.start()
    
    try:
        while not quit_flag:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Failed to grab frame.")
                time.sleep(0.1)
                continue
                
            # Show live feed
            display_frame = cv2.resize(frame, (960, 540)) # Resize for display so it fits on screen
            cv2.imshow("Live Feed - Press Q in terminal to quit", display_frame)
            
            # Wait for 1ms, needed for imshow to work. Also check for 'q' key in the window
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: # q or Esc
                quit_flag = True
                break
            elif key == ord(' ') or key == 13: # Space or Enter in cv window
                capture_flag = True
                
            if capture_flag:
                timestamp = int(time.time() * 1000)
                filename = DATA_DIR / f"mite_sample_{timestamp}.jpg"
                cv2.imwrite(str(filename), frame)
                count += 1
                print(f"\n[{count}] Saved: {filename}")
                print("Press ENTER in the terminal to capture, or type 'q' to quit.")
                capture_flag = False
                
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        quit_flag = True
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released.")

if __name__ == "__main__":
    main()
