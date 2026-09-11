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
        
        cap = None
        try:
            # Briefly open the camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Failed to open camera for mite detection.")
                return result_payload
            
            # Read a single frame
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to grab frame from camera.")
                return result_payload
            
            # Run inference
            results = self._model.predict(source=frame, conf=conf, verbose=False)
            
            # Count detected bounding boxes
            count = 0
            if results and len(results) > 0:
                count = len(results[0].boxes)
                
            result_payload["mite_count"] = count
            result_payload["available"] = True
            
        except Exception as e:
            logger.error("Error during mite detection: %s", e)
        finally:
            # Immediately release camera
            if cap is not None:
                cap.release()
                
        return result_payload
