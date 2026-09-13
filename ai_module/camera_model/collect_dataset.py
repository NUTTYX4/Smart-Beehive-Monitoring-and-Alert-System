import cv2
import os
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

OUTPUT_DIR = Path(__file__).parent / 'dataset' / 'images'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Global variable to share the camera feed between the web server and the save button
latest_frame = None

# --- Web Server Logic ---
class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b\"\"\"
            <html>
            <body style="background:#0f172a; color:white; text-align:center; font-family:sans-serif;">
                <h2>🐝 Live Dataset Framing</h2>
                <p>Keep this browser tab open. Press <b>ENTER</b> in your terminal to snap the photo.</p>
                <img src="/stream.mjpg" style="border:3px solid #f59e0b; border-radius:8px; max-width:90vw;">
            </body>
            </html>
            \"\"\")
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    if latest_frame is not None:
                        _, jpeg = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(jpeg)))
                        self.end_headers()
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b'\r\n')
                    time.sleep(0.1) # Limits stream to ~10 FPS to save CPU
            except Exception:
                pass

def start_server():
    HTTPServer(('0.0.0.0', 8000), StreamingHandler).serve_forever()

# --- Camera Capture Logic ---
def update_camera():
    global latest_frame
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    while True:
        ret, frame = cap.read()
        if ret:
            latest_frame = frame
        time.sleep(0.03)

def main():
    global latest_frame
    # 1. Start the background threads
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=update_camera, daemon=True).start()

    # 2. Main Terminal Input Loop
    img_count = len(list(OUTPUT_DIR.glob('*.jpg')))
    print("=====================================================")
    print("✅ Live camera web server active!")
    print("Open your laptop/phone browser and go to:")
    print("➡️  http://<YOUR_PI_IP>:8000")
    print(f"Images will be saved to: {OUTPUT_DIR.absolute()}")
    print("=====================================================")

    # Wait a moment for the camera to warm up
    time.sleep(2)

    try:
        while True:
            input(f"Press ENTER to capture image #{img_count + 1} (or Ctrl+C to stop)...")
            if latest_frame is not None:
                timestamp = int(time.time() * 1000)
                filename = OUTPUT_DIR / f"mite_frame_{timestamp}.jpg"
                cv2.imwrite(str(filename), latest_frame)
                print(f"   ✅ Saved: {filename.name}")
                img_count += 1
                
                # Remind the user to add variety every 15 images
                if img_count % 15 == 0:
                    print("\n   🔄 ACTION: Rearrange the seeds to add variety to your dataset!\n")
            else:
                print("   ⏳ Waiting for camera to initialize...")
    except KeyboardInterrupt:
        print("\n🛑 Collection stopped safely.")

if __name__ == '__main__':
    main()
