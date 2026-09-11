#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_camera.py
====================
A hardware diagnostic script to verify the Raspberry Pi camera for headless 
setups (like SSH via PuTTY).

It captures a single frame and serves it over a temporary local web server 
so you can view it on your laptop's browser.
"""

import subprocess
import sys
import http.server
import socketserver
import socket
import os

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    print("Testing Raspberry Pi Camera Hardware (Headless Mode)...")
    
    cmd_base = None
    if subprocess.run(["which", "rpicam-jpeg"], capture_output=True).returncode == 0:
        cmd_base = "rpicam-jpeg"
    elif subprocess.run(["which", "libcamera-jpeg"], capture_output=True).returncode == 0:
        cmd_base = "libcamera-jpeg"
        
    if not cmd_base:
        print("❌ Error: Native camera tools not found (rpicam-jpeg/libcamera-jpeg).")
        sys.exit(1)

    print(f"✅ Found camera utility: {cmd_base}")
    print("📸 Capturing a test image...")
    
    # Change to the tests directory to serve from there
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    output_file = "test_image.jpg"
    
    res = subprocess.run([cmd_base, "-o", output_file, "-t", "1000", "--width", "1920", "--height", "1080", "--nopreview"], capture_output=True)
    
    if res.returncode != 0 or not os.path.exists(output_file):
        print("❌ Error capturing image. Is the camera properly connected?")
        print(res.stderr.decode('utf-8'))
        sys.exit(1)
        
    print(f"✅ Image saved successfully as {output_file}!")
    
    ip = get_local_ip()
    port = 8000
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    print("\n" + "="*50)
    print(f"🌐 Server started! To view the image on your laptop,")
    print(f"open your web browser and go to:")
    print(f"➡️  http://{ip}:{port}/{output_file}")
    print("="*50)
    print("Press Ctrl+C to stop the server when you're done.")
    
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == "__main__":
    main()
