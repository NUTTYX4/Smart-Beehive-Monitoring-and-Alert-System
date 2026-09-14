import cv2
import os
import sys
import subprocess
import numpy as np
from pathlib import Path

SAVE_DIR = Path(__file__).parent / 'dataset' / 'images'
SAVE_DIR.mkdir(parents=True, exist_ok=True)

print("Starting native Pi 5 camera stream (bypassing VideoCapture)...")

# Detect whether to use rpicam-vid or libcamera-vid
cmd_base = "rpicam-vid"
if subprocess.run(["which", "rpicam-vid"], capture_output=True).returncode != 0:
    cmd_base = "libcamera-vid"

# We use 1920x1080 because the IMX219 driver on Pi 5 often times out on 640x480 crops.
# We will just resize it to 640x480 in OpenCV!
cmd = [
    cmd_base,
    "-t", "0",
    "--codec", "mjpeg",
    "--width", "1920",
    "--height", "1080",
    "--framerate", "15",
    "--nopreview",
    "-o", "-"
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=sys.stderr)

bytes_data = b''
img_count = len(list(SAVE_DIR.glob('*.jpg')))
print(f"✅ Camera active. Found {img_count} existing images in {SAVE_DIR.absolute()}")
print("INSTRUCTIONS:")
print("- Press 'SPACEBAR' to capture and save an image.")
print("- Press 'ESC' or 'q' to close the window.")

try:
    while True:
        chunk = process.stdout.read(8192)
        if not chunk:
            print("❌ Camera stream ended unexpectedly.")
            break
        bytes_data += chunk
        
        # Find start and end of JPEG frame
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            
            # Decode JPEG into OpenCV frame
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Resize the 1080p frame down to 640x480 for our dataset
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
finally:
    process.terminate()
    cv2.destroyAllWindows()
