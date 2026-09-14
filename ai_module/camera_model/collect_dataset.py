#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_module/camera_model/collect_dataset.py
==========================================
Varroa Mite Dataset Collector -- Raspberry Pi 5 Edition
Uses Picamera2 (the official Pi 5 library) to stream a
live preview, then captures full-resolution frames on demand.

Folder structure created automatically:
    ai_module/camera_model/vision_dataset/
        raw/        <- full-res captured frames saved here

Controls (click the live preview window first):
    SPACE  -- capture and save current frame
    q/ESC  -- quit safely

Usage:
    python3 ai_module/camera_model/collect_dataset.py
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent / "vision_dataset"
RAW_DIR  = BASE_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PREVIEW_RES  = (640, 480)
CAPTURE_RES  = (1920, 1080)
WINDOW_TITLE = "BeeHive | Varroa Mite Dataset Collector  [SPACE=save  Q=quit]"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def count_existing() -> int:
    return len(list(RAW_DIR.glob("mite_*.jpg")))


def overlay_hud(frame: np.ndarray, count: int) -> np.ndarray:
    """Burn a minimal HUD onto the preview frame."""
    h, w = frame.shape[:2]
    bar = frame.copy()
    cv2.rectangle(bar, (0, h - 45), (w, h), (0, 0, 0), -1)
    frame = cv2.addWeighted(bar, 0.55, frame, 0.45, 0)
    cv2.putText(frame,
                f"Saved: {count}  |  SPACE = capture    Q = quit",
                (12, h - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 120), 1,
                cv2.LINE_AA)
    return frame


def flash_saved(frame: np.ndarray, name: str) -> np.ndarray:
    """Flash a green SAVED banner on a copy of the frame."""
    out = frame.copy()
    cv2.putText(out, f"SAVED  {name}", (12, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 80), 2, cv2.LINE_AA)
    return out


# ---------------------------------------------------------------------------
# Main -- Picamera2 (official Pi 5 library)
# ---------------------------------------------------------------------------
def run_picamera2() -> None:
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("ERROR: Picamera2 is not installed.")
        print("Install it with:  sudo apt install python3-picamera2")
        sys.exit(1)

    print("Initialising Picamera2 ...")
    cam = Picamera2()

    # Dual-stream config: lores for live preview, main for full-res captures
    preview_cfg = cam.create_video_configuration(
        main={"size": CAPTURE_RES, "format": "RGB888"},
        lores={"size": PREVIEW_RES, "format": "YUV420"},
        display="lores"
    )
    cam.configure(preview_cfg)
    cam.start()
    time.sleep(1)  # let auto-exposure settle

    count = count_existing()
    print(f"Camera live. Dataset already contains {count} images.")
    print(f"Saving to: {RAW_DIR.resolve()}")
    print("Controls  -- SPACE: capture | Q / ESC: quit")

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, *PREVIEW_RES)

    try:
        while True:
            # Grab the low-res YUV preview buffer (fast, no disk I/O)
            yuv = cam.capture_array("lores")
            bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV420p2BGR)
            bgr = cv2.resize(bgr, PREVIEW_RES)

            display = overlay_hud(bgr, count)
            cv2.imshow(WINDOW_TITLE, display)

            key = cv2.waitKey(1) & 0xFF

            if key in (ord('q'), 27):  # Q or ESC
                print("Quitting...")
                break

            if key == 32:  # SPACE -- capture
                # Pull a full-res RGB frame from the main stream
                full_rgb = cam.capture_array("main")
                full_bgr = cv2.cvtColor(full_rgb, cv2.COLOR_RGB2BGR)

                ts   = int(time.time() * 1000)
                name = f"mite_{ts}.jpg"
                path = RAW_DIR / name
                cv2.imwrite(str(path), full_bgr,
                            [cv2.IMWRITE_JPEG_QUALITY, 95])

                count += 1
                print(f"  [{count:>4}]  Saved  {name}")

                # Flash confirmation on screen for 400 ms
                cv2.imshow(WINDOW_TITLE, flash_saved(display, name))
                cv2.waitKey(400)

                if count % 15 == 0:
                    print("\n  *** Rearrange the mites/seeds for more variety! ***\n")

    finally:
        cam.stop()
        cam.close()
        cv2.destroyAllWindows()
        print(f"\nDone. {count} images saved to {RAW_DIR.resolve()}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_picamera2()
