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
    ACCEL_MAG_TOLERANCE,
    ACCEL_Z_EXPECTED_G,
    ACCEL_Z_TOLERANCE,
    GYRO_ABS_ALERT,
    MOTION_ACCEL_DELTA,
    MOTION_GYRO_DELTA,
    TELEGRAM_API_BASE,
    TELEGRAM_BOT_TOKEN,
    WEIGHT_MAX_VALID,
    WEIGHT_SUDDEN_JUMP,
)
from utils.logger import get_logger
from utils.network import build_http_session
from utils.weather import weather_service

logger = get_logger(__name__)

_session = build_http_session()


# ----------------------------------------------------------------------
# Behaviour classification
# ----------------------------------------------------------------------
def classify_behavior(freq: float) -> Tuple[str, Optional[str]]:
    """Return (status_label, alert_text_or_None) for a dominant frequency."""
    if freq > 450:
        return "Aggressive / Swarming", (
            f"[CRITICAL] Aggressive or Swarm Acoustic Profile ({freq:.2f} Hz)\n"
            "High frequency energy indicates defensive activity or imminent swarming."
        )
    if 330 <= freq <= 450:
        return "Queen Piping", (
            f"[WARNING] Queen Piping Acoustic Signature ({freq:.2f} Hz)\n"
            "Virgin queen signaling detected; colony state change likely."
        )
    if 190 <= freq < 330:
        return "Normal / Active", None
    if 100 <= freq < 190:
        return "Queenless Roar", (
            f"[WARNING] Queenless Roar Signature ({freq:.2f} Hz)\n"
            "Low frequency harmonic resonance indicates colony distress or queenlessness."
        )
    if 0 < freq < 100:
        return "Dormant / Low Activity", None
    return "Unknown / Standby", None


@dataclass
class AlertContext:
    """Previous-cycle state needed to detect sudden changes."""

    prev_freq: float = 0.0
    prev_weight: Optional[float] = None
    prev_accel_mag: Optional[float] = None
    prev_gyro_mag: Optional[float] = None


def build_alerts(sensor: Dict, dominant_freq: float, ctx: AlertContext) -> Tuple[List[str], str]:
    """Evaluate alert criteria against sensor readings and adaptive outdoor weather."""
    alerts: List[str] = []

    # ------------------------------------------------------------------
    # Acoustic behaviour — AI-primary, FFT-fallback
    # ------------------------------------------------------------------
    ai_behavior = sensor.get("behavior", "")
    ai_confidence = sensor.get("confidence", 0.0)

    if ai_behavior:
        status = ai_behavior
        if "Triggered" in ai_behavior:
            alerts.append(
                f"[CRITICAL] Colony Distress State Triggered (AI Confidence: {ai_confidence:.0%})"
            )
    else:
        status, freq_alert = classify_behavior(dominant_freq)
        if freq_alert:
            alerts.append(freq_alert)

    if ctx.prev_freq > 0 and abs(dominant_freq - ctx.prev_freq) >= ALERT_FREQ_CHANGE_THRESHOLD:
        alerts.append(f"[NOTICE] Frequency Shift: {ctx.prev_freq:.2f} Hz -> {dominant_freq:.2f} Hz")

    # Fetch real-time ambient weather to apply dynamic thermodynamic tolerances
    ambient = weather_service.get_current_conditions()
    limits = weather_service.get_adaptive_thresholds(ambient)

    t, h = sensor["temperature"], sensor["humidity"]
    if t > limits["temp_high"]:
        alerts.append(f"[ALERT] Internal Temp High: {t:.1f}°C (Max Allowed: {limits['temp_high']}°C)")
    elif t < limits["temp_low"]:
        alerts.append(f"[ALERT] Internal Temp Low: {t:.1f}°C (Min Allowed: {limits['temp_low']}°C)")
    if h < limits["humid_low"]:
        alerts.append(f"[ALERT] Internal Humidity Low: {h:.1f}% RH (Min Allowed: {limits['humid_low']}%)")
    elif h > limits["humid_high"]:
        alerts.append(f"[ALERT] Internal Humidity High: {h:.1f}% RH (Max Allowed: {limits['humid_high']}%)")

    w = sensor["weight"]
    if w < -2.0:  # Allow minimal settling jitter around 0g tare
        alerts.append(f"[ALERT] Negative Weight Reading: {w:.2f} g")
    if w > WEIGHT_MAX_VALID:
        alerts.append(f"[CRITICAL] Scale Over Capacity: {w:.2f} g (Max: {WEIGHT_MAX_VALID} g)")
    if ctx.prev_weight is not None and abs(w - ctx.prev_weight) >= WEIGHT_SUDDEN_JUMP:
        delta = w - ctx.prev_weight
        direction = "Gain" if delta > 0 else "Loss"
        alerts.append(f"[ALERT] Rapid Weight {direction}: {ctx.prev_weight:.2f} g -> {w:.2f} g (Δ {delta:+.2f} g)")

    ax, ay, az = sensor["accel_x"], sensor["accel_y"], sensor["accel_z"]
    accel_mag = (ax**2 + ay**2 + az**2) ** 0.5
    gx, gy, gz = sensor["gyro_x"], sensor["gyro_y"], sensor["gyro_z"]
    gyro_mag = (gx**2 + gy**2 + gz**2) ** 0.5

    # Use total vector magnitude rather than rigid Z-axis check to prevent false orientation alarms
    if abs(accel_mag - 1.0) > ACCEL_MAG_TOLERANCE:
        alerts.append(f"[WARNING] Structural Shock or Tilt Detected: |a|={accel_mag:.2f}g")
    if any(abs(g) > GYRO_ABS_ALERT for g in (gx, gy, gz)):
        alerts.append(f"[WARNING] High Angular Velocity: Gx={gx:.1f}, Gy={gy:.1f}, Gz={gz:.1f} dps")

    if ctx.prev_accel_mag is not None and abs(accel_mag - ctx.prev_accel_mag) >= MOTION_ACCEL_DELTA:
        d = accel_mag - ctx.prev_accel_mag
        direction = "spike" if d > 0 else "drop"
        alerts.append(f"[NOTICE] Acceleration {direction}: {ctx.prev_accel_mag:.2f}g -> {accel_mag:.2f}g (Δ {d:+.2f}g)")

    if ctx.prev_gyro_mag is not None and abs(gyro_mag - ctx.prev_gyro_mag) >= MOTION_GYRO_DELTA:
        d = gyro_mag - ctx.prev_gyro_mag
        direction = "spike" if d > 0 else "drop"
        alerts.append(f"[NOTICE] Rotational rate {direction}: {ctx.prev_gyro_mag:.1f} -> {gyro_mag:.1f} dps (Δ {d:+.1f})")

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
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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
