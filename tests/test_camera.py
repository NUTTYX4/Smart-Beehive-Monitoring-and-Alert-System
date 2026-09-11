#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_camera.py
====================
A simple hardware diagnostic script to verify that the Raspberry Pi camera 
is physically connected and working. 

It uses the native libcamera/rpicam stack to open a live preview window on 
the display attached to the Raspberry Pi.
"""

import subprocess
import sys

def main():
    print("Testing Raspberry Pi Camera Hardware...")
    
    # Check for rpicam-hello (default on newer Pi OS) or libcamera-hello
    cmd_base = None
    if subprocess.run(["which", "rpicam-hello"], capture_output=True).returncode == 0:
        cmd_base = "rpicam-hello"
    elif subprocess.run(["which", "libcamera-hello"], capture_output=True).returncode == 0:
        cmd_base = "libcamera-hello"
        
    if not cmd_base:
        print("❌ Error: Native camera tools not found (rpicam-hello/libcamera-hello).")
        print("Are you running this on a Raspberry Pi OS (Bullseye/Bookworm)?")
        sys.exit(1)

    print(f"✅ Found camera utility: {cmd_base}")
    print("Opening a live preview window on the screen...")
    print("➡️  Press Ctrl+C in this terminal to close the camera window.")
    
    try:
        # -t 0 keeps the preview open indefinitely
        subprocess.run([cmd_base, "-t", "0"])
    except KeyboardInterrupt:
        print("\nCamera test stopped by user.")
    except Exception as e:
        print(f"❌ Error running camera: {e}")

if __name__ == "__main__":
    main()
