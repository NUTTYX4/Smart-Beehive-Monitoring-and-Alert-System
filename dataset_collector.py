#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataset_collector.py
====================
Sandbox utility for capturing raw images from the Raspberry Pi 5 camera 
for YOLO model training. 

Press 'Enter' to capture an image.
Press 'q' or 'Esc' to quit.
"""

import cv2
import os
import time
from pathlib import Path

DATA_DIR = Path("dataset/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Starting camera... Press ENTER in the terminal to capture, or type 'q' to quit.")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    count = 0
    try:
        while True:
            # We must constantly read frames to keep the buffer fresh
            ret, frame = cap.read()
            if not ret:
                print("Warning: Failed to grab frame.")
                time.sleep(0.1)
                continue
                
            cmd = input("Press ENTER to capture, 'q' to quit: ")
            
            if cmd.lower() == 'q':
                break
                
            # If we reach here, user pressed Enter (empty string) or something else
            # We want to grab a fresh frame right when they press it
            ret, frame = cap.read()
            if ret:
                timestamp = int(time.time() * 1000)
                filename = DATA_DIR / f"mite_sample_{timestamp}.jpg"
                cv2.imwrite(str(filename), frame)
                count += 1
                print(f"[{count}] Saved: {filename}")
            else:
                print("Error: Failed to capture.")
                
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        cap.release()
        print("Camera released.")

if __name__ == "__main__":
    main()
