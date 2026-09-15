# -*- coding: utf-8 -*-
"""
ai_module/camera_model/vision_engine.py
========================================
Varroa mite vision engine — Raspberry Pi 4 Edition.

Architecture (Pi 4 optimised):
  - Live feed  : cv2.VideoCapture (V4L2, /dev/video0) runs continuously in a
                 daemon thread so the display never freezes.
  - AI inference: triggered in a SECOND daemon thread on a configurable
                 interval (default 60 s) so the CPU never pins at 100 %.
  - main thread : call `get_latest_result()` at any time — always instant,
                 never blocking, never crashes the monitor loop.

No libcamerify, no Picamera2, no subprocess wrappers needed on Pi 4.
"""

import threading
import time
from pathlib import Path
from typing import Dict

from utils.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# Optional heavy imports
# --------------------------------------------------------------------------
try:
    import cv2
    _CV2_OK = True
except ImportError:
    cv2 = None  # type: ignore
    _CV2_OK = False
    logger.warning("OpenCV not installed — VarroaVisionEngine disabled.")

try:
    from ultralytics import YOLO
    _YOLO_OK = True
except ImportError:
    YOLO = None  # type: ignore
    _YOLO_OK = False
    logger.warning("Ultralytics not installed — YOLO inference disabled.")


# --------------------------------------------------------------------------
# Constants (can be overridden via constructor kwargs)
# --------------------------------------------------------------------------
_DEFAULT_MODEL_PATH  = "ai_module/camera_model/varroa_nano.pt"
_DEFAULT_CAM_INDEX   = 0
_DEFAULT_INFER_EVERY = 60      # seconds between AI scans
_CAPTURE_W           = 1280
_CAPTURE_H           = 720
_CONF_THRESHOLD      = 0.25


# --------------------------------------------------------------------------
class VarroaVisionEngine:
    """
    Thread-safe, non-blocking vision engine for Raspberry Pi 4.

    Usage
    -----
    engine = VarroaVisionEngine()
    engine.start()                        # call once — starts background threads

    result = engine.get_latest_result()   # always returns instantly
    # {"mite_count": int, "available": bool, "last_scan_ts": float | None}

    engine.stop()                         # clean shutdown
    """

    def __init__(self,
                 model_path: str = _DEFAULT_MODEL_PATH,
                 cam_index: int  = _DEFAULT_CAM_INDEX,
                 infer_every: float = _DEFAULT_INFER_EVERY):

        self._model_path  = Path(model_path)
        self._cam_index   = cam_index
        self._infer_every = infer_every

        self._model   = None
        self.available = False          # True once YOLO model is loaded

        self._cap     = None            # cv2.VideoCapture, owned by _feed_thread
        self._lock    = threading.Lock()
        self._stop_event = threading.Event()

        # Shared state — written by inference thread, read by caller
        self._latest_frame  = None
        self._latest_result: Dict = {
            "mite_count": 0,
            "available": False,
            "last_scan_ts": None,
        }

        self._feed_thread  : threading.Thread | None = None
        self._infer_thread : threading.Thread | None = None

        self._load_model()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def _load_model(self) -> None:
        if not (_CV2_OK and _YOLO_OK):
            return
        if not self._model_path.exists():
            logger.warning(
                "YOLO model not found at %s — inference disabled until model is trained.",
                self._model_path,
            )
            return
        try:
            self._model = YOLO(str(self._model_path))
            self.available = True
            logger.info("VarroaVisionEngine: YOLO model loaded from %s", self._model_path)
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Launch background camera-feed and inference threads."""
        if not _CV2_OK:
            logger.warning("OpenCV unavailable — VarroaVisionEngine not started.")
            return

        self._feed_thread = threading.Thread(
            target=self._feed_loop, name="vision-feed", daemon=True
        )
        self._infer_thread = threading.Thread(
            target=self._inference_loop, name="vision-infer", daemon=True
        )
        self._feed_thread.start()
        self._infer_thread.start()
        logger.info("VarroaVisionEngine started (infer every %.0fs).", self._infer_every)

    def stop(self) -> None:
        """Signal both threads to exit and wait up to 3 s each."""
        self._stop_event.set()
        for t in (self._feed_thread, self._infer_thread):
            if t and t.is_alive():
                t.join(timeout=3)
        if self._cap and self._cap.isOpened():
            self._cap.release()
        logger.info("VarroaVisionEngine stopped.")

    def get_latest_result(self) -> Dict:
        """Return the most recent mite-count result (always instant)."""
        with self._lock:
            return dict(self._latest_result)

    # Convenience alias so monitor.py can keep calling detect_mites()
    def detect_mites(self, conf: float = _CONF_THRESHOLD) -> Dict:
        return self.get_latest_result()

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------
    def _open_camera(self) -> bool:
        """
        Open /dev/video0 via V4L2 (standard Pi 4 path).
        Returns True on success.
        """
        self._cap = cv2.VideoCapture(self._cam_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            # Fallback: let OpenCV pick any available backend
            self._cap = cv2.VideoCapture(self._cam_index)
        if not self._cap.isOpened():
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  _CAPTURE_W)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, _CAPTURE_H)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        # Reduce internal buffer to 1 frame — keeps preview latency minimal
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return True

    def _feed_loop(self) -> None:
        """
        Continuously reads frames from the camera.
        Keeps self._latest_frame fresh for the inference thread.
        Never runs YOLO here — CPU stays well under budget.
        """
        if not self._open_camera():
            logger.error(
                "VarroaVisionEngine: cannot open camera at index %d. "
                "Check that the HP W200 USB webcam is plugged into a USB 3.0 port and /dev/video0 exists.",
                self._cam_index,
            )
            return

        logger.info("VarroaVisionEngine: camera feed running at %dx%d.",
                    _CAPTURE_W, _CAPTURE_H)

        while not self._stop_event.is_set():
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("VarroaVisionEngine: missed a frame — retrying.")
                time.sleep(0.05)
                continue
            with self._lock:
                self._latest_frame = frame

        self._cap.release()

    def _inference_loop(self) -> None:
        """
        Waits `infer_every` seconds, grabs the latest frame,
        runs YOLO Nano, and writes the result to `_latest_result`.
        Completely decoupled from the feed — the feed always stays smooth.
        """
        if not self.available:
            logger.info(
                "VarroaVisionEngine: inference loop idle (no model loaded)."
            )
            return

        # Wait for the feed thread to deliver the first frame
        for _ in range(50):                      # up to 5 s
            if self._stop_event.is_set():
                return
            with self._lock:
                has_frame = self._latest_frame is not None
            if has_frame:
                break
            time.sleep(0.1)

        while not self._stop_event.is_set():
            # Sleep in small chunks so we can respond to stop_event quickly
            for _ in range(int(self._infer_every * 10)):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)

            with self._lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is None:
                continue

            try:
                results = self._model.predict(
                    source=frame,
                    conf=_CONF_THRESHOLD,
                    verbose=False,
                    device="cpu",   # force CPU — no CUDA on Pi 4
                    half=False,     # half-precision only useful on GPU
                )
                count = len(results[0].boxes) if results else 0
                ts    = time.time()

                with self._lock:
                    self._latest_result = {
                        "mite_count": count,
                        "available":  True,
                        "last_scan_ts": ts,
                    }

                logger.info(
                    "VarroaVisionEngine: scan complete — %d mite(s) detected.", count
                )
            except Exception as exc:
                logger.error("VarroaVisionEngine inference error: %s", exc)

    # ------------------------------------------------------------------
    # Legacy static-image helper (unchanged)
    # ------------------------------------------------------------------
    def detect_mites_from_image(self, image_path: str, conf: float = _CONF_THRESHOLD) -> Dict:
        """Run inference on a saved image file (used by test_vision.py)."""
        result_payload = {"mite_count": 0, "available": False}
        if not (self.available and _CV2_OK):
            return result_payload
        try:
            frame = cv2.imread(image_path)
            if frame is None:
                logger.error("Cannot read image: %s", image_path)
                return result_payload
            results = self._model.predict(source=frame, conf=conf, verbose=False)
            count   = len(results[0].boxes) if results else 0
            result_payload.update({"mite_count": count, "available": True})
        except Exception as exc:
            logger.error("Static-image inference error: %s", exc)
        return result_payload

