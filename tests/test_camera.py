import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# -- ensure project root is on sys.path when running directly --

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__file__), '..'))
import sys
"""
tests/test_camera.py
====================
Hardware diagnostic for the HP W200 USB webcam.
Opens a live desktop window — press Q or ESC to exit.

Run:
    python3 tests/test_camera.py
"""

import sys
import time
import cv2

# ---------------------------------------------------------------------------
CAM_INDEX    = 0          # /dev/video0 — change to 1 if needed
TARGET_W     = 1280
TARGET_H     = 720
TARGET_FPS   = 30
WINDOW_TITLE = "BeeHive | HP W200 Camera Test  [Q=quit]"
# ---------------------------------------------------------------------------


def _detect_camera() -> str:
    """Return a short description of the camera device."""
    import subprocess
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--device=/dev/video0", "--info"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "Card type" in line:
                return line.split(":")[-1].strip()
    except Exception:
        pass
    return "/dev/video0 (v4l2-ctl not available)"


def main() -> None:
    print("=" * 55)
    print("  BeeHive Monitor — HP W200 USB Camera Diagnostic")
    print("=" * 55)

    # ---- Detect device -------------------------------------------------
    cam_name = _detect_camera()
    print(f"  Detected : {cam_name}")

    # ---- Open camera ---------------------------------------------------
    print(f"  Opening  : /dev/video{CAM_INDEX} via V4L2 ...")
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAM_INDEX)   # backend fallback

    if not cap.isOpened():
        print(f"\n  FAIL : Cannot open /dev/video{CAM_INDEX}.")
        print("  Troubleshooting:")
        print("    1. Run:  ls /dev/video*")
        print("    2. Make sure the webcam USB cable is plugged into a USB port.")
        print("    3. Try a different USB port or cable.")
        sys.exit(1)

    # ---- Configure resolution ------------------------------------------
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  TARGET_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    actual_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"  Resolution: {actual_w} x {actual_h}  @  {actual_fps:.0f} FPS")
    print()

    # ---- Warm-up -------------------------------------------------------
    print("  Warming up (10 frames) ...")
    for _ in range(10):
        cap.read()

    # ---- Live preview loop --------------------------------------------
    print("  LIVE FEED OPEN — press  Q  or  ESC  to quit.")
    print()

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, actual_w, actual_h)

    frame_count = 0
    t_start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("  WARNING: dropped frame, retrying ...")
            time.sleep(0.02)
            continue

        frame_count += 1
        elapsed = time.time() - t_start
        live_fps = frame_count / elapsed if elapsed > 0 else 0

        # Burn live FPS counter onto frame
        cv2.putText(
            frame,
            f"HP W200  |  {actual_w}x{actual_h}  |  {live_fps:.1f} FPS  |  Press Q to quit",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 100), 2, cv2.LINE_AA,
        )

        cv2.imshow(WINDOW_TITLE, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):   # Q or ESC
            break

    # ---- Results -------------------------------------------------------
    elapsed = time.time() - t_start
    avg_fps = frame_count / elapsed if elapsed > 0 else 0

    cap.release()
    cv2.destroyAllWindows()

    print("=" * 55)
    print(f"  PASS  : Camera test completed successfully.")
    print(f"  Frames: {frame_count}  |  Duration: {elapsed:.1f}s  |  Avg FPS: {avg_fps:.1f}")
    print("=" * 55)


if __name__ == "__main__":
    main()


