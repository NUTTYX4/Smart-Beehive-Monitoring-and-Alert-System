#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vision_relay.py
==========================
Live Native GUI Vision Test + Automated Vaporizer Relay Trigger
This script merges the local camera feed with the actual Relay hardware.
If mites >= MITE_THRESHOLD (15), it instantly turns on the relay 
in a background thread without freezing your camera feed!
"""

import sys, os
import threading
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import cv2
import tkinter as tk
from PIL import Image, ImageTk
from ultralytics import YOLO

from config import MITE_THRESHOLD
from sensors.relay_actuator import RelayActuator

# Paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai_module', 'camera_model', 'varroa_nano.onnx')
CAM_INDEX = 0
CAPTURE_W = 1280
CAPTURE_H = 720

def main():
    print("==================================================")
    print("  BeeHive | Native Live Vision + RELAY Trigger")
    print("==================================================")
    print(f"Relay will trigger if Mites >= {MITE_THRESHOLD}")
    print("==================================================")

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        sys.exit(1)

    print("Loading YOLOv8 Nano model...")
    model = YOLO(MODEL_PATH, task='detect')
    print("Model loaded successfully.")

    print("Initializing Relay Actuator hardware...")
    relay = RelayActuator()
    relay_is_treating = False

    print("\nOpening camera...")
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAM_INDEX)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera at index {CAM_INDEX}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Set up Tkinter Native Window
    root = tk.Tk()
    root.title(f"BeeHive Vision + Relay (Threshold: {MITE_THRESHOLD})")
    root.geometry(f"{CAPTURE_W}x{CAPTURE_H}")
    root.configure(bg="black")

    video_label = tk.Label(root, bg="black")
    video_label.pack(fill=tk.BOTH, expand=True)

    def trigger_relay_background():
        nonlocal relay_is_treating
        relay_is_treating = True
        try:
            # trigger_treatment handles the actual GPIO click and internal cooldown
            relay.trigger_treatment()
        finally:
            relay_is_treating = False

    def update_frame():
        ret, frame = cap.read()
        if ret:
            # Run YOLO inference
            results = model.predict(source=frame, conf=0.5, verbose=False)
            annotated_frame = results[0].plot()

            # Display mite count
            mite_count = len(results[0].boxes)
            
            # --- RELAY LOGIC ---
            if mite_count >= MITE_THRESHOLD and not relay_is_treating:
                threading.Thread(target=trigger_relay_background, daemon=True).start()

            # Warning text color if treating
            text_color = (0, 165, 255) if relay_is_treating else (0, 0, 255) # Orange if active, Red normally
            status_text = f"Mites detected: {mite_count}"
            if relay_is_treating:
                status_text += " [VAPORIZER ON!]"

            cv2.putText(
                annotated_frame, 
                status_text, 
                (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1.5, 
                text_color, 
                3, 
                cv2.LINE_AA
            )

            # Convert from BGR (OpenCV) to RGB (PIL)
            color_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(color_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update label
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        
        # Loop every 15 milliseconds
        root.after(15, update_frame)

    def on_closing():
        cap.release()
        root.destroy()
        print("\nTest completed.")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    update_frame()
    root.mainloop()

if __name__ == "__main__":
    main()
