# -*- coding: utf-8 -*-
"""
utils/thingspeak.py
====================
Resilient ThingSpeak uploader for the two channels used by the hive
monitor: environment/motion, and weight/audio. Uses a retrying HTTP
session and enforces ThingSpeak's minimum update interval.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

import requests

from config import (
    THINGSPEAK_ENV_MOTION_API_KEY,
    THINGSPEAK_MIN_INTERVAL_S,
    THINGSPEAK_RETRY_BACKOFF,
    THINGSPEAK_RETRY_TOTAL,
    THINGSPEAK_TIMEOUT_S,
    THINGSPEAK_URL,
    THINGSPEAK_WEIGHT_AUDIO_API_KEY,
)
from utils.logger import get_logger
from utils.network import build_http_session

logger = get_logger(__name__)


class ThingSpeakUploader:
    """Uploads sensor readings to two ThingSpeak channels with retry logic."""

    def __init__(self) -> None:
        self._session = build_http_session(
            total=THINGSPEAK_RETRY_TOTAL, backoff=THINGSPEAK_RETRY_BACKOFF
        )
        self._lock = threading.Lock()
        self._last_upload_ts = 0.0

    def _throttle(self) -> None:
        """Enforce ThingSpeak's minimum interval between updates."""
        elapsed = time.time() - self._last_upload_ts
        if elapsed < THINGSPEAK_MIN_INTERVAL_S:
            time.sleep(THINGSPEAK_MIN_INTERVAL_S - elapsed)

    def _post(self, payload: Dict[str, Any]) -> bool:
        with self._lock:
            self._throttle()
            try:
                resp = self._session.post(
                    THINGSPEAK_URL, data=payload, timeout=THINGSPEAK_TIMEOUT_S
                )
                self._last_upload_ts = time.time()
                if resp.status_code != 200 or resp.text.strip() == "0":
                    logger.warning(
                        "ThingSpeak upload rejected: status=%s body=%s",
                        resp.status_code,
                        resp.text[:150],
                    )
                    return False
                return True
            except requests.exceptions.Timeout:
                logger.error("ThingSpeak upload timed out")
                return False
            except requests.exceptions.RequestException as exc:
                logger.error("ThingSpeak upload failed: %s", exc)
                return False

    def upload_env_motion(self, sensor: Dict[str, Any]) -> bool:
        payload = {
            "api_key": THINGSPEAK_ENV_MOTION_API_KEY,
            "field1": sensor.get("temperature"),
            "field2": sensor.get("humidity"),
            "field3": sensor.get("accel_x"),
            "field4": sensor.get("accel_y"),
            "field5": sensor.get("accel_z"),
            "field6": sensor.get("gyro_x"),
            "field7": sensor.get("gyro_y"),
            "field8": sensor.get("gyro_z"),
        }
        return self._post(payload)

    def upload_weight_audio(self, sensor: Dict[str, Any]) -> bool:
        payload = {
            "api_key": THINGSPEAK_WEIGHT_AUDIO_API_KEY,
            "field1": sensor.get("weight"),
            "field3": sensor.get("dominant_freq"),
        }
        return self._post(payload)

    def upload_all(self, sensor: Dict[str, Any]) -> None:
        """Upload both channels, logging (never raising) on failure."""
        ok1 = self.upload_env_motion(sensor)
        ok2 = self.upload_weight_audio(sensor)
        if not (ok1 and ok2):
            logger.warning("One or more ThingSpeak channel uploads failed this cycle")
