import os
import shutil
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description='Train YOLOv8 model for Varroa Mite Detection (Extended/Practical)')
    parser.add_argument('--data', type=str, default='dataset_v2.yaml', help='Path to dataset.yaml')
    parser.add_argument('--epochs', type=int, default=1000, help='Number of epochs to train (use a high number if using time limit)')
    parser.add_argument('--time', type=float, default=3.0, help='Maximum training time in hours')
    parser.add_argument('--output', type=str, default='varroa_nano_v2.pt', help='Output PyTorch model name')
    parser.add_argument('--onnx_output', type=str, default='varroa_nano_v2.onnx', help='Output ONNX model name (keeps original varroa_nano.onnx safe as backup)')
    args = parser.parse_args()

    print('=======================================')
    print(' Varroa Mite YOLO Extended Training')
    print('=======================================')
    
    if not os.path.exists(args.data):
        print(f'Error: Could not find dataset config file {args.data}.')
        print('Please make sure you have labeled your images and created the dataset.yaml file.')
        return
        
    print('Loading YOLOv8 Nano base model...')
    model = YOLO('yolov8n.pt')  # load a pretrained model
    
    print(f'Starting training for a maximum of {args.time} hours or {args.epochs} epochs...')
    print('Applying robust data augmentations to improve practical accuracy...')
    
    # Train the model with extended augmentations
    results = model.train(
        data=args.data, 
        epochs=args.epochs,
        time=args.time,       # Ultralytics supports training time limits directly
        imgsz=640,
        patience=50,          # Stop early if no improvement for 50 epochs
        batch=16,             # Adjust if running out of memory
        # Data Augmentations
        hsv_h=0.015,          # Image HSV-Hue augmentation
        hsv_s=0.7,            # Image HSV-Saturation augmentation
        hsv_v=0.4,            # Image HSV-Value augmentation
        degrees=10.0,         # Image rotation (+/- deg)
        translate=0.1,        # Image translation (+/- fraction)
        scale=0.5,            # Image scale (+/- gain)
        fliplr=0.5,           # Image flip left-right (probability)
        mosaic=1.0            # Image mosaic (probability)
    )
    
    print('Training complete! Saving PyTorch model...')
    best_model_path = 'runs/detect/train/weights/best.pt'
    
    # Check if the run was saved in a different folder like train2, train3, etc.
    # Ultralytics usually saves to the latest run directory.
    latest_run = results.save_dir if hasattr(results, 'save_dir') else 'runs/detect/train'
    best_model_path = os.path.join(latest_run, 'weights', 'best.pt')

    if os.path.exists(best_model_path):
        shutil.copy(best_model_path, args.output)
        print(f'Successfully saved optimized PyTorch model to {args.output}')
        
        print('Exporting to ONNX for production Edge AI deployment...')
        # Load the best model to export it
        best_model = YOLO(args.output)
        best_model.export(format='onnx', imgsz=640)
        
        # The exported ONNX is saved alongside the PT model, so let's move it to the requested path
        exported_onnx = args.output.replace('.pt', '.onnx')
        if os.path.exists(exported_onnx):
            shutil.move(exported_onnx, args.onnx_output)
            print(f'✅ Successfully exported and saved ONNX model to {args.onnx_output}')
            print('Note: The original varroa_nano.onnx remains untouched as a safe backup.')
        else:
            print('Error: ONNX export failed or file not found.')
    else:
        print(f'Warning: Could not find best.pt in {latest_run}. Check the output logs.')

if __name__ == '__main__':
    main()
