# BeeHive Monitor — Full Deployment Instructions
## Raspberry Pi 4 · Debian Bookworm 64-bit (Headless) · Via PuTTY

> **Read everything in a section before typing any command.**
> Lines starting with `$` are commands you type in PuTTY.
> Lines starting with `#` inside code blocks are comments — do NOT type them.

---

## Table of Contents

1. [Codebase Overview](#1-codebase-overview)
2. [Pre-Requisites (on your Windows PC)](#2-pre-requisites-on-your-windows-pc)
3. [First Boot and PuTTY Connection](#3-first-boot-and-putty-connection)
4. [Update the System](#4-update-the-system)
5. [Transfer Project Files to the Pi](#5-transfer-project-files-to-the-pi)
6. [Create the Python Virtual Environment (venv)](#6-create-the-python-virtual-environment-venv)
7. [Set Your Secrets (Telegram and ThingSpeak)](#7-set-your-secrets-telegram-and-thingspeak)
8. [Enable I2C and I2S Hardware Interfaces](#8-enable-i2c-and-i2s-hardware-interfaces)
9. [Install and Start the systemd Service](#9-install-and-start-the-systemd-service)
10. [Verify Everything Works](#10-verify-everything-works)
11. [Running Tests (Optional)](#11-running-tests-optional)
12. [Manual Debug Run](#12-manual--debug-run)
13. [Useful Day-to-Day Commands](#13-useful-day-to-day-commands)
14. [File Reference](#14-file-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Codebase Overview

```
BeeHiveMonitor/
├── monitor.py            <- sensor loop, CSV, ThingSpeak, Telegram posts
├── bot.py                <- Telegram bot; launches monitor.py as subprocess
├── config.py             <- ALL config and secrets (override via env vars)
├── requirements.txt      <- Python dependencies
├── install.sh            <- one-shot installer (runs steps 6-9 automatically)
├── enable_i2s.sh         <- adds I2S mic overlay to /boot/firmware/config.txt
├── services/
│   └── beehive.service   <- systemd unit template
├── audio/                <- I2S capture, FFT, bandpass filters
├── sensors/              <- per-sensor drivers (HX711, DHT22, MPU6050, INMP441)
├── tgbot/                <- Telegram alerts, commands, keyboards
├── utils/                <- logging, CSV, ThingSpeak, network, watchdog, calibration
├── tests/                <- hardware-free pytest suite
└── logs/                 <- runtime log files (auto-created)
```

### Hardware wired to the Pi

| Sensor  | What it measures         | Interface                           |
|---------|--------------------------|-------------------------------------|
| HX711   | Hive weight (load cell)  | GPIO 5 (DOUT) / GPIO 6 (SCK)       |
| DHT22   | Temperature and humidity | GPIO 4                              |
| MPU6050 | Vibration / tilt         | I2C bus 1 (SDA GPIO2 / SCL GPIO3)  |
| INMP441 | Bee acoustics (I2S mic)  | GPIO 18/19/20, L/R -> GND, VDD 3.3V|

> All GPIO pin numbers can be changed via environment variables in
> `/etc/systemd/system/beehive.service.d/override.conf` (see section 7).

---

## 2. Pre-Requisites (on your Windows PC)

### 2.1 Install PuTTY

Download from https://www.putty.org and install it.

### 2.2 Install WinSCP (file transfer)

Download from https://winscp.net — you will use it to copy the project folder to the Pi.

### 2.3 Flash Raspberry Pi OS Bookworm (Lite, 64-bit)

1. Download **Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. Choose OS -> **Raspberry Pi OS (other)** -> **Raspberry Pi OS Lite (64-bit)**
3. Before writing, click the gear icon and:
   - Set **hostname**: e.g. `beehive`
   - Enable **SSH** (password or key)
   - Set **username / password** (e.g. `pi` / your chosen password)
   - Set **Wi-Fi** SSID and password (if using Wi-Fi)
4. Write to SD card -> insert into Pi -> power on.

### 2.4 Find the Pi's IP address

On your router admin page look for `beehive` or use **Advanced IP Scanner**
(https://www.advanced-ip-scanner.com/).

---

## 3. First Boot and PuTTY Connection

1. Open **PuTTY**.
2. In **Host Name (or IP address)** enter the Pi's IP (e.g. `192.168.1.50`).
3. **Port**: `22`, **Connection type**: SSH.
4. Click **Open** -> accept the host key fingerprint -> log in with your username/password.

You should see a prompt like:

```
pi@beehive:~$
```

---

## 4. Update the System

Run these commands **one at a time** and wait for each to finish:

```bash
$ sudo apt-get update -y
$ sudo apt-get upgrade -y
$ sudo apt-get autoremove -y
```

> This can take 5-15 minutes on first boot. Do not close PuTTY.

---

## 5. Transfer Project Files to the Pi

### Option A — WinSCP (recommended for beginners)

1. Open **WinSCP** -> **New Site**.
2. **File protocol**: SFTP · **Host name**: Pi's IP · **User name / Password**: same as PuTTY.
3. Click **Login**.
4. On the **right** panel navigate to `/home/pi/`.
5. On the **left** panel navigate to your Windows folder containing `BeeHiveMonitor`.
6. Drag the entire `BeeHiveMonitor` folder to the right panel.
7. Wait for the transfer to complete.

### Option B — Git (if the repo is on GitHub)

```bash
$ cd ~
$ sudo apt-get install -y git
$ git clone https://github.com/YOUR_USERNAME/BeeHiveMonitor.git BeeHiveMonitor
```

Replace the URL with your actual repository URL.

### Verify the transfer

```bash
$ ls ~/BeeHiveMonitor
```

You should see: `monitor.py  bot.py  config.py  requirements.txt  install.sh  ...`

---

## 6. Create the Python Virtual Environment (venv)

### Step 6.1 — Install system dependencies

```bash
$ sudo apt-get install -y \
    python3 python3-venv python3-pip python3-dev \
    i2c-tools libatlas-base-dev \
    portaudio19-dev libportaudio2 libasound2-dev \
    git build-essential
```

### Step 6.2 — Navigate to the project directory

```bash
$ cd ~/BeeHiveMonitor
```

### Step 6.3 — Create the virtual environment

```bash
$ python3 -m venv venv
```

This creates a `venv/` folder inside the project. Takes about 30 seconds.

### Step 6.4 — Activate the virtual environment

```bash
$ source venv/bin/activate
```

Your prompt changes to:

```
(venv) pi@beehive:~/BeeHiveMonitor$
```

> Every time you open a new PuTTY session and want to run the project manually,
> you must run this activate command again.

### Step 6.5 — Upgrade pip and install requirements

```bash
$ pip install --upgrade pip setuptools wheel
$ pip install -r requirements.txt
```

> This installs numpy, scipy, python-telegram-bot, RPi.GPIO, smbus2, hx711,
> sounddevice, and all other dependencies. Takes 3-10 minutes.
> Watch for any red ERROR lines.

### Step 6.6 — Deactivate (when done with manual work)

```bash
$ deactivate
```

---

## 7. Set Your Secrets (Telegram and ThingSpeak)

> NEVER edit config.py to put in real tokens. Use a systemd override file instead.
> This keeps secrets out of the source code.

### Step 7.1 — Get your Telegram bot token

1. Open Telegram -> search for **@BotFather**.
2. Send `/newbot` (or `/revoke` to rotate an existing token).
3. Follow the prompts -> copy the token (e.g. `123456789:ABCDEFGxyz...`).

### Step 7.2 — Get your Telegram user ID

1. Search for **@userinfobot** in Telegram -> send `/start`.
2. It replies with your numeric user ID (e.g. `5633775788`).

### Step 7.3 — Get your ThingSpeak write keys

1. Log in at https://thingspeak.mathworks.com
2. Open your channel -> **API Keys** tab.
3. Copy both Write API Keys.

### Step 7.4 — Create the systemd override directory

```bash
$ sudo mkdir -p /etc/systemd/system/beehive.service.d
```

### Step 7.5 — Write the secrets override file

Open nano to create the file:

```bash
$ sudo nano /etc/systemd/system/beehive.service.d/override.conf
```

Inside nano, type exactly this (replace every placeholder value):

```
[Service]
Environment=BEEHIVE_TELEGRAM_TOKEN=123456789:YOUR_REAL_BOT_TOKEN_HERE
Environment=BEEHIVE_ADMIN_ID=YOUR_NUMERIC_TELEGRAM_USER_ID
Environment=BEEHIVE_CHANNEL=@YourChannelUsername
Environment=BEEHIVE_CHANNEL_LINK=https://t.me/YourChannelUsername
Environment=BEEHIVE_TS_ENV_KEY=YOUR_THINGSPEAK_ENV_MOTION_WRITE_KEY
Environment=BEEHIVE_TS_WA_KEY=YOUR_THINGSPEAK_WEIGHT_AUDIO_WRITE_KEY
```

To save in nano:
- Press Ctrl + O then press Enter to confirm the filename
- Press Ctrl + X to exit

### Step 7.6 — Verify the file was saved

```bash
$ sudo cat /etc/systemd/system/beehive.service.d/override.conf
```

You should see your values printed back.

---

## 8. Enable I2C and I2S Hardware Interfaces

### Step 8.1 — Make scripts executable

```bash
$ cd ~/BeeHiveMonitor
$ chmod +x install.sh enable_i2s.sh
```

### Step 8.2 — Enable I2C (for MPU6050)

```bash
$ sudo raspi-config nonint do_i2c 0
```

Verify I2C is enabled:

```bash
$ ls /dev/i2c*
```

You should see `/dev/i2c-1`.

### Step 8.3 — Enable I2S (for INMP441 microphone)

```bash
$ sudo bash ~/BeeHiveMonitor/enable_i2s.sh
```

This adds two lines to `/boot/firmware/config.txt`:

```
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
```

Verify they were added:

```bash
$ grep -E "i2s|googlevoicehat" /boot/firmware/config.txt
```

### Step 8.4 — Reboot (REQUIRED after enabling I2C and I2S)

```bash
$ sudo reboot
```

PuTTY will disconnect. Wait 60 seconds, then reconnect via PuTTY.

### Step 8.5 — Verify the microphone is visible

After reconnecting:

```bash
$ arecord -l
```

You should see something like:

```
card 0: sndrpigooglevoi [snd_rpi_googlevoicehat_soundcar], device 0: ...
```

If you see nothing, refer to section 15 Troubleshooting.

### Step 8.6 — Verify I2C devices are detected

```bash
$ sudo i2cdetect -y 1
```

You should see `68` in the grid (MPU6050 at address 0x68).

---

## 9. Install and Start the systemd Service

Run the one-shot installer as root:

```bash
$ cd ~/BeeHiveMonitor
$ sudo ./install.sh
```

This script will:
1. Re-run apt-get update and install any missing system packages
2. Re-enable I2C / run enable_i2s.sh
3. Create/update the Python venv and install requirements.txt
4. Create data/ and logs/ directories
5. Copy services/beehive.service to /etc/systemd/system/beehive.service (with paths filled in)
6. Run systemctl daemon-reload, systemctl enable, systemctl restart

### Step 9.1 — Reload systemd to pick up the override file

```bash
$ sudo systemctl daemon-reload
```

### Step 9.2 — Enable and start the service

```bash
$ sudo systemctl enable beehive.service
$ sudo systemctl start beehive.service
```

### Step 9.3 — Check the service status

```bash
$ sudo systemctl status beehive.service
```

You should see Active: active (running) in green. Press Q to exit.

---

## 10. Verify Everything Works

### Step 10.1 — Watch live logs

```bash
$ journalctl -u beehive.service -f
```

Press Ctrl + C to stop. Look for lines like:

```
INFO  bot.py: Bot started, waiting for commands...
INFO  monitor.py: Cycle complete — weight=X.Xg temp=XX.X°C ...
```

### Step 10.2 — Watch the application log file

```bash
$ tail -f ~/BeeHiveMonitor/logs/beehive.log
```

Press Ctrl + C to stop.

### Step 10.3 — Test the Telegram bot

Open Telegram -> find your bot -> send /start.
You should receive a reply with the control panel keyboard.

### Step 10.4 — Confirm sensors are reading

From the Telegram bot, press the Status button.
You should see live sensor values.

---

## 11. Running Tests (Optional)

These tests run without hardware attached (everything is mocked):

```bash
$ cd ~/BeeHiveMonitor
$ source venv/bin/activate
$ python -m pytest tests/ -v
$ deactivate
```

All tests should show PASSED.

---

## 12. Manual / Debug Run

Use this to debug issues without the service running.

### Step 12.1 — Stop the service first

```bash
$ sudo systemctl stop beehive.service
```

### Step 12.2 — Activate venv

```bash
$ cd ~/BeeHiveMonitor
$ source venv/bin/activate
```

### Step 12.3 — Run the bot manually

```bash
$ python3 bot.py
```

Press Ctrl + C to stop.

### Step 12.4 — Run the monitor directly (sensor debugging)

```bash
$ python3 monitor.py 650 "Debug User" 123456789
```

Replace 650 with your calibration weight in grams, and 123456789 with your actual Telegram user ID.

### Step 12.5 — Re-enable the service when done

```bash
$ deactivate
$ sudo systemctl start beehive.service
```

---

## 13. Useful Day-to-Day Commands

| Task                           | Command                                                                 |
|--------------------------------|-------------------------------------------------------------------------|
| Check service status           | sudo systemctl status beehive.service                                   |
| Start service                  | sudo systemctl start beehive.service                                    |
| Stop service                   | sudo systemctl stop beehive.service                                     |
| Restart service                | sudo systemctl restart beehive.service                                  |
| Watch live service logs        | journalctl -u beehive.service -f                                        |
| Watch app log file             | tail -f ~/BeeHiveMonitor/logs/beehive.log                              |
| Activate venv (manual work)    | source ~/BeeHiveMonitor/venv/bin/activate                              |
| Deactivate venv                | deactivate                                                              |
| Update Python packages         | source ~/BeeHiveMonitor/venv/bin/activate && pip install -r ~/BeeHiveMonitor/requirements.txt --upgrade && deactivate |
| Check I2C devices              | sudo i2cdetect -y 1                                                     |
| Check microphone               | arecord -l                                                              |
| Check CPU temperature          | vcgencmd measure_temp                                                   |
| View data CSV                  | cat ~/BeeHiveMonitor/data/hive_update.csv                              |
| View calibration               | cat ~/BeeHiveMonitor/data/calibration.json                             |
| Edit secrets override          | sudo nano /etc/systemd/system/beehive.service.d/override.conf          |
| Reload after editing secrets   | sudo systemctl daemon-reload && sudo systemctl restart beehive.service  |
| Reboot Pi                      | sudo reboot                                                             |

---

## 14. File Reference

| File / Folder              | Purpose                                                                              |
|----------------------------|--------------------------------------------------------------------------------------|
| monitor.py                 | Main sensor loop — reads sensors every 25s, logs CSV, uploads ThingSpeak, alerts     |
| bot.py                     | Telegram bot — receives commands, launches/stops monitor.py as a child process       |
| config.py                  | All constants with env-var overrides — never put real secrets here                   |
| requirements.txt           | Python package list — install inside the venv                                        |
| install.sh                 | One-shot installer — runs apt, creates venv, installs service                        |
| enable_i2s.sh              | Adds I2S overlay lines to /boot/firmware/config.txt                                  |
| services/beehive.service   | systemd unit template (placeholders replaced by install.sh)                          |
| audio/capture.py           | Records 2s of audio from INMP441 via sounddevice                                     |
| audio/fft.py               | FFT analysis — extracts dominant frequency in 100-800 Hz bee band                    |
| audio/filters.py           | Bandpass filter for acoustic signal                                                  |
| sensors/hx711_sensor.py    | HX711 driver — reads load cell, applies calibration                                  |
| sensors/dht22_sensor.py    | DHT22 driver — reads temperature and humidity                                        |
| sensors/mpu6050_sensor.py  | MPU6050 driver — reads accelerometer and gyroscope over I2C                          |
| sensors/inmp441_sensor.py  | INMP441 driver — delegates to audio/capture.py                                       |
| tgbot/alerts.py            | Formats and sends threshold-breach alerts to Telegram                                |
| tgbot/commands.py          | All /start, status, calibration, CSV download handlers                               |
| tgbot/keyboards.py         | Telegram inline keyboard layouts                                                     |
| utils/logger.py            | Rotating file and console logger                                                     |
| utils/csv_logger.py        | Appends sensor readings to data/hive_update.csv                                      |
| utils/thingspeak.py        | Uploads fields to ThingSpeak channels with rate-limit guard                          |
| utils/network.py           | Retrying HTTP session with exponential backoff                                       |
| utils/watchdog.py          | Writes heartbeat file each cycle                                                     |
| utils/calibration.py       | Loads / saves calibration JSON; guides weighing workflow                              |
| data/calibration.json      | Saved scale calibration (auto-created, persists across reboots)                      |
| data/members.json          | Telegram member access list (managed via bot commands)                               |
| data/hive_update.csv       | Rolling sensor data log                                                              |
| logs/beehive.log           | Rotating application log (max 5 MB x 5 files)                                       |

---

## 15. Troubleshooting

### arecord -l shows no capture devices

```bash
# Confirm the overlay lines exist
$ grep -E "i2s|googlevoicehat" /boot/firmware/config.txt

# If missing, re-run and reboot
$ sudo bash ~/BeeHiveMonitor/enable_i2s.sh
$ sudo reboot
```

### i2cdetect -y 1 shows no device at 0x68

- Check SDA -> GPIO2 and SCL -> GPIO3 are firmly connected.
- Check MPU6050 VCC is 3.3V (not 5V).
- Re-enable I2C:

```bash
$ sudo raspi-config nonint do_i2c 0
$ sudo reboot
```

### Service fails to start (status shows failed)

```bash
# View error details
$ journalctl -u beehive.service -n 50 --no-pager
```

Common causes:
- Wrong bot token — re-check override.conf (section 7.5)
- Import error — pip install -r requirements.txt not run in venv
- Port conflict — another instance is running, stop it first

### Bot does not reply in Telegram

1. Check the token in override.conf is correct.
2. Make sure BEEHIVE_ADMIN_ID matches your actual Telegram user ID.
3. Tail logs for Unauthorized or Conflict errors:

```bash
$ journalctl -u beehive.service -f
```

### pip install -r requirements.txt fails

- Ensure libatlas-base-dev and portaudio19-dev are installed (section 6.1).
- Ensure venv is activated (prompt shows (venv)).
- For hx711 errors try: pip install hx711==1.1.2.3

### Permission denied on GPIO / I2C / audio (manual run only)

```bash
$ sudo usermod -aG gpio,i2c,audio,spi pi
$ newgrp gpio
```

### After editing override.conf, changes not picked up

```bash
$ sudo systemctl daemon-reload
$ sudo systemctl restart beehive.service
```

---

## Quick-Start Summary (after initial setup is complete)

```bash
# 1. SSH in via PuTTY

# 2. Check the service is running
sudo systemctl status beehive.service

# 3. If not running, start it
sudo systemctl start beehive.service

# 4. Watch live logs
journalctl -u beehive.service -f
```

That is it. The bot handles everything else from Telegram.
