# -*- coding: utf-8 -*-
"""
utils/calibration.py
=====================
Persistence for HX711 scale calibration (ratio, reference weight, and
the Telegram user who performed the calibration) so the monitor can
recover its calibration automatically after a reboot or restart.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import CALIBRATION_FILE, DEFAULT_CALIBRATION_WEIGHT_G
from utils.logger import get_logger

logger = get_logger(__name__)
_lock = threading.Lock()


@dataclass
class CalibrationData:
    weight_g: float = DEFAULT_CALIBRATION_WEIGHT_G
    scale_ratio: float = 1.0
    owner_id: Optional[int] = None
    owner_name: str = "System"
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return asdict(self)


def load_calibration(path: Path = CALIBRATION_FILE) -> CalibrationData:
    """Load calibration from disk, returning defaults if unavailable."""
    with _lock:
        if not path.exists():
            return CalibrationData()
        try:
            with open(path, "r") as fh:
                raw = json.load(fh)
            return CalibrationData(
                weight_g=float(raw.get("weight_g", DEFAULT_CALIBRATION_WEIGHT_G)),
                scale_ratio=float(raw.get("scale_ratio", 1.0)),
                owner_id=raw.get("owner_id") or raw.get("starter_id"),
                owner_name=raw.get("owner_name") or raw.get("starter_name", "System"),
                timestamp=raw.get("timestamp", ""),
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to load calibration (%s), using defaults", exc)
            return CalibrationData()


def save_calibration(
    weight_g: float,
    scale_ratio: float,
    owner_name: str = "System",
    owner_id: Optional[int] = None,
    path: Path = CALIBRATION_FILE,
) -> None:
    """Persist calibration data to disk."""
    data = CalibrationData(
        weight_g=float(weight_g),
        scale_ratio=float(scale_ratio),
        owner_id=owner_id,
        owner_name=owner_name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    with _lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as fh:
                json.dump(data.to_dict(), fh, indent=2)
        except OSError as exc:
            logger.error("Failed to persist calibration: %s", exc)
