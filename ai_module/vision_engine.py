# -*- coding: utf-8 -*-
"""
ai_module/vision_engine.py
==========================
Vision module for detecting Varroa mites (using sprouted horse gram seeds
as a proxy for the hackathon). Uses a Raspberry Pi Camera V2 and a YOLOv8 Nano model.
"""

import time
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import cv2
    from ultralytics import YOLO
except ImportError as e:
    logger.warning("Vision engine dependencies not met: %s", e)
    cv2 = None
    YOLO = None

class VarroaVisionEngine:
    def __init__(self, model_path: str = "ai_module/varroa_nano.pt"):
        self._model_path = Path(model_path)
        self._model = None
        self.available = False

        if cv2 is not None and YOLO is not None:
            try:
                # Load the YOLO model (we don't strictly check for the file here because 
                # ultralytics might try to download or create a default if not found, 
                # but it's best if the user places varroa_nano.pt there).
                if not self._model_path.exists():
                    logger.warning("YOLO model file not found at %s. Inference will fail if it's not downloaded.", self._model_path)
                
                self._model = YOLO(str(self._model_path))
                self.available = True
                logger.info("VarroaVisionEngine loaded YOLO model from %s", self._model_path)
            except Exception as e:
                logger.error("Failed to load YOLO model: %s", e)
        else:
            logger.warning("OpenCV or Ultralytics not installed. VarroaVisionEngine disabled.")

    def detect_mites(self, conf: float = 0.25) -> dict:
        """
        Briefly opens the camera, reads one frame, runs inference to count
        mites (or seeds), and releases the camera immediately.
        Returns a dict: {"mite_count": int, "available": bool}
        """
        result_payload = {"mite_count": 0, "available": False}
        
        if not self.available or self._model is None:
            return result_payload
        
        frame = None
        
        # 1. Try native Raspberry Pi 5 libcamera stack (rpicam-jpeg or libcamera-jpeg)
        import subprocess
        import numpy as np
        
        for cmd in ["rpicam-jpeg", "libcamera-jpeg"]:
            try:
                # -t 100: wait 100ms for exposure to settle
                # -o -: output to stdout
                # --nopreview: don't show preview window
                res = subprocess.run([cmd, "-t", "100", "-o", "-", "--nopreview", "--width", "1920", "--height", "1080"], 
                                     capture_output=True, check=False)
                if res.returncode == 0 and len(res.stdout) > 1024:
                    image_array = np.frombuffer(res.stdout, dtype=np.uint8)
                    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    break
            except FileNotFoundError:
                continue
                
        # 2. Fallback to OpenCV V4L2 if libcamera commands failed or not found
        if frame is None:
            cap = None
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    ret, frame_cap = cap.read()
                    if ret:
                        frame = frame_cap
            finally:
                if cap is not None:
                    cap.release()

        if frame is None:
            logger.error("Failed to capture frame from any camera backend.")
            return result_payload
            
        try:
            # Run inference
            results = self._model.predict(source=frame, conf=conf, verbose=False)
            
            # Count detected bounding boxes
            count = 0
            if results and len(results) > 0:
                count = len(results[0].boxes)
                
            result_payload["mite_count"] = count
            result_payload["available"] = True
            
        except Exception as e:
            logger.error("Error during mite detection inference: %s", e)
                
        return result_payload

    def detect_mites_from_image(self, image_path: str, conf: float = 0.25) -> dict:
        """
        Runs inference on a static image file.
        Returns a dict: {"mite_count": int, "available": bool}
        """
        result_payload = {"mite_count": 0, "available": False}
        
        if not self.available or self._model is None:
            return result_payload
            
        try:
            frame = cv2.imread(image_path)
            if frame is None:
                logger.error("Could not read image file: %s", image_path)
                return result_payload
                
            results = self._model.predict(source=frame, conf=conf, verbose=False)
            
            count = 0
            if results and len(results) > 0:
                count = len(results[0].boxes)
                
            result_payload["mite_count"] = count
            result_payload["available"] = True
            
        except Exception as e:
            logger.error("Error during static image inference: %s", e)
            
        return result_payload
