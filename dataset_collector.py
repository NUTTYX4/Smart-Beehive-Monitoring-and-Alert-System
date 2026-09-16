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

import os
import time
import subprocess
from pathlib import Path

DATA_DIR = Path("dataset_v2/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Starting dataset collector...")
    print("This uses native libcamera/rpicam commands for the Raspberry Pi 5.")
    print("Make sure your camera is connected.")
    
    count = 0
    cmd_base = None
    
    # Detect available libcamera command
    if subprocess.run(["which", "rpicam-jpeg"], capture_output=True).returncode == 0:
        cmd_base = "rpicam-jpeg"
    elif subprocess.run(["which", "libcamera-jpeg"], capture_output=True).returncode == 0:
        cmd_base = "libcamera-jpeg"
    else:
        print("Error: Neither rpicam-jpeg nor libcamera-jpeg found on this system.")
        return
        
    try:
        while True:
            cmd = input("Press ENTER to capture, 'q' to quit: ")
            
            if cmd.lower() == 'q':
                break
                
            timestamp = int(time.time() * 1000)
            filename = DATA_DIR / f"mite_sample_{timestamp}.jpg"
            
            print(f"Capturing frame with {cmd_base}...")
            # Run the capture command
            res = subprocess.run([
                cmd_base, 
                "-o", str(filename), 
                "-t", "500",      # 500ms warmup
                "--width", "1920", 
                "--height", "1080",
                "--nopreview"
            ], capture_output=True)
            
            if res.returncode == 0 and filename.exists():
                count += 1
                print(f"[{count}] Saved: {filename}")
            else:
                print("Error: Failed to capture.")
                if res.stderr:
                    print(res.stderr.decode('utf-8'))
                
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        print("Done.")

if __name__ == "__main__":
    main()
