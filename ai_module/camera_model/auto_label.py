#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_label.py
=============
Automatically detects dark objects (seeds/mites) on a light background
using adaptive thresholding + contour detection, and generates YOLO-format
label files (.txt) for every image in the raw dataset.

Output:
    vision_dataset/
        images/
            train/   (80%)
            val/     (20%)
        labels/
            train/
            val/
        dataset.yaml
"""

import os
import sys
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE       = Path(__file__).parent / "vision_dataset"
RAW_DIR    = BASE / "raw"
IMG_TRAIN  = BASE / "images" / "train"
IMG_VAL    = BASE / "images" / "val"
LBL_TRAIN  = BASE / "labels" / "train"
LBL_VAL    = BASE / "labels" / "val"
YAML_PATH  = BASE / "dataset.yaml"

TRAIN_RATIO = 0.80
MIN_AREA    = 30       # pixels² — ignore noise smaller than this
MAX_AREA    = 8000     # pixels² — ignore huge artefacts (edges of paper, etc.)
PAD_PX      = 4        # extra pixels around each detected blob for the bbox
CLASS_ID    = 0        # single class: varroa_mite
CLASS_NAME  = "varroa_mite"

# ---------------------------------------------------------------------------
def auto_detect_objects(img_path: str):
    """
    Detect dark blobs on a light background.
    Returns a list of YOLO-format annotations: [(class_id, cx, cy, w, h), ...]
    All values normalised to [0, 1].
    """
    img = cv2.imread(img_path)
    if img is None:
        return []

    h, w = img.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    # Adaptive threshold — excellent for uneven lighting
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, 15
    )

    # Morphological close to fill small holes inside seeds
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    annotations = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA or area > MAX_AREA:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)

        # Add padding
        x  = max(0, x - PAD_PX)
        y  = max(0, y - PAD_PX)
        bw = min(w - x, bw + 2 * PAD_PX)
        bh = min(h - y, bh + 2 * PAD_PX)

        # Convert to YOLO normalised format (center_x, center_y, width, height)
        cx = (x + bw / 2) / w
        cy = (y + bh / 2) / h
        nw = bw / w
        nh = bh / h

        annotations.append((CLASS_ID, cx, cy, nw, nh))

    return annotations


def write_label_file(label_path: Path, annotations: list):
    with open(label_path, "w") as f:
        for cls, cx, cy, w, h in annotations:
            f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def main():
    print("=" * 60)
    print("  Varroa Mite Auto-Labeller + Dataset Builder")
    print("=" * 60)

    # Gather all images
    images = sorted(RAW_DIR.glob("mite_*.jpg"))
    if not images:
        print(f"  ERROR: No images found in {RAW_DIR}")
        sys.exit(1)
    print(f"  Found {len(images)} raw images in {RAW_DIR}")

    # Clean previous dataset split
    for d in (IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # Shuffle and split
    random.seed(42)
    shuffled = list(images)
    random.shuffle(shuffled)
    split_idx = int(len(shuffled) * TRAIN_RATIO)
    train_set = shuffled[:split_idx]
    val_set   = shuffled[split_idx:]

    print(f"  Train : {len(train_set)} images")
    print(f"  Val   : {len(val_set)} images")
    print()

    total_objects = 0
    skipped = 0

    for subset_name, subset, img_dir, lbl_dir in [
        ("train", train_set, IMG_TRAIN, LBL_TRAIN),
        ("val",   val_set,   IMG_VAL,   LBL_VAL),
    ]:
        for img_path in subset:
            annotations = auto_detect_objects(str(img_path))

            if not annotations:
                skipped += 1
                continue

            total_objects += len(annotations)

            # Copy image
            dst_img = img_dir / img_path.name
            shutil.copy2(str(img_path), str(dst_img))

            # Write label
            lbl_name = img_path.stem + ".txt"
            write_label_file(lbl_dir / lbl_name, annotations)

        print(f"  [{subset_name:>5}] Processed {len(subset)} images")

    # Write dataset.yaml
    yaml_content = f"""# YOLOv8 Dataset Configuration — Auto-generated
# Do not edit manually; re-run auto_label.py to regenerate.

path: {BASE.resolve().as_posix()}
train: images/train
val: images/val

nc: 1
names:
  0: {CLASS_NAME}
"""
    with open(YAML_PATH, "w") as f:
        f.write(yaml_content)

    print()
    print(f"  Total objects labelled : {total_objects}")
    print(f"  Images skipped (empty): {skipped}")
    print(f"  dataset.yaml written  : {YAML_PATH.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
