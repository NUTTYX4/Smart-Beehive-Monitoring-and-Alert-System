import cv2
import os
import sys
import subprocess
from pathlib import Path
import shutil

SAVE_DIR = Path(__file__).parent / 'dataset' / 'images'
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def check_camera():
    print("⏳ Checking camera hardware...")
    # Fire a 10ms test shot to ensure the camera is responsive
    res = subprocess.run(
        ["rpicam-jpeg", "-o", "/dev/null", "-t", "10", "--width", "640", "--height", "480", "--nopreview"],
        capture_output=True
    )
    if res.returncode != 0:
        print("❌ ERROR: Camera is not available or is locked by another process!")
        print("Error details:", res.stderr.decode('utf-8').strip())
        print("\nTroubleshooting:")
        print("1. Run 'sudo reboot' to unlock the camera hardware.")
        print("2. Check your ribbon cable connection.")
        sys.exit(1)
    print("✅ Camera is available and connected!")

def collect_data():
    check_camera()
    
    img_count = len(list(SAVE_DIR.glob('*.jpg')))
    print(f"\n✅ Ready! Found {img_count} existing images.")
    print("=========================================")
    print("🎮 DATASET COLLECTION CONTROLS:")
    print("  [SPACEBAR] : Capture a high-res snapshot")
    print("  [y]        : Confirm and save snapshot")
    print("  [n]        : Cancel and discard snapshot")
    print("  [q] or ESC : Quit safely")
    print("  (Or press Ctrl+C in this terminal)")
    print("=========================================")
    print("Opening live feed...")
    
    window_name = "🐝 Live Mite Dataset Collector"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    while True:
        preview_file = SAVE_DIR / "preview.jpg"
        
        # 1. Grab a preview frame (Hardware reset mode, very stable)
        cmd = ["rpicam-jpeg", "-o", str(preview_file), "-t", "200", "--width", "1024", "--height", "768", "--nopreview"]
        subprocess.run(cmd, capture_output=True)
        
        if not preview_file.exists():
            continue
            
        frame = cv2.imread(str(preview_file))
        if frame is None:
            continue
            
        frame = cv2.resize(frame, (640, 480))
        
        # Add UI text to live feed
        cv2.putText(frame, "LIVE FEED - Press SPACE to capture", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(window_name, frame)
        
        # Wait 1ms for keypress
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27 or key == ord('q'): # ESC or q
            print("\n🛑 Exiting safely...")
            break
            
        elif key == 32: # SPACEBAR
            print("\n📸 Snapshot requested! Capturing high-res frame...")
            
            # Capture a high-quality frame
            capture_file = SAVE_DIR / "capture.jpg"
            cmd_hq = ["rpicam-jpeg", "-o", str(capture_file), "-t", "500", "--width", "1920", "--height", "1080", "--nopreview"]
            subprocess.run(cmd_hq, capture_output=True)
            
            if capture_file.exists():
                cap_frame = cv2.imread(str(capture_file))
                if cap_frame is not None:
                    disp_frame = cv2.resize(cap_frame, (640, 480))
                    
                    # Add confirmation text
                    cv2.putText(disp_frame, "CAPTURED! Press 'y' to save, 'n' to discard.", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                    cv2.imshow(window_name, disp_frame)
                    
                    print("❓ Press 'y' (Save) or 'n' (Discard) in the camera window...")
                    
                    # Wait infinitely for y or n
                    while True:
                        confirm_key = cv2.waitKey(0) & 0xFF
                        if confirm_key == ord('y'):
                            final_file = SAVE_DIR / f"mite_frame_{img_count:03d}.jpg"
                            shutil.copy(str(capture_file), str(final_file))
                            print(f"✅ SAVED: {final_file.name}")
                            img_count += 1
                            if img_count % 15 == 0:
                                print("\n🔄 ACTION: Please rearrange the seeds to add variety!\n")
                            break
                        elif confirm_key == ord('n'):
                            print("❌ Discarded. Returning to live feed...")
                            break
                        elif confirm_key == 27 or confirm_key == ord('q'):
                            print("\n🛑 Exiting safely...")
                            if preview_file.exists(): preview_file.unlink()
                            if capture_file.exists(): capture_file.unlink()
                            cv2.destroyAllWindows()
                            sys.exit(0)
                            
                capture_file.unlink()
                
        if preview_file.exists():
            preview_file.unlink()

if __name__ == "__main__":
    try:
        collect_data()
    except KeyboardInterrupt:
        print("\n🛑 Exited via Ctrl+C safely.")
    finally:
        cv2.destroyAllWindows()
