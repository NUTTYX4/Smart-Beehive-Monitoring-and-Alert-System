#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_module/train_model.py
=========================
Standalone training script — run on a **PC** (not on the Pi) to produce
``bee_acoustic_model.tflite`` from clean demonstration WAV files.

Usage::

    python ai_module/train_model.py \\
        --normal  path/to/Normal.wav \\
        --triggered path/to/Triggered.wav \\
        [--epochs 50] [--output ai_module/bee_acoustic_model.tflite]

The script:
1. Slices each WAV into 2.0-second chunks.
2. Applies a 100–800 Hz Butterworth bandpass filter.
3. Extracts 40 mean MFCCs per chunk.
4. Trains a lightweight Keras Sequential classifier.
5. Exports the frozen model to TensorFlow Lite.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

# ---------------------------------------------------------------------------
# Constants (mirror config.py values so the training script is self-contained)
# ---------------------------------------------------------------------------
SAMPLE_RATE = 44_100
CHUNK_SECONDS = 2.0
BAND_LOW_HZ = 100.0
BAND_HIGH_HZ = 800.0
N_MFCC = 40
FILTER_ORDER = 5

# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _bandpass(samples: np.ndarray, sr: float) -> np.ndarray:
    nyquist = sr / 2.0
    low = max(BAND_LOW_HZ / nyquist, 1e-5)
    high = min(BAND_HIGH_HZ / nyquist, 1.0 - 1e-5)
    sos = butter(FILTER_ORDER, [low, high], btype="band", output="sos")
    return sosfilt(sos, samples).astype(np.float32)


def _extract_mfcc(samples: np.ndarray, sr: float) -> np.ndarray:
    import librosa  # type: ignore[import-untyped]
    mfccs = librosa.feature.mfcc(y=samples.astype(np.float32), sr=sr, n_mfcc=N_MFCC)
    return np.mean(mfccs, axis=1).astype(np.float32)


def load_and_slice(
    wav_path: str | Path, label: int, chunk_s: float = CHUNK_SECONDS, sr: int = SAMPLE_RATE
) -> list[tuple[np.ndarray, int]]:
    """Load a WAV file, slice into ``chunk_s``-second windows, bandpass
    filter, extract MFCCs, and return a list of ``(features, label)``."""
    import librosa  # type: ignore[import-untyped]

    audio, actual_sr = librosa.load(str(wav_path), sr=sr, mono=True)
    chunk_samples = int(chunk_s * actual_sr)
    results: list[tuple[np.ndarray, int]] = []

    for start in range(0, len(audio) - chunk_samples + 1, chunk_samples):
        chunk = audio[start : start + chunk_samples]
        filtered = _bandpass(chunk, actual_sr)
        mfcc_feat = _extract_mfcc(filtered, actual_sr)
        results.append((mfcc_feat, label))

    return results


# ---------------------------------------------------------------------------
# Model definition & training
# ---------------------------------------------------------------------------

def build_model(input_dim: int = N_MFCC):
    """Build a lightweight Keras Sequential classifier."""
    import tensorflow as tf  # type: ignore[import-untyped]

    model = tf.keras.Sequential([
        tf.keras.layers.Dense(32, activation="relu", input_shape=(input_dim,)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train_and_export(
    normal_wav: str | Path,
    triggered_wav: str | Path,
    output_path: str | Path,
    epochs: int = 50,
) -> None:
    import tensorflow as tf  # type: ignore[import-untyped]

    print(f"Loading Normal WAV:    {normal_wav}")
    normal_data = load_and_slice(normal_wav, label=0)
    print(f"  → {len(normal_data)} chunks")

    print(f"Loading Triggered WAV: {triggered_wav}")
    triggered_data = load_and_slice(triggered_wav, label=1)
    print(f"  → {len(triggered_data)} chunks")

    all_data = normal_data + triggered_data
    if len(all_data) < 4:
        print("ERROR: Not enough audio chunks for training. Provide longer WAV files.")
        sys.exit(1)

    np.random.shuffle(all_data)
    X = np.array([d[0] for d in all_data], dtype=np.float32)
    y = np.array([d[1] for d in all_data], dtype=np.float32)

    print(f"\nDataset: {len(X)} samples ({int(np.sum(y == 0))} normal, {int(np.sum(y == 1))} triggered)")

    model = build_model(input_dim=X.shape[1])
    model.summary()

    history = model.fit(X, y, epochs=epochs, batch_size=8, validation_split=0.2, verbose=1)

    final_acc = history.history["accuracy"][-1]
    print(f"\nFinal training accuracy: {final_acc:.2%}")

    # ---- Export to TFLite ----
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(tflite_model)
    print(f"\n✅ TFLite model exported to: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train bee acoustic classifier and export to TFLite."
    )
    parser.add_argument("--normal", required=True, help="Path to Normal.wav (label 0)")
    parser.add_argument("--triggered", required=True, help="Path to Triggered.wav (label 1)")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs (default: 50)")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "bee_acoustic_model.tflite"),
        help="Output .tflite path",
    )
    args = parser.parse_args()

    for path_arg, name in [(args.normal, "Normal"), (args.triggered, "Triggered")]:
        if not Path(path_arg).is_file():
            print(f"ERROR: {name} WAV file not found: {path_arg}")
            sys.exit(1)

    train_and_export(args.normal, args.triggered, args.output, args.epochs)


if __name__ == "__main__":
    main()
