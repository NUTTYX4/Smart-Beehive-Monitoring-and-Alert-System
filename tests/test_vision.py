#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vision.py
========================
A clean, native local window for the live camera feed that completely 
bypasses the OpenCV cv2.imshow() Wayland crash. 
Uses standard Tkinter to create a well-established desktop popup.

Run:
    pip install Pillow
    python3 tests/test_vision.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import cv2
import tkinter as tk
from PIL import Image, ImageTk
from ultralytics import YOLO

# Paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai_module', 'camera_model', 'varroa_nano.onnx')
CAM_INDEX = 0
CAPTURE_W = 1280
CAPTURE_H = 720

def main():
    print("==================================================")
    print("  BeeHive | Native Live Mite Detection (GUI)")
    print("==================================================")

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        sys.exit(1)

    print("Loading YOLOv8 Nano model...")
    model = YOLO(MODEL_PATH, task='detect')
    print("Model loaded successfully.")

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
    root.title("BeeHive - Native Live Vision")
    root.geometry(f"{CAPTURE_W}x{CAPTURE_H}")
    root.configure(bg="black")

    video_label = tk.Label(root, bg="black")
    video_label.pack(fill=tk.BOTH, expand=True)

    def update_frame():
        ret, frame = cap.read()
        if ret:
            # Run YOLO inference
            results = model.predict(source=frame, conf=0.5, verbose=False)
            annotated_frame = results[0].plot()

            # Display mite count
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

    print("\nNative window opening... Close the window to quit.")
    update_frame()
    root.mainloop()

if __name__ == "__main__":
    main()

