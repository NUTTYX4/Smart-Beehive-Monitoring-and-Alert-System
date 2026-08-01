# -*- coding: utf-8 -*-
"""
utils/csv_logger.py
====================
Thread-safe CSV logging of hive sensor readings.
"""

from __future__ import annotations

import csv
import os
import threading
from pathlib import Path
from typing import Any, Dict

from config import HIVE_DATA_CSV
from utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = [
    "Timestamp",
    "Temperature (C)",
    "Humidity (%)",
    "Weight (g)",
    "Frequency (Hz)",
    "Behavior",
    "Accel X",
    "Accel Y",
    "Accel Z",
    "Gyro X",
    "Gyro Y",
    "Gyro Z",
]

_lock = threading.Lock()


class CsvLogger:
    """Appends hive sensor rows to a CSV file, creating headers once."""

    def __init__(self, path: Path = HIVE_DATA_CSV) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_header_if_needed(self) -> None:
        with _lock:
            if not self.path.exists() or self.path.stat().st_size == 0:
                try:
                    with open(self.path, "w", newline="") as fh:
                        csv.writer(fh).writerow(_HEADERS)
                except OSError as exc:
                    logger.error("Failed to write CSV header: %s", exc)

    def log(self, data: Dict[str, Any], behavior: str = "") -> None:
        """Append one row of sensor data to the CSV file."""
        self.write_header_if_needed()
        row = [
            data.get("datestamp", ""),
            data.get("temperature", ""),
            data.get("humidity", ""),
            data.get("weight", ""),
            data.get("dominant_freq", ""),
            behavior,
            data.get("accel_x", ""),
            data.get("accel_y", ""),
            data.get("accel_z", ""),
            data.get("gyro_x", ""),
            data.get("gyro_y", ""),
            data.get("gyro_z", ""),
        ]
        with _lock:
            try:
                with open(self.path, "a", newline="") as fh:
                    csv.writer(fh).writerow(row)
            except OSError as exc:
                logger.error("Failed to append CSV row: %s", exc)

    def exists(self) -> bool:
        return self.path.exists() and self.path.stat().st_size > 0

    def size_bytes(self) -> int:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0
