#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_module/camera_model/collect_dataset.py
==========================================
Varroa Mite Dataset Collector -- Raspberry Pi 4 Edition.

Uses standard OpenCV VideoCapture (V4L2) — no libcamerify,
no Picamera2, no subprocess wrappers required.

Folder layout created automatically:
    ai_module/camera_model/vision_dataset/raw/  <- JPEG frames saved here

Controls (click the preview window to focus it first):
    SPACE  -- save the current frame
    q / ESC -- quit

Run:
    python3 ai_module/camera_model/collect_dataset.py
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = Path(__file__).parent / "vision_dataset" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CAPTURE_W    = 640
CAPTURE_H    = 480
CAM_INDEX    = 0
WINDOW_TITLE = "BeeHive | Varroa Mite Dataset Collector  [SPACE=save  Q=quit]"

# ---------------------------------------------------------------------------
def count_existing() -> int:
    return len(list(RAW_DIR.glob("mite_*.jpg")))


def draw_hud(frame: np.ndarray, count: int) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 42), (w, h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
    cv2.putText(
        frame,
        f"Saved: {count}   |   SPACE = capture    Q = quit",
        (10, h - 12),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 120), 1, cv2.LINE_AA,
    )
    return frame


def flash_saved(frame: np.ndarray, name: str) -> np.ndarray:
    out = frame.copy()
    cv2.putText(
        out, f"SAVED -- {name}", (10, 38),
        cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA,
    )
    return out


# ---------------------------------------------------------------------------
def main() -> None:
    print("Opening camera (/dev/video0 via V4L2)...")

    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        # Fallback: let OpenCV choose a backend (works on Pi 4 with legacy stack)
        cap = cv2.VideoCapture(CAM_INDEX)

    if not cap.isOpened():
        print("ERROR: Cannot open camera at index", CAM_INDEX)
        print("Check that the camera ribbon is seated and 'raspi-config' has the camera enabled.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # minimise preview lag

    count = count_existing()
    print(f"Camera live at {CAPTURE_W}x{CAPTURE_H}.")
    print(f"Saving to    : {RAW_DIR.resolve()}")
    print(f"Images so far: {count}")
    print("Controls     : SPACE = capture   Q/ESC = quit\n")

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, CAPTURE_W, CAPTURE_H)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Missed frame — retrying.")
                time.sleep(0.02)
                continue

            display = draw_hud(frame, count)
            cv2.imshow(WINDOW_TITLE, display)

            key = cv2.waitKey(1) & 0xFF

            if key in (ord('q'), 27):        # Q or ESC
                print("\nQuitting...")
                break

            if key == 32:                    # SPACE
                ts   = int(time.time() * 1000)
                name = f"mite_{ts}.jpg"
                path = RAW_DIR / name
                cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                count += 1
                print(f"  [{count:>4}]  Saved  {name}")

                # Flash confirmation for 350 ms
                cv2.imshow(WINDOW_TITLE, flash_saved(display, name))
                cv2.waitKey(350)

                if count % 15 == 0:
                    print("\n  *** Rearrange the mites/seeds for variety! ***\n")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nDone. {count} images saved to {RAW_DIR.resolve()}")


if __name__ == "__main__":
    main()
