import cv2
import os
import time
from pathlib import Path
import subprocess
import numpy as np

OUTPUT_DIR = Path(__file__).parent / 'dataset' / 'images'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def capture_image_libcamera():
    for cmd in ['rpicam-jpeg', 'libcamera-jpeg']:
        try:
            res = subprocess.run([cmd, '-t', '100', '-o', '-', '--nopreview', '--width', '1920', '--height', '1080'], 
                                 capture_output=True, check=False)
            if res.returncode == 0 and len(res.stdout) > 1024:
                image_array = np.frombuffer(res.stdout, dtype=np.uint8)
                return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        except FileNotFoundError:
            continue
    return None

def capture_image_opencv():
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            return frame
    return None

def main():
    print('=======================================')
    print(' Varroa Mite Dataset Collection Tool')
    print('=======================================')
    print(f'Images will be saved to: {OUTPUT_DIR.absolute()}')
    print('Press [ENTER] to capture an image. Press [Ctrl+C] to exit.\n')
    
    count = 0
    while True:
        try:
            input('Press ENTER to capture image...')
            
            frame = capture_image_libcamera()
            if frame is None:
                frame = capture_image_opencv()
                
            if frame is None:
                print('Error: Could not capture image from camera.')
                continue
                
            timestamp = int(time.time() * 1000)
            filename = OUTPUT_DIR / f'mite_{timestamp}.jpg'
            cv2.imwrite(str(filename), frame)
            
            count += 1
            print(f'[{count}] Saved {filename.name}')
            
            if count % 15 == 0:
                print('\n---------------------------------------')
                print(f'Awesome! You have captured {count} images.')
                print('ACTION: Please rearrange or add more mites (seeds) to the board to vary the dataset.')
                print('---------------------------------------\n')
                
        except KeyboardInterrupt:
            print('\nExiting dataset collection. Great job!')
            break

if __name__ == '__main__':
    main()
