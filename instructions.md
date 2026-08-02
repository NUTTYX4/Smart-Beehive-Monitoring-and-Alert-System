# BeeHive Monitor — Unified Edge AI & Full Deployment Instructions
## Raspberry Pi 4 · Debian Bookworm 64-bit (Headless) · Via PuTTY & Edge AI Architecture

> **Version**: NASSCOM Expo 2026 Unified Edition  
> **Target Hardware**: Raspberry Pi 4 Model B (Debian Bookworm 64-bit) & Google VoiceHAT I2S MEMS  
> **AI Model**: TFLite MFCC-based binary classifier (Normal vs Triggered Hive Distress)

---

## Table of Contents

1. [Codebase Overview & Folder Structure](#1-codebase-overview--folder-structure)
2. [Pre-Requisites (on your Windows PC)](#2-pre-requisites-on-your-windows-pc)
3. [First Boot and PuTTY Connection](#3-first-boot-and-putty-connection)
4. [Update the System](#4-update-the-system)
5. [Transfer Project Files to the Pi](#5-transfer-project-files-to-the-pi)
6. [Create the Python Virtual Environment (venv)](#6-create-the-python-virtual-environment-venv)
7. [Set Your Secrets & Hardware Audio Configuration](#7-set-your-secrets--hardware-audio-configuration)
8. [Enable I2C and I2S Hardware Interfaces](#8-enable-i2c-and-i2s-hardware-interfaces)
9. [Install and Start the systemd Service](#9-install-and-start-the-systemd-service)
10. [Edge AI Workflow & Training (PC / Pi)](#10-edge-ai-workflow--training-pc--pi)
11. [AI Inference & Graceful Fallback Behavior](#11-ai-inference--graceful-fallback-behavior)
12. [Calibration Auto-Recovery & /set_ratio Command](#12-calibration-auto-recovery--set_ratio-command)
13. [Alert Labels & CSV Logging](#13-alert-labels--csv-logging)
14. [Useful Day-to-Day Commands](#14-useful-day-to-day-commands)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Codebase Overview & Folder Structure

```
BeeHiveMonitor/
├── ai_module/                    ← Self-contained Edge AI package
│   ├── __init__.py
│   ├── ai_engine.py              ← TFLite inference engine (Pi)
│   ├── train_model.py            ← Keras training & MFCC sliding window slicing script
│   ├── bee_acoustic_model.tflite ← Trained TFLite model (git-ignored)
│   └── audio_samples/            ← Bundled audio test samples
│       ├── Normal.wav            ← Healthy hive recording (label 0)
│       └── Triggered.wav         ← Distressed/panic hive recording (label 1)
├── audio/                        ← Signal processing & audio capture
│   ├── capture.py                ← INMP441 I2S stereo capture & Left-channel extraction
│   ├── fft.py                    ← FFT dominant-frequency analyser & spectrum math
│   └── filters.py                ← Bandpass filtering, windowing, peak noise gate
├── sensors/                      ← Hardware sensor drivers
│   ├── inmp441_sensor.py         ← Facade combining I2S capture, Edge AI, and FFT
│   ├── dht22_sensor.py           ← DHT22 temp & humidity sensor
│   ├── hx711_sensor.py           ← HX711 load cell weight sensor
│   └── mpu6050_sensor.py         ← MPU6050 6-axis accelerometer/gyroscope tilt sensor
├── tgbot/                        ← Telegram Bot API communication
│   ├── alerts.py                 ← Multi-rule hive alert evaluation & plain-text retry fallback
│   ├── commands.py               ← /start, status, /set_ratio, calibration handlers
│   └── keyboards.py              ← Inline keyboards & control menus
├── utils/                        ← Logging, network retries, watchdog, calibration math
├── config.py                     ← Central system defaults & environment variable overrides
├── bot.py                        ← Telegram bot service process
├── monitor.py                    ← Core polling loop (reads sensors, logs CSV, ThingSpeak)
├── token.md                      ← systemd Environment= secrets (git-ignored)
├── requirements.txt              ← Unified platform dependencies (includes TFLite & librosa)
├── install.sh                    ← One-shot automated setup script
└── instructions.md               ← THIS FILE (Unified Documentation)
```

### Hardware Wired to the Pi

| Sensor  | What it measures         | Interface                           |
|---------|--------------------------|-------------------------------------|
| HX711   | Hive weight (load cell)  | GPIO 5 (DOUT) / GPIO 6 (SCK)       |
| DHT22   | Temperature and humidity | GPIO 4                              |
| MPU6050 | Vibration / tilt         | I2C bus 1 (SDA GPIO2 / SCL GPIO3)  |
| INMP441 | Bee acoustics (I2S mic)  | GPIO 18/19/20, L/R -> GND, VDD 3.3V|

---

## 2. Pre-Requisites (on your Windows PC)

1. **Install PuTTY**: Download from https://www.putty.org for SSH command access.
2. **Install WinSCP**: Download from https://winscp.net for dragging and dropping files to the Pi.
3. **Flash Raspberry Pi OS Bookworm (Lite, 64-bit)** using Raspberry Pi Imager. Configure SSH, username/password (`pi` / custom password), and Wi-Fi credentials in the Advanced Settings gear icon before flashing.

---

## 3. First Boot and PuTTY Connection

1. Open **PuTTY**, enter your Pi's IP address (e.g. `192.168.1.50`) on Port `22` (SSH).
2. Click **Open**, accept the security fingerprint, and log in.

---

## 4. Update the System

Run these terminal commands one at a time:

```bash
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get autoremove -y
```

---

## 5. Transfer Project Files to the Pi

Either clone via Git directly on your Raspberry Pi:
```bash
cd ~
git clone https://github.com/NUTTYX4/Smart-Beehive-Monitoring-and-Alert-System.git BeeHiveMonitor
cd BeeHiveMonitor
```

Or drag-and-drop your Windows folder to `/home/pi/BeeHiveMonitor` using **WinSCP**.

---

## 6. Create the Python Virtual Environment (venv)

```bash
# 1. Install system native compilation and PortAudio header libraries
sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
    i2c-tools libatlas-base-dev portaudio19-dev libportaudio2 libasound2-dev git build-essential

# 2. Enter project folder and create virtual environment
cd ~/BeeHiveMonitor
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Upgrade pip and install unified system dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

> **Note on AI Dependencies**: `requirements.txt` includes smart platform conditionals. On Raspberry Pi ARM architectures (`aarch64`/`armv7l`), it automatically installs lightweight `tflite-runtime` and `librosa`. On desktop computers (`x86_64`), it installs full `tensorflow` for AI model training.

---

## 7. Set Your Secrets & Hardware Audio Configuration

The application never stores real tokens or hardcoded audio overrides in source code. We pass them securely via systemd overrides or a local `token.md` file.

### Create/Edit Systemd Override File
```bash
sudo mkdir -p /etc/systemd/system/beehive.service.d
sudo nano /etc/systemd/system/beehive.service.d/override.conf
```

### Complete Production Configuration Template (`override.conf` / `token.md`):
```ini
[Service]
# Telegram Credentials
Environment=BEEHIVE_TELEGRAM_TOKEN=your_real_bot_token_here
Environment=BEEHIVE_ADMIN_ID=your_numeric_telegram_user_id
Environment=BEEHIVE_CHANNEL=@YourChannelUsername
Environment=BEEHIVE_CHANNEL_LINK=https://t.me/YourChannelUsername

# ThingSpeak API Keys
Environment=BEEHIVE_TS_ENV_KEY=your_thingspeak_env_motion_write_key
Environment=BEEHIVE_TS_WA_KEY=your_thingspeak_weight_audio_write_key

# INMP441 / Google VoiceHAT Hardware Audio Configuration
Environment=BEEHIVE_MIC_DEVICE=snd_rpi_googlevoicehat_soundcar
Environment=BEEHIVE_MIC_SAMPLE_RATE=48000
Environment=BEEHIVE_MIC_CHANNELS=2
Environment=BEEHIVE_MIC_DTYPE=float32
Environment=BEEHIVE_MIC_BLOCK_SIZE=4096
Environment=BEEHIVE_MIC_CAPTURE_SECONDS=2.0
Environment=BEEHIVE_FFT_NOISE_GATE=0.01
```
Save in nano with `Ctrl+O` -> `Enter`, then exit with `Ctrl+X`.

---

## 8. Enable I2C and I2S Hardware Interfaces

```bash
cd ~/BeeHiveMonitor
chmod +x install.sh enable_i2s.sh

# Enable I2C bus for MPU6050 gyroscope/accelerometer
sudo raspi-config nonint do_i2c 0

# Enable native I2S audio driver for INMP441
sudo bash ~/BeeHiveMonitor/enable_i2s.sh

# REQUIRED: Reboot to apply device overlays
sudo reboot
```

After reconnecting, verify devices:
* Check microphone card: `arecord -l` (should show `snd_rpi_googlevoicehat_soundcar`).
* Check I2C sensor grid: `sudo i2cdetect -y 1` (should highlight address `68`).

---

## 9. Install and Start the systemd Service

```bash
cd ~/BeeHiveMonitor
sudo ./install.sh

sudo systemctl daemon-reload
sudo systemctl enable beehive.service
sudo systemctl restart beehive.service
sudo systemctl status beehive.service
```
You should see `Active: active (running)` in green.

---

## 10. Edge AI Workflow & Training (PC / Pi)

The acoustic AI module converts raw 2.0-second I2S sound clips into **40 Mel-Frequency Cepstral Coefficients (MFCCs)** and analyzes them with a 2D Convolutional Neural Network (CNN) compressed into TensorFlow Lite.

### Training the Model
You can train directly on your PC or on the Raspberry Pi using the bundled demo files (`Normal.wav` and `Triggered.wav`). The training engine utilizes a **0.5-second sliding window stride** to multiply training samples 4x and applies **feature standardization (zero-mean, unit-variance)**.

```bash
cd ~/BeeHiveMonitor
source venv/bin/activate
python ai_module/train_model.py
```
* **Output**: Successfully trains the Keras neural network to ~95%+ accuracy and exports an ultra-lightweight binary model to `ai_module/bee_acoustic_model.tflite` (~12 KB).
* To use custom WAV files: `python ai_module/train_model.py --normal /path/to/normal.wav --triggered /path/to/panic.wav --epochs 100`

---

## 11. AI Inference & Graceful Fallback Behavior

When `monitor.py` polls sensors every cycle, `inmp441_sensor.py` manages audio analysis with automatic fallback resilience:
1. **Primary AI Path**: Captures stereo audio, extracts Left channel index `[0]`, verifies amplitude above `BEEHIVE_FFT_NOISE_GATE`, extracts MFCCs, and classifies state via TFLite.
2. **Legacy FFT Fallback**: Simultaneously computes Fast Fourier Transform dominant frequency (Hz) for ThingSpeak telemetry. If `tflite-runtime` or the `.tflite` model file is ever missing or deleted, the system seamlessly falls back to legacy frequency-band classification without downtime!

---

## 12. Calibration Auto-Recovery & /set_ratio Command

### Auto-Recovery
On startup, `monitor.py` reads `data/calibration.json`. If a valid `scale_ratio` exists (≠ 1.0), it applies the calibration immediately. **No physical unloading or re-weighing is required** after power outages or routine reboots!

### Telegram Fine-Tuning
Admins can manually adjust scale sensitivity on live occupied hives without disturbing bees using Telegram:
```
/set_ratio -0.069231
```
This updates `calibration.json` instantly and takes effect on the next cycle or reboot.

---

## 13. Alert Labels & CSV Logging

### AI Mode (Primary)
| AI Prediction | Behavior Label | Telegram Alert |
|---|---|---|
| Confidence > 0.65 | ⚔️ Triggered / Panic | `⚔️ DANGER: Hive Distress / Panic State Detected! (AI Confidence: 95%)` |
| Confidence ≤ 0.65 | 🟢 Normal / Active | No alert (normal operational state) |
| Peak < Noise Gate | ⚪ Silence | No alert (below acoustic threshold) |

### FFT Fallback Mode (Legacy)
| Dominant Frequency | Behavior Label & Interpretation |
|---|---|
| > 450 Hz | ⚔️ Aggressive / Swarming (High defensive buzzing) |
| 330–450 Hz | 👑 Queen Piping (Virgin queen pre-swarm signal) |
| 190–329 Hz | 🟢 Normal / Active (Standard foraging hum) |
| 100–189 Hz | 🆘 Queenless Roar (Low chaotic distress moaning) |
| 1–99 Hz | 💤 Dormant / Low (Winter dormancy / inactivity) |

### CSV & Telegram Telemetry
All acoustic classifications, temperatures, weights, and motion deltas are logged sequentially in `data/hive_update.csv`. If any Telegram alert message encounters Markdown syntax formatting conflicts (e.g., usernames with unescaped underscores), `tgbot/alerts.py` automatically catches the HTTP 400 rejection and **retries sending immediately as raw plain-text** so critical alerts are never lost.

---

## 14. Useful Day-to-Day Commands

| Task | Terminal Command |
|---|---|
| **Check service status** | `sudo systemctl status beehive.service` |
| **Restart systemd service** | `sudo systemctl restart beehive.service` |
| **Stop service** | `sudo systemctl stop beehive.service` |
| **Watch live service logs** | `journalctl -u beehive.service -f` |
| **Watch app rotating log** | `tail -f ~/BeeHiveMonitor/logs/beehive.log` |
| **Check connected I2S mic** | `arecord -l` |
| **Check connected I2C sensors** | `sudo i2cdetect -y 1` |
| **Edit secret override config** | `sudo nano /etc/systemd/system/beehive.service.d/override.conf` |
| **Reload config & restart** | `sudo systemctl daemon-reload && sudo systemctl restart beehive.service` |
| **Run manual debug monitor** | `source venv/bin/activate && python3 monitor.py 650 "Admin" 12345678` |

---

## 15. Troubleshooting

* **`arecord -l` shows no microphone**: Confirm `/boot/firmware/config.txt` has `dtoverlay=googlevoicehat-soundcard` and reboot.
* **Dominant frequency returns `0.00 Hz` during testing**: Verify `BEEHIVE_FFT_NOISE_GATE=0.01` is set in your systemd override. If testing quiet synthetic sounds, lower it temporarily to `0.0001`.
* **Telegram sendMessage 400 Bad Request ("can't parse entities")**: The automated plain-text fallback in `tgbot/alerts.py` will catch this and send the text without Markdown styling. Ensure your bot is running Version 2 codebase or newer.
* **PortAudio / Sounddevice library not found**: Re-run `sudo apt-get install portaudio19-dev libportaudio2 libasound2-dev`.
