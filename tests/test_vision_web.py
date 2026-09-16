#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_vision_web.py
========================
Bypasses the Raspberry Pi cv2.imshow() Segmentation Fault by streaming 
the live annotated camera feed to a local web browser!

Run:
    pip install flask
    python3 tests/test_vision_web.py

Then open http://<RASPBERRY_PI_IP>:5000 in your laptop/phone browser.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import cv2
from flask import Flask, Response
from ultralytics import YOLO

# Paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai_module', 'camera_model', 'varroa_nano.onnx')
CAM_INDEX = 0

app = Flask(__name__)

# Load model globally
if not os.path.exists(MODEL_PATH):
    print(f"ERROR: Model not found at {MODEL_PATH}")
    sys.exit(1)

print("Loading YOLOv8 ONNX model...")
model = YOLO(MODEL_PATH, task='detect')
print("Model loaded successfully.")

def generate_frames():
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAM_INDEX)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
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
        
        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        # Yield in multipart MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("\n==================================================")
    print("  BeeHive | Live YOLOv8 Web Stream")
    print("==================================================")
    print("Open your web browser and go to: http://localhost:5000")
    print("Or if accessing from your PC: http://<raspberry-pi-ip>:5000")
    print("==================================================\n")
    app.run(host='0.0.0.0', port=5000, threaded=True)
