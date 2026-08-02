# -*- coding: utf-8 -*-
"""
tgbot/alerts.py
=================
Bee behaviour classification from dominant frequency, full alert-rule
evaluation across acoustics/environment/weight/motion, and resilient
Telegram send helpers used by both `monitor.py` (posting to the public
channel) and `bot.py` (direct messages to members).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

from config import (
    ALERT_FREQ_CHANGE_THRESHOLD,
    ALERT_HUMID_HIGH,
    ALERT_HUMID_LOW,
    ALERT_TEMP_HIGH,
    ALERT_TEMP_LOW,
    ACCEL_Z_EXPECTED_G,
    ACCEL_Z_TOLERANCE,
    GYRO_ABS_ALERT,
    MOTION_ACCEL_DELTA,
    MOTION_GYRO_DELTA,
    TELEGRAM_BOT_TOKEN,
    WEIGHT_MAX_VALID,
    WEIGHT_SUDDEN_JUMP,
)
from utils.logger import get_logger
from utils.network import build_http_session

logger = get_logger(__name__)

_session = build_http_session()


# ----------------------------------------------------------------------
# Behaviour classification
# ----------------------------------------------------------------------
def classify_behavior(freq: float) -> Tuple[str, Optional[str]]:
    """Return (status_label, alert_text_or_None) for a dominant frequency."""
    if freq > 450:
        return "⚔️ Aggressive / Swarming", (
            f"⚔️ *DANGER: Aggression/Swarm Detected!* ({freq:.2f}Hz)\n"
            "_High pitch indicates bees are defensive or taking flight to swarm._"
        )
    if 330 <= freq <= 450:
        return "👑 Queen Piping", (
            f"👑 *ALERT: Queen Piping Detected!* ({freq:.2f}Hz)\n"
            "_Virgin queen is signaling; a swarm may leave the hive soon._"
        )
    if 190 <= freq < 330:
        return "🟢 Normal / Active", None
    if 100 <= freq < 190:
        return "🆘 Queenless Roar", (
            f"🆘 *WARNING: Queenless Roar!* ({freq:.2f}Hz)\n"
            "_Low, chaotic moaning sound indicates distress or a missing queen._"
        )
    if 0 < freq < 100:
        return "💤 Dormant / Low", (
            f"💤 *NOTICE: Low Activity* ({freq:.2f}Hz)\n"
            "_Hive is dormant/sleeping, or the sensor path is obstructed._"
        )
    return "⚪ Unknown / Silence", None


@dataclass
class AlertContext:
    """Previous-cycle state needed to detect sudden changes."""

    prev_freq: float = 0.0
    prev_weight: Optional[float] = None
    prev_accel_mag: Optional[float] = None
    prev_gyro_mag: Optional[float] = None


def build_alerts(sensor: Dict, dominant_freq: float, ctx: AlertContext) -> Tuple[List[str], str]:
    """Evaluate every alert rule against the current sensor snapshot and
    the previous cycle's context. Returns (alerts, behavior_status).

    When the AI engine is active, ``sensor["behavior"]`` is non-empty
    and used as the primary status label. When it is empty (FFT-only
    fallback), ``classify_behavior()`` derives the label from the
    dominant frequency.
    """
    alerts: List[str] = []

    # ------------------------------------------------------------------
    # Acoustic behaviour — AI-primary, FFT-fallback
    # ------------------------------------------------------------------
    ai_behavior = sensor.get("behavior", "")
    ai_confidence = sensor.get("confidence", 0.0)

    if ai_behavior:
        # AI engine provided a classification
        status = ai_behavior
        if "Triggered" in ai_behavior:
            alerts.append(
                f"⚔️ *DANGER: Hive Distress / Panic State Detected!* "
                f"(AI Confidence: {ai_confidence:.0%})"
            )
    else:
        # FFT-only fallback
        status, freq_alert = classify_behavior(dominant_freq)
        if freq_alert:
            alerts.append(freq_alert)

    if ctx.prev_freq > 0 and abs(dominant_freq - ctx.prev_freq) >= ALERT_FREQ_CHANGE_THRESHOLD:
        alerts.append(f"⚠️ *Sudden Freq Shift:* {ctx.prev_freq:.2f}Hz ➡ {dominant_freq:.2f}Hz")

    t, h = sensor["temperature"], sensor["humidity"]
    if t > ALERT_TEMP_HIGH:
        alerts.append(f"🔥 *Too Hot:* {t:.1f}°C")
    elif t < ALERT_TEMP_LOW:
        alerts.append(f"🥶 *Too Cold:* {t:.1f}°C")
    if h < ALERT_HUMID_LOW:
        alerts.append(f"🌵 *Too Dry:* {h:.1f}%")
    elif h > ALERT_HUMID_HIGH:
        alerts.append(f"💧 *Too Humid:* {h:.1f}%")

    w = sensor["weight"]
    if w < 0:
        alerts.append(f"⚖️ *Negative Weight:* {w:.2f} g")
    if w > WEIGHT_MAX_VALID:
        alerts.append(f"⚖️ *Over Capacity:* {w:.2f} g")
    if ctx.prev_weight is not None and abs(w - ctx.prev_weight) >= WEIGHT_SUDDEN_JUMP:
        delta = w - ctx.prev_weight
        direction = "increase" if delta > 0 else "decrease"
        alerts.append(f"⚖️ *Sudden weight {direction}:* {ctx.prev_weight:.2f} g → {w:.2f} g (Δ {delta:+.2f} g)")

    if abs(sensor["accel_z"] - ACCEL_Z_EXPECTED_G) > ACCEL_Z_TOLERANCE:
        alerts.append(f"📈 *Tilt/Movement:* AccZ={sensor['accel_z']:.2f}g")
    if any(abs(g) > GYRO_ABS_ALERT for g in (sensor["gyro_x"], sensor["gyro_y"], sensor["gyro_z"])):
        alerts.append(
            f"🌀 *High Rotation:* Gx={sensor['gyro_x']:.1f}, Gy={sensor['gyro_y']:.1f}, Gz={sensor['gyro_z']:.1f}"
        )

    ax, ay, az = sensor["accel_x"], sensor["accel_y"], sensor["accel_z"]
    accel_mag = (ax**2 + ay**2 + az**2) ** 0.5
    gx, gy, gz = sensor["gyro_x"], sensor["gyro_y"], sensor["gyro_z"]
    gyro_mag = (gx**2 + gy**2 + gz**2) ** 0.5

    if ctx.prev_accel_mag is not None and abs(accel_mag - ctx.prev_accel_mag) >= MOTION_ACCEL_DELTA:
        d = accel_mag - ctx.prev_accel_mag
        direction = "increase" if d > 0 else "decrease"
        alerts.append(f"📳 *Sudden acceleration {direction}:* |a| {ctx.prev_accel_mag:.2f}g → {accel_mag:.2f}g (Δ {d:+.2f}g)")

    if ctx.prev_gyro_mag is not None and abs(gyro_mag - ctx.prev_gyro_mag) >= MOTION_GYRO_DELTA:
        d = gyro_mag - ctx.prev_gyro_mag
        direction = "increase" if d > 0 else "decrease"
        alerts.append(f"🌀 *Sudden rotation {direction}:* |ω| {ctx.prev_gyro_mag:.1f} → {gyro_mag:.1f} (Δ {d:+.1f})")

    ctx.prev_freq = dominant_freq
    ctx.prev_weight = w
    ctx.prev_accel_mag = accel_mag
    ctx.prev_gyro_mag = gyro_mag

    return alerts, status


# ----------------------------------------------------------------------
# Telegram send helpers (used by monitor.py, which has no Bot instance
# of its own -- it talks to the Bot API directly over HTTPS so it does
# not depend on python-telegram-bot's async Updater/Application).
# ----------------------------------------------------------------------
def send_message(chat_id: str, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
    """Send a message via raw Bot API HTTPS call with retry/backoff."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = _session.post(url, data=payload, timeout=10)
        if resp.status_code == 400 and parse_mode is not None:
            # Fallback to plaintext if Markdown entity parsing fails (e.g. usernames with underscores)
            logger.warning("Markdown syntax error in Telegram message, retrying as raw text...")
            payload.pop("parse_mode", None)
            resp = _session.post(url, data=payload, timeout=10)
        if resp.status_code != 200:
            logger.warning("Telegram sendMessage non-200: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except requests.exceptions.RequestException as exc:
        logger.error("Telegram sendMessage failed: %s", exc)
        return False


def send_channel_log(channel: str, text: str) -> bool:
    return send_message(channel, text)


def send_data_and_alerts(channel: str, data_message: str, alerts: List[str]) -> bool:
    alert_section = "\n".join(alerts) + "\n\n" if alerts else ""
    return send_message(channel, alert_section + data_message)
