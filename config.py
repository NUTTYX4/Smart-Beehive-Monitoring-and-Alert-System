# -*- coding: utf-8 -*-
"""
config.py
=========
Central configuration for the BeeHive Monitor project.

All secrets, GPIO pin assignments, thresholds, and tunable intervals
live here so nothing is hard-coded anywhere else in the codebase.

Values can be overridden with environment variables (useful for
systemd `Environment=` directives or a `.env` file loaded by
`install.sh`) while still falling back to sane defaults so the
project runs out of the box.

SECURITY NOTE:
    The Telegram bot token and ThingSpeak API keys below were carried
    over from the legacy scripts. Because they previously lived in
    plain Python source that may have been shared or committed to a
    repository, it is strongly recommended that you rotate them
    (BotFather -> /revoke for Telegram, ThingSpeak channel settings
    for the write keys) and then only ever set the new values through
    environment variables, never by editing this file in place.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final


def _env(name: str, default: str) -> str:
    """Return an environment variable, falling back to a default."""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# -------------------------------------------------------------------
# Base paths
# -------------------------------------------------------------------
BASE_DIR: Final[Path] = Path(os.environ.get("BEEHIVE_HOME", Path(__file__).resolve().parent))
LOG_DIR: Final[Path] = BASE_DIR / "logs"
DATA_DIR: Final[Path] = BASE_DIR / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

HIVE_DATA_CSV: Final[Path] = DATA_DIR / "hive_update.csv"
CALIBRATION_FILE: Final[Path] = DATA_DIR / "calibration.json"
MEMBERS_FILE: Final[Path] = DATA_DIR / "members.json"
APP_LOG_FILE: Final[Path] = LOG_DIR / "beehive.log"

# -------------------------------------------------------------------
# Telegram
# -------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: Final[str] = _env("BEEHIVE_TELEGRAM_TOKEN", "")
TELEGRAM_AUTHORIZED_USER_ID: Final[int] = _env_int("BEEHIVE_ADMIN_ID", 0)
TELEGRAM_LOG_CHANNEL: Final[str] = _env("BEEHIVE_CHANNEL", "@MyHiveAlerts")
TELEGRAM_PUBLIC_CHANNEL_LINK: Final[str] = _env(
    "BEEHIVE_CHANNEL_LINK", "https://t.me/MyHiveAlerts"
)
TELEGRAM_READ_TIMEOUT: Final[int] = _env_int("BEEHIVE_TG_READ_TIMEOUT", 30)
TELEGRAM_CONNECT_TIMEOUT: Final[int] = _env_int("BEEHIVE_TG_CONNECT_TIMEOUT", 20)
TELEGRAM_POLL_TIMEOUT: Final[int] = _env_int("BEEHIVE_TG_POLL_TIMEOUT", 60)

# -------------------------------------------------------------------
# ThingSpeak
# -------------------------------------------------------------------
THINGSPEAK_URL: Final[str] = _env("BEEHIVE_TS_URL", "https://api.thingspeak.com/update")
THINGSPEAK_ENV_MOTION_API_KEY: Final[str] = _env("BEEHIVE_TS_ENV_KEY", "")
THINGSPEAK_WEIGHT_AUDIO_API_KEY: Final[str] = _env("BEEHIVE_TS_WA_KEY", "")
THINGSPEAK_MIN_INTERVAL_S: Final[float] = _env_float("BEEHIVE_TS_MIN_INTERVAL", 15.0)
THINGSPEAK_RETRY_TOTAL: Final[int] = _env_int("BEEHIVE_TS_RETRY_TOTAL", 4)
THINGSPEAK_RETRY_BACKOFF: Final[float] = _env_float("BEEHIVE_TS_RETRY_BACKOFF", 1.5)
THINGSPEAK_TIMEOUT_S: Final[int] = _env_int("BEEHIVE_TS_TIMEOUT", 20)

# -------------------------------------------------------------------
# GPIO / bus assignments
# -------------------------------------------------------------------
HX711_DOUT_PIN: Final[int] = _env_int("BEEHIVE_HX711_DOUT", 5)
HX711_SCK_PIN: Final[int] = _env_int("BEEHIVE_HX711_SCK", 6)

DHT22_PIN: Final[int] = _env_int("BEEHIVE_DHT22_PIN", 4)

MPU6050_I2C_BUS: Final[int] = _env_int("BEEHIVE_MPU_I2C_BUS", 1)
MPU6050_ADDR: Final[int] = _env_int("BEEHIVE_MPU_ADDR", 0x68)

# INMP441 I2S MEMS microphone (native Raspberry Pi I2S, via sounddevice)
INMP441_SAMPLE_RATE: Final[int] = _env_int("BEEHIVE_MIC_SAMPLE_RATE", 44100)
INMP441_CHANNELS: Final[int] = _env_int("BEEHIVE_MIC_CHANNELS", 1)
INMP441_DEVICE: Final[str] = _env("BEEHIVE_MIC_DEVICE", "")  # "" = sounddevice default
INMP441_BLOCK_SIZE: Final[int] = _env_int("BEEHIVE_MIC_BLOCK_SIZE", 4096)
INMP441_CAPTURE_SECONDS: Final[float] = _env_float("BEEHIVE_MIC_CAPTURE_SECONDS", 2.0)
INMP441_DTYPE: Final[str] = _env("BEEHIVE_MIC_DTYPE", "int32")

# -------------------------------------------------------------------
# Acoustic analysis
# -------------------------------------------------------------------
FFT_BAND_LOW_HZ: Final[float] = _env_float("BEEHIVE_FFT_LOW", 100.0)
FFT_BAND_HIGH_HZ: Final[float] = _env_float("BEEHIVE_FFT_HIGH", 800.0)
FFT_NOISE_GATE: Final[float] = _env_float("BEEHIVE_FFT_NOISE_GATE", 15.0)

# -------------------------------------------------------------------
# Alert thresholds
# -------------------------------------------------------------------
ALERT_FREQ_CHANGE_THRESHOLD: Final[float] = _env_float("BEEHIVE_ALERT_FREQ_DELTA", 20.0)
ALERT_TEMP_HIGH: Final[float] = _env_float("BEEHIVE_ALERT_TEMP_HIGH", 36.0)
ALERT_TEMP_LOW: Final[float] = _env_float("BEEHIVE_ALERT_TEMP_LOW", 30.0)
ALERT_HUMID_LOW: Final[float] = _env_float("BEEHIVE_ALERT_HUMID_LOW", 40.0)
ALERT_HUMID_HIGH: Final[float] = _env_float("BEEHIVE_ALERT_HUMID_HIGH", 70.0)

WEIGHT_MIN_VALID: Final[float] = _env_float("BEEHIVE_WEIGHT_MIN", -50.0)
WEIGHT_MAX_VALID: Final[float] = _env_float("BEEHIVE_WEIGHT_MAX", 5000.0)
WEIGHT_SUDDEN_JUMP: Final[float] = _env_float("BEEHIVE_WEIGHT_JUMP", 300.0)

ACCEL_Z_EXPECTED_G: Final[float] = _env_float("BEEHIVE_ACCEL_Z_EXPECTED", 1.0)
ACCEL_Z_TOLERANCE: Final[float] = _env_float("BEEHIVE_ACCEL_Z_TOLERANCE", 0.25)
GYRO_ABS_ALERT: Final[float] = _env_float("BEEHIVE_GYRO_ABS_ALERT", 120.0)

MOTION_ACCEL_DELTA: Final[float] = _env_float("BEEHIVE_MOTION_ACCEL_DELTA", 0.20)
MOTION_GYRO_DELTA: Final[float] = _env_float("BEEHIVE_MOTION_GYRO_DELTA", 50.0)

# -------------------------------------------------------------------
# Calibration
# -------------------------------------------------------------------
STABILITY_WINDOW_S: Final[float] = _env_float("BEEHIVE_STABILITY_WINDOW", 3.0)
STABILITY_STD_THRESH: Final[float] = _env_float("BEEHIVE_STABILITY_STD", 1500.0)
CALIBRATION_MAX_ITERATIONS: Final[int] = _env_int("BEEHIVE_CAL_MAX_ITER", 3)
CALIBRATION_TOLERANCE: Final[float] = _env_float("BEEHIVE_CAL_TOLERANCE", 0.03)
DEFAULT_CALIBRATION_WEIGHT_G: Final[float] = _env_float("BEEHIVE_DEFAULT_CAL_WEIGHT", 212.0)

# -------------------------------------------------------------------
# Monitor loop timing
# -------------------------------------------------------------------
MONITOR_CYCLE_SECONDS: Final[float] = _env_float("BEEHIVE_CYCLE_SECONDS", 25.0)
MONITOR_IDLE_SLEEP: Final[float] = _env_float("BEEHIVE_IDLE_SLEEP", 0.1)

# -------------------------------------------------------------------
# Networking / retries
# -------------------------------------------------------------------
NETWORK_MAX_RETRIES: Final[int] = _env_int("BEEHIVE_NET_MAX_RETRIES", 5)
NETWORK_BACKOFF_BASE: Final[float] = _env_float("BEEHIVE_NET_BACKOFF_BASE", 1.5)
NETWORK_BACKOFF_MAX: Final[float] = _env_float("BEEHIVE_NET_BACKOFF_MAX", 60.0)

# -------------------------------------------------------------------
# Watchdog
# -------------------------------------------------------------------
WATCHDOG_HEARTBEAT_FILE: Final[Path] = DATA_DIR / "heartbeat.txt"
WATCHDOG_STALE_SECONDS: Final[float] = _env_float("BEEHIVE_WATCHDOG_STALE", 180.0)

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
LOG_LEVEL: Final[str] = _env("BEEHIVE_LOG_LEVEL", "INFO")
LOG_MAX_BYTES: Final[int] = _env_int("BEEHIVE_LOG_MAX_BYTES", 5 * 1024 * 1024)
LOG_BACKUP_COUNT: Final[int] = _env_int("BEEHIVE_LOG_BACKUP_COUNT", 5)

# -------------------------------------------------------------------
# Process control (used by bot.py to launch/stop monitor.py)
# -------------------------------------------------------------------
MONITOR_SCRIPT: Final[Path] = BASE_DIR / "monitor.py"
PYTHON_EXECUTABLE: Final[str] = _env("BEEHIVE_PYTHON", "python3")

# -------------------------------------------------------------------
# AI module
# -------------------------------------------------------------------
AI_MODEL_PATH: Final[Path] = BASE_DIR / "ai_module" / "bee_acoustic_model.tflite"
AI_CONFIDENCE_THRESHOLD: Final[float] = _env_float("BEEHIVE_AI_THRESHOLD", 0.65)
AI_MFCC_COEFFICIENTS: Final[int] = _env_int("BEEHIVE_AI_N_MFCC", 40)


# -------------------------------------------------------------------
# Startup validation
# -------------------------------------------------------------------
def validate_secrets() -> list:
    """Return a list of missing required secrets."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("BEEHIVE_TELEGRAM_TOKEN")
    if TELEGRAM_AUTHORIZED_USER_ID == 0:
        missing.append("BEEHIVE_ADMIN_ID")
    if not TELEGRAM_LOG_CHANNEL:
        missing.append("BEEHIVE_CHANNEL")
    return missing
