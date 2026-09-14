import cv2
import os
import sys
import subprocess
from pathlib import Path

SAVE_DIR = Path(__file__).parent / 'dataset' / 'images'
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# FALLBACK: If Picamera2 is missing, use a subprocess loop
# ---------------------------------------------------------
def run_fallback():
    print("⚠️ Using subprocess fallback (1-2 FPS).")
    img_count = len(list(SAVE_DIR.glob('*.jpg')))
    while True:
        output_file = SAVE_DIR / "temp.jpg"
        # We know rpicam-jpeg works from your test_camera.py script!
        cmd = ["rpicam-jpeg", "-o", str(output_file), "-t", "10", "--width", "1920", "--height", "1080", "--nopreview"]
        subprocess.run(cmd, capture_output=True)
        if output_file.exists():
            frame = cv2.imread(str(output_file))
            if frame is not None:
                frame = cv2.resize(frame, (640, 480))
                cv2.imshow("🐝 Live Mite Dataset Collector (Fallback)", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 32:
            final_file = SAVE_DIR / f"mite_frame_{img_count:03d}.jpg"
            import shutil
            shutil.copy(str(output_file), str(final_file))
            print(f"✅ Saved: {final_file.name}")
            img_count += 1
        elif key == 27 or key == ord('q'):
            break
    if output_file.exists():
        output_file.unlink()
    cv2.destroyAllWindows()

# ---------------------------------------------------------
# MAIN: Use Picamera2 for native Raspberry Pi 5 support
# ---------------------------------------------------------
try:
    from picamera2 import Picamera2
except ImportError:
    print("❌ Picamera2 not found.")
    run_fallback()
    sys.exit(0)

print("✅ Initializing native Picamera2 stream for Raspberry Pi 5...")

try:
    picam2 = Picamera2()
    # Use video configuration to avoid IMX219 sensor timeout bugs
    config = picam2.create_video_configuration(main={"size": (1920, 1080)})
    picam2.configure(config)
    picam2.start()
except Exception as e:
    print(f"❌ Failed to start Picamera2: {e}")
    print("Switching to bulletproof fallback method...")
    run_fallback()
    sys.exit(1)

img_count = len(list(SAVE_DIR.glob('*.jpg')))
print(f"✅ Camera active. Found {img_count} existing images in {SAVE_DIR.absolute()}")
print("INSTRUCTIONS:")
print("- Press 'SPACEBAR' to capture and save an image.")
print("- Press 'ESC' or 'q' to close the window.")

try:
    while True:
        # Capture raw frame from GPU memory
        frame_rgb = picam2.capture_array("main")
        
        # Convert RGB to BGR for OpenCV
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        # Resize to 640x480 for dataset speed
        frame = cv2.resize(frame, (640, 480))
        
        cv2.imshow("🐝 Live Mite Dataset Collector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 32: # Spacebar
            filename = SAVE_DIR / f"mite_frame_{img_count:03d}.jpg"
            cv2.imwrite(str(filename), frame)
            print(f"✅ Saved: {filename.name}")
            img_count += 1
            if img_count % 15 == 0:
                print("\n🔄 ACTION: Rearrange the seeds to add variety!\n")
        elif key == 27 or key == ord('q'): # ESC or q
            break
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
    cv2.destroyAllWindows()
