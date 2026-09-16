#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataset_collector.py
====================
Sandbox utility for capturing raw images from the camera
for YOLO model training.

Shows a live video feed window.
Press 'Enter' in the terminal or 'Space' in the video window to capture.
Press 'q' or 'Esc' to quit.
"""

import cv2
import os
import time
import threading
import subprocess
import numpy as np
from pathlib import Path

DATA_DIR = Path("dataset_v2/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_native_cmd():
    if subprocess.run(["which", "rpicam-vid"], capture_output=True).returncode == 0:
        return "rpicam-vid"
    elif subprocess.run(["which", "libcamera-vid"], capture_output=True).returncode == 0:
        return "libcamera-vid"
    return None

def main():
    print("Starting camera stream... A live feed window will appear.")
    print("Press ENTER in the terminal to capture, or type 'q' to quit.")
    
    cmd_base = get_native_cmd()
    cap = None
    process = None
    
    if cmd_base:
        print(f"Optimal framework detected: Using native {cmd_base} for Pi 5 compatibility...")
        # Stream MJPEG to stdout
        cmd = [
            cmd_base, "-t", "0", "--codec", "mjpeg", 
            "--width", "1920", "--height", "1080", 
            "--framerate", "15", "--inline", "-o", "-"
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    else:
        print("Native tools not found, falling back to basic OpenCV...")
        cap = cv2.VideoCapture(0)
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
                
    input_thread = threading.Thread(target=terminal_input, daemon=True)
    input_thread.start()
    
    bytes_data = b''
    
    try:
        while not quit_flag:
            frame = None
            
            if process:
                # Read from native MJPEG stream
                bytes_data += process.stdout.read(4096)
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                # Read from standard OpenCV
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
            
            if frame is None:
                continue

            # Show live feed
            display_frame = cv2.resize(frame, (960, 540)) 
            cv2.imshow("Live Feed - Press Q in terminal to quit", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                quit_flag = True
                break
            elif key == ord(' ') or key == 13: 
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
        if process:
            process.terminate()
            process.wait()
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("Camera released.")

if __name__ == "__main__":
    main()
