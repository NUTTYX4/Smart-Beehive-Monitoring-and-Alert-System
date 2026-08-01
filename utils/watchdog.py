# -*- coding: utf-8 -*-
"""
utils/watchdog.py
==================
Simple file-based heartbeat watchdog. The monitor loop touches a
heartbeat file every cycle; an external systemd timer or cron job
(see README.md) can check its age and restart the service if the
monitor has hung, in addition to the in-process error recovery.
"""

from __future__ import annotations

import time
from pathlib import Path

from config import WATCHDOG_HEARTBEAT_FILE, WATCHDOG_STALE_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


class Heartbeat:
    def __init__(self, path: Path = WATCHDOG_HEARTBEAT_FILE) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def beat(self) -> None:
        try:
            self.path.write_text(str(time.time()))
        except OSError as exc:
            logger.warning("Failed to write heartbeat: %s", exc)

    def is_stale(self, max_age: float = WATCHDOG_STALE_SECONDS) -> bool:
        if not self.path.exists():
            return False
        try:
            last = float(self.path.read_text().strip())
            return (time.time() - last) > max_age
        except (OSError, ValueError):
            return False

    def age_seconds(self) -> float:
        if not self.path.exists():
            return -1.0
        try:
            last = float(self.path.read_text().strip())
            return time.time() - last
        except (OSError, ValueError):
            return -1.0
