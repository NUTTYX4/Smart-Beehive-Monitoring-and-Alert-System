import cv2
import os
from pathlib import Path

SAVE_DIR = Path(__file__).parent / 'dataset' / 'images'
SAVE_DIR.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("❌ Camera failed to open. (Run with libcamerify if needed)")
    exit()

img_count = len(list(SAVE_DIR.glob('*.jpg')))
print(f"✅ Camera active. Found {img_count} existing images in {SAVE_DIR.absolute()}")
print("INSTRUCTIONS:")
print("- Press 'SPACEBAR' to capture and save an image.")
print("- Press 'ESC' or 'q' to close the window.")

while True:
    ret, frame = cap.read()
    if not ret: continue

    # Display the live feed natively on your desktop
    cv2.imshow("🐝 Live Mite Dataset Collector", frame)
    
    # Listen for keyboard presses (1ms delay)
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

cap.release()
cv2.destroyAllWindows()
