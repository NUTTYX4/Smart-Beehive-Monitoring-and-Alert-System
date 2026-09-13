import os
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description='Train YOLOv8 model for Varroa Mite Detection')
    parser.add_argument('--data', type=str, default='dataset.yaml', help='Path to dataset.yaml')
    parser.add_argument('--epochs', type=int, default=50, help='Number of epochs to train')
    parser.add_argument('--output', type=str, default='varroa_nano.pt', help='Output model name')
    args = parser.parse_args()

    print('=======================================')
    print(' Varroa Mite YOLO Training Script')
    print('=======================================')
    
    if not os.path.exists(args.data):
        print(f'Error: Could not find dataset config file {args.data}.')
        print('Please make sure you have labeled your images and created the dataset.yaml file.')
        return
        
    print('Loading YOLOv8 Nano base model...')
    model = YOLO('yolov8n.pt')  # load a pretrained model (recommended for training)
    
    print(f'Starting training for {args.epochs} epochs...')
    # Train the model
    results = model.train(data=args.data, epochs=args.epochs, imgsz=640)
    
    print('Training complete! Saving model...')
    # Usually Ultralytics saves to runs/detect/train/weights/best.pt
    # We can copy it to our desired output path
    best_model_path = 'runs/detect/train/weights/best.pt'
    if os.path.exists(best_model_path):
        import shutil
        shutil.copy(best_model_path, args.output)
        print(f'Successfully saved optimized model to {args.output}')
    else:
        print('Warning: Could not find best.pt in the runs folder. Check the ultralytics output logs.')

if __name__ == '__main__':
    main()
