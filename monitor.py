#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor.py
==========
Main hive monitoring loop. Reads the HX711 load cell, DHT22, MPU6050,
and INMP441 (I2S) sensors on a fixed cycle, classifies bee acoustic
behaviour, evaluates alert rules, logs to CSV, uploads to ThingSpeak,
and posts a formatted hive update plus any alerts to the Telegram
channel.

Invoked either directly:
    python3 monitor.py [calibration_weight_g] [starter_name] [starter_id]

or with no arguments, in which case it recovers the last persisted
calibration automatically (post-reboot recovery).
"""

from __future__ import annotations

import os
import signal
import sys
import time
import traceback

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from config import (
    DEFAULT_CALIBRATION_WEIGHT_G,
    MONITOR_CYCLE_SECONDS,
    MONITOR_IDLE_SLEEP,
    TELEGRAM_LOG_CHANNEL,
)
from sensors.dht22_sensor import Dht22Sensor
from sensors.hx711_sensor import HX711Sensor
from sensors.inmp441_sensor import Inmp441Sensor
from sensors.mpu6050_sensor import Mpu6050Sensor
from tgbot.alerts import AlertContext, build_alerts, send_data_and_alerts, send_message
from utils.calibration import load_calibration
from utils.csv_logger import CsvLogger
from utils.logger import get_logger
from utils.network import wait_for_internet
from utils.thingspeak import ThingSpeakUploader
from utils.watchdog import Heartbeat

logger = get_logger(__name__)

_shutdown_requested = False


def _handle_shutdown(signum, frame) -> None:  # noqa: ANN001
    global _shutdown_requested
    logger.info("Received signal %s, shutting down gracefully...", signum)
    _shutdown_requested = True


def _build_hive_update_message(sensor: dict, behavior: str) -> str:
    return f"""
🐝 *HIVE UPDATE* 🐝
🕑 *Time:* `{sensor['datestamp']}`
🔊 *Acoustics*
├ Dominant Freq: `{sensor['dominant_freq']:.2f} Hz`
└ Behavior: *{behavior}*
🌡️ *Environment*
├ Temperature: `{sensor['temperature']:.1f} °C`
└ Humidity: `{sensor['humidity']:.1f} %`
⚖️ *Weight*
└ Current: `{sensor['weight']:.2f} g`
📈 *Motion (Accel)*
├ Ax: `{sensor['accel_x']:.2f} g`
├ Ay: `{sensor['accel_y']:.2f} g`
└ Az: `{sensor['accel_z']:.2f} g`
🌀 *Rotation (Gyro)*
├ Gx: `{sensor['gyro_x']:.1f}`
├ Gy: `{sensor['gyro_y']:.1f}`
└ Gz: `{sensor['gyro_z']:.1f}`
""".strip()


def _parse_args() -> tuple[float, str, str]:
    if len(sys.argv) >= 4:
        try:
            return float(sys.argv[1]), sys.argv[2], sys.argv[3]
        except ValueError:
            logger.warning("Invalid CLI calibration args, falling back to persisted calibration")
    cal = load_calibration()
    return cal.weight_g, cal.owner_name, str(cal.owner_id or "N/A")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    init_weight, starter_name, starter_id = _parse_args()

    logger.info("Initializing sensors...")
    hx711 = HX711Sensor(notify=lambda msg: send_message(TELEGRAM_LOG_CHANNEL, msg))
    mpu6050 = Mpu6050Sensor()
    dht22 = Dht22Sensor()
    inmp441 = Inmp441Sensor()

    csv_logger = CsvLogger()
    thingspeak = ThingSpeakUploader()
    heartbeat = Heartbeat()

    wait_for_internet(max_wait=30.0)

    owner_id = int(starter_id) if str(starter_id).isdigit() else None
    hx711.calibrate(init_weight or DEFAULT_CALIBRATION_WEIGHT_G, starter_name, owner_id)

    send_message(TELEGRAM_LOG_CHANNEL, f"🚀 *Started* by {starter_name}")
    send_message(TELEGRAM_LOG_CHANNEL, "✅ Hive Monitor is online. If you see this, channel posting works.")
    csv_logger.write_header_if_needed()

    ctx = AlertContext()
    last_cycle = 0.0

    logger.info("Entering monitor loop (cycle=%.1fs)", MONITOR_CYCLE_SECONDS)
    try:
        while not _shutdown_requested:
            now = time.time()
            if now - last_cycle >= MONITOR_CYCLE_SECONDS:
                try:
                    _run_cycle(hx711, mpu6050, dht22, inmp441, csv_logger, thingspeak, ctx)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Unhandled error during monitor cycle: %s\n%s", exc, traceback.format_exc())
                    # Never crash: log, alert, and continue on the next cycle.
                    send_message(TELEGRAM_LOG_CHANNEL, f"⚠️ *Monitor cycle error (recovered):* `{exc}`")
                finally:
                    last_cycle = now
                    heartbeat.beat()
            time.sleep(MONITOR_IDLE_SLEEP)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Monitor stopping")
        send_message(TELEGRAM_LOG_CHANNEL, "🛑 *Stopped*")


def _run_cycle(hx711, mpu6050, dht22, inmp441, csv_logger, thingspeak, ctx: AlertContext) -> None:
    from datetime import datetime

    weight = hx711.read_weight_robust()
    climate = dht22.read_median()
    imu = mpu6050.read()
    acoustic = inmp441.read()

    sensor = {
        "datestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "weight": round(weight, 2),
        "temperature": climate.temperature_c,
        "humidity": climate.humidity_pct,
        "dominant_freq": round(acoustic.dominant_freq_hz, 2),
        "accel_x": imu.accel_x, "accel_y": imu.accel_y, "accel_z": imu.accel_z,
        "gyro_x": imu.gyro_x, "gyro_y": imu.gyro_y, "gyro_z": imu.gyro_z,
    }

    if not acoustic.available:
        logger.warning("INMP441 microphone unavailable this cycle; frequency reported as 0.0")

    alerts, behavior = build_alerts(sensor, sensor["dominant_freq"], ctx)

    message = _build_hive_update_message(sensor, behavior)
    send_data_and_alerts(TELEGRAM_LOG_CHANNEL, message, alerts)

    csv_logger.log(sensor, behavior=behavior)
    thingspeak.upload_all(sensor)


if __name__ == "__main__":
    main()
