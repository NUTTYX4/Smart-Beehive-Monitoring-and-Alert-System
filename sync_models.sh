#!/bin/bash
# sync_models.sh
# Easily push your trained models to GitHub!

echo "========================================="
echo "   BeeHive AI Model GitHub Sync Tool"
echo "========================================="

# 1. Pull the latest code first to avoid conflicts
echo "Pulling latest changes from GitHub..."
git pull origin main

# 2. Add the models
echo "Staging AI models..."
git add ai_module/camera_model/*.pt
git add ai_module/audio_model/*.tflite

# 3. Commit the changes
read -p "Enter a commit message for your new model (e.g., 'Update Varroa model'): " commit_msg
git commit -m "$commit_msg"

# 4. Push to GitHub
echo "Pushing models to GitHub..."
git push origin main

echo "Done! Your models are safely synced to GitHub."
