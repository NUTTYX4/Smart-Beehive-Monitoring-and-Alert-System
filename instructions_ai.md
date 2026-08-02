# BeeHive Monitor — Edge AI Upgrade Instructions

> **Version**: NASSCOM Expo 2026 Edition
> **Target Hardware**: Raspberry Pi 4 Model B (Debian Bookworm 64-bit)
> **AI Model**: TFLite MFCC-based binary classifier (Normal vs Triggered)

---

## 1. Folder Structure

```
BeeHiveMonitor/
├── ai_module/                    ← NEW: self-contained AI package
│   ├── __init__.py
│   ├── ai_engine.py              ← TFLite inference engine (Pi)
│   ├── train_model.py            ← Keras training script (PC)
│   ├── requirements_ai.txt       ← AI-specific dependencies
│   └── bee_acoustic_model.tflite ← trained model (git-ignored)
├── audio/                        ← legacy FFT pipeline (preserved)
│   ├── capture.py                ← INMP441 I2S recording
│   ├── fft.py                    ← FFT dominant-frequency analyser
│   └── filters.py                ← DC removal, windowing, noise gate
├── sensors/
│   ├── inmp441_sensor.py         ← MODIFIED: AI-first, FFT-fallback
│   ├── dht22_sensor.py
│   ├── hx711_sensor.py
│   └── mpu6050_sensor.py
├── tgbot/
│   ├── alerts.py                 ← MODIFIED: AI behaviour alerts
│   ├── commands.py               ← MODIFIED: /set_ratio command
│   └── keyboards.py
├── utils/
│   ├── calibration.py
│   ├── csv_logger.py
│   └── thingspeak.py
├── config.py                     ← MODIFIED: secrets cleaned, AI config
├── bot.py                        ← MODIFIED: /set_ratio, secret validation
├── monitor.py                    ← MODIFIED: AI integration, cal recovery
├── token.md                      ← systemd Environment= overrides (git-ignored)
├── .env.example                  ← template for environment variables
├── requirements.txt              ← MODIFIED: + librosa
└── instructions_ai.md            ← THIS FILE
```

### Clean Revert to FFT-Only Mode

Deleting or renaming the `ai_module/` directory (or just removing
`bee_acoustic_model.tflite`) will cause `inmp441_sensor.py` to log a
single warning at startup and automatically fall back to the legacy
FFT peak-frequency analyser. No other code changes are required.

---

## 2. How Secrets Are Loaded

The system uses a layered secret-loading strategy:

```
Environment Variables  →  config.py _env() helpers  →  Application
     ↑
token.md / .env / systemd override
```

### Priority Order (highest wins)

1. **Systemd override** (`/etc/systemd/system/beehive.service.d/override.conf`)
2. **Shell environment variables** (e.g., `export BEEHIVE_TELEGRAM_TOKEN=...`)
3. **`token.md`** (systemd `[Service]` `Environment=` format, loaded manually)

### Required Secrets

| Variable                  | Description                     |
|---------------------------|---------------------------------|
| `BEEHIVE_TELEGRAM_TOKEN`  | Telegram Bot API token          |
| `BEEHIVE_ADMIN_ID`        | Telegram numeric user ID        |
| `BEEHIVE_CHANNEL`         | Telegram channel username       |
| `BEEHIVE_TS_ENV_KEY`      | ThingSpeak env/motion write key |
| `BEEHIVE_TS_WA_KEY`       | ThingSpeak weight/audio write key|

> **IMPORTANT**: `config.py` no longer contains hardcoded fallback
> secrets. If any required secret is missing, `bot.py` and `monitor.py`
> will log an error and exit at startup.

### Setting Up `token.md`

Create/edit `token.md` in the project root with your real credentials:

```ini
[Service]
Environment=BEEHIVE_TELEGRAM_TOKEN=your_bot_token_here
Environment=BEEHIVE_ADMIN_ID=your_numeric_id
Environment=BEEHIVE_CHANNEL=@YourChannel
Environment=BEEHIVE_CHANNEL_LINK=https://t.me/YourChannel
Environment=BEEHIVE_TS_ENV_KEY=your_thingspeak_key
Environment=BEEHIVE_TS_WA_KEY=your_thingspeak_key
```

Then source it before running, or install it as a systemd override:

```bash
sudo cp token.md /etc/systemd/system/beehive.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart beehive.service
```

---

## 3. AI Workflow Overview

```
┌──────────────────┐     ┌──────────────────┐
│   Normal.wav     │     │  Triggered.wav   │
│   (label 0)      │     │   (label 1)      │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └────────┬───────────────┘
                  ▼
    ┌──────────────────────────┐
    │  train_model.py (PC)     │
    │  1. Slice into 2s chunks │
    │  2. Bandpass 100-800 Hz  │
    │  3. Extract 40 MFCCs     │
    │  4. Train Keras model    │
    │  5. Export to TFLite     │
    └──────────┬───────────────┘
               ▼
    ┌──────────────────────────┐
    │ bee_acoustic_model.tflite│
    │ (~10-50 KB)              │
    └──────────┬───────────────┘
               │  (copy to Pi)
               ▼
    ┌──────────────────────────┐
    │  ai_engine.py (Pi)       │
    │  1. Noise gate check     │
    │  2. Bandpass 100-800 Hz  │
    │  3. Extract 40 MFCCs     │
    │  4. TFLite inference     │
    │  5. Threshold @ 0.65     │
    └──────────────────────────┘
```

---

## 4. Training on a PC

### Prerequisites

```bash
# Create a virtual environment (recommended)
python3 -m venv ai_venv
source ai_venv/bin/activate  # Linux/Mac
# ai_venv\Scripts\activate   # Windows

# Install training dependencies
pip install -r ai_module/requirements_ai.txt
```

### Prepare Audio Files

Place clean demonstration WAV files in an accessible directory:
- **`Normal.wav`** — recording of a healthy, calm hive (label 0)
- **`Triggered.wav`** — recording of a distressed/panic hive (label 1)

These should be mono or stereo, 44100 Hz sample rate, and at least
10 seconds long for meaningful training (5+ chunks per class).

### Run Training

```bash
python ai_module/train_model.py \
    --normal  path/to/Normal.wav \
    --triggered path/to/Triggered.wav \
    --epochs 50 \
    --output ai_module/bee_acoustic_model.tflite
```

**Expected output:**

```
Loading Normal WAV:    path/to/Normal.wav
  → 15 chunks
Loading Triggered WAV: path/to/Triggered.wav
  → 12 chunks

Dataset: 27 samples (15 normal, 12 triggered)
Model: "sequential"
...
Final training accuracy: 96.30%

✅ TFLite model exported to: ai_module/bee_acoustic_model.tflite
   Size: 12.4 KB
```

---

## 5. Deploying to Raspberry Pi

### Transfer the Model

```bash
scp ai_module/bee_acoustic_model.tflite pi@<pi-ip>:~/BeeHiveMonitor/ai_module/
```

### Install Pi-Side Dependencies

```bash
# Activate the project venv
source ~/BeeHiveMonitor/venv/bin/activate

# Install TFLite runtime (lightweight, no full TensorFlow needed)
pip install tflite-runtime

# Install librosa for MFCC extraction
pip install librosa
```

### Verify TFLite Inference

Quick smoke test on the Pi:

```bash
cd ~/BeeHiveMonitor
python3 -c "
from ai_module.ai_engine import AIAcousticEngine
engine = AIAcousticEngine()
print('AI engine available:', engine.available)
if engine.available:
    import numpy as np
    # Generate a 2-second test signal
    sr = 44100
    t = np.linspace(0, 2.0, int(2.0 * sr), endpoint=False)
    test_signal = 0.5 * np.sin(2 * np.pi * 250 * t)  # 250 Hz tone
    result = engine.predict_acoustic_state(test_signal, sr)
    print('Result:', result)
"
```

**Expected output (with model deployed):**

```
AI acoustic engine loaded: /home/pi/BeeHiveMonitor/ai_module/bee_acoustic_model.tflite
AI engine available: True
Result: {'behavior': '🟢 Normal / Active', 'confidence': 0.87, 'is_silent': False}
```

**Expected output (without model):**

```
AI model not found at .../bee_acoustic_model.tflite — AI engine disabled (FFT fallback active)
AI engine available: False
```

---

## 6. Fallback Behaviour

The system is designed for **zero-downtime graceful degradation**:

| Condition | Behaviour |
|-----------|-----------|
| `.tflite` present + runtime installed | Full AI classification |
| `.tflite` missing | FFT-only (legacy frequency bands) |
| `tflite-runtime` not installed | FFT-only (logged warning at startup) |
| `librosa` not installed | FFT-only (logged warning at startup) |
| `ai_module/` deleted entirely | FFT-only (import fails gracefully) |
| AI inference throws at runtime | FFT-only for that cycle (try/except) |

---

## 7. The `/set_ratio` Command

Available to admins and approved members via Telegram:

```
/set_ratio 423.567890
```

This:
1. Updates `data/calibration.json` with the new ratio
2. Preserves the existing `weight_g` reference
3. The running monitor picks up the new ratio on next restart

Useful for fine-tuning the HX711 load cell without running the full
guided calibration sequence (e.g., when the hive is occupied and
you can't remove the weight).

---

## 8. Calibration Auto-Recovery

On boot, `monitor.py` checks `data/calibration.json`:

- If a valid `scale_ratio` exists (≠ 1.0), it applies the saved
  calibration directly via `hx711.apply_saved_calibration()` — **no
  guided re-weigh sequence** is triggered.
- If no prior calibration exists or the ratio is the default (1.0),
  the full guided calibration flow runs as before.

This prevents an occupied hive box from being forced through a
re-weigh cycle after a power outage or reboot.

---

## 9. Alert Labels

### AI Mode (primary)

| AI Prediction | Behaviour Label | Alert |
|---------------|-----------------|-------|
| > 0.65 | ⚔️ Triggered / Panic | ⚔️ DANGER: Hive Distress / Panic State Detected! |
| ≤ 0.65 | 🟢 Normal / Active | — |
| Below noise gate | Silence | — |

### FFT Fallback Mode (legacy)

| Frequency Range | Behaviour Label |
|-----------------|-----------------|
| > 450 Hz | ⚔️ Aggressive / Swarming |
| 330–450 Hz | 👑 Queen Piping |
| 190–329 Hz | 🟢 Normal / Active |
| 100–189 Hz | 🆘 Queenless Roar |
| 1–99 Hz | 💤 Dormant / Low |
| 0 Hz | ⚪ Unknown / Silence |

---

## 10. CSV Logging

The `data/hive_update.csv` file now includes the AI behaviour label in
the `Behavior` column. Example:

```csv
Timestamp,Temperature (C),Humidity (%),Weight (g),Frequency (Hz),Behavior,Accel X,...
2026-08-02 14:30:00,33.2,55.0,1250.00,245.67,🟢 Normal / Active,0.02,...
2026-08-02 14:30:25,33.3,54.8,1250.10,312.45,⚔️ Triggered / Panic,0.03,...
```

---

## Troubleshooting

### "AI engine disabled" at startup
- Verify `bee_acoustic_model.tflite` exists in `ai_module/`
- Check `tflite-runtime` or `tensorflow` is installed: `pip list | grep -i tflite`
- Check `librosa` is installed: `python3 -c "import librosa; print(librosa.__version__)"`

### Training produces poor accuracy
- Ensure WAV files are long enough (≥10s each → 5+ chunks)
- Verify audio quality — the demo speaker should be close to the INMP441
- Try increasing epochs: `--epochs 100`
- Check that Normal and Triggered sounds are genuinely distinct

### Secrets missing at startup
- Run `cat token.md` and verify all `Environment=` lines are present
- If using systemd: `systemctl show beehive.service | grep Environment`
- Manually export and test: `export BEEHIVE_TELEGRAM_TOKEN=... && python3 bot.py`
