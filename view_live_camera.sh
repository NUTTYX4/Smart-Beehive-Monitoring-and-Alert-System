#!/bin/bash
# view_live_camera.sh
# -------------------
# Helper script to view the live webcam feed with the mite counter overlay.

echo "=========================================="
echo "🐝 Starting Live Mite Monitor Feed..."
echo "=========================================="

echo "Launching live feed... (Press 'Q' or 'Esc' in the video window to quit)"
echo "Note: If the camera fails to open, ensure the monitor script is stopped in the Telegram Bot."

# Activate virtual environment if it exists in the current directory
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the test script we created earlier which has the mite counter!
python3 test/test_model_raspi.py

echo ""
echo "=========================================="
echo "✅ Live feed closed."
echo "=========================================="
