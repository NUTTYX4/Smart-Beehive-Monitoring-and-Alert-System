#!/bin/bash
# view_live_camera.sh
# -------------------
# Helper script to view the live webcam feed with the mite counter overlay.
# This safely pauses the main beehive background service so the camera isn't locked,
# opens the live UI, and automatically restarts the service when you close the window.

echo "=========================================="
echo "🐝 Starting Live Mite Monitor Feed..."
echo "=========================================="
echo "1. Temporarily stopping background beehive service to release the camera..."
sudo systemctl stop beehive.service

echo "2. Launching live feed... (Press 'Q' or 'Esc' in the video window to quit)"

# Activate virtual environment if it exists in the current directory
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the test script we created earlier which has the mite counter!
python3 test/test_model_raspi.py

echo ""
echo "3. Live feed closed. Restarting background beehive service..."
sudo systemctl start beehive.service

echo "=========================================="
echo "✅ Done! Background monitoring resumed."
echo "=========================================="
