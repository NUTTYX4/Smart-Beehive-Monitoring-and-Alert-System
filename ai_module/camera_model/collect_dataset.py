import cv2
import os
import sys
import subprocess
from pathlib import Path
import shutil

SAVE_DIR = Path(__file__).parent / 'dataset' / 'images'
SAVE_DIR.mkdir(parents=True, exist_ok=True)

print("✅ Initializing fail-safe dataset collector (Hardware Reset Mode)...")
img_count = len(list(SAVE_DIR.glob('*.jpg')))
print(f"✅ Found {img_count} existing images in {SAVE_DIR.absolute()}")
print("INSTRUCTIONS:")
print("- The camera will update 1-2 times per second (this prevents hardware crashes).")
print("- Press 'SPACEBAR' to capture and save an image.")
print("- Press 'ESC' or 'q' to close the window.")

while True:
    output_file = SAVE_DIR / "temp.jpg"
    
    # We use -t 400 to give the camera 400ms to adjust brightness/exposure
    # Running a fresh hardware capture every frame bypasses all continuous stream bugs!
    cmd = ["rpicam-jpeg", "-o", str(output_file), "-t", "400", "--width", "1920", "--height", "1080", "--nopreview"]
    subprocess.run(cmd, capture_output=True)
    
    if output_file.exists():
        frame = cv2.imread(str(output_file))
        if frame is not None:
            # Resize for optimal UI scaling and YOLO processing
            frame = cv2.resize(frame, (640, 480))
            cv2.imshow("🐝 Live Mite Dataset Collector", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == 32: # Spacebar
        final_file = SAVE_DIR / f"mite_frame_{img_count:03d}.jpg"
        if output_file.exists():
            shutil.copy(str(output_file), str(final_file))
            print(f"✅ Saved: {final_file.name}")
            img_count += 1
            if img_count % 15 == 0:
                print("\n🔄 ACTION: Rearrange the seeds to add variety!\n")
    elif key == 27 or key == ord('q'): # ESC or q
        break

if output_file.exists():
    output_file.unlink()
cv2.destroyAllWindows()
