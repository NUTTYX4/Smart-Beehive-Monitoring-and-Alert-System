# -*- coding: utf-8 -*-
"""
utils/logger.py
================
Centralized, rotating, thread-safe logger configuration shared by every
module in the project. Import `get_logger(__name__)` anywhere a logger
is needed instead of calling `logging.basicConfig` repeatedly.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from threading import Lock

from config import APP_LOG_FILE, LOG_BACKUP_COUNT, LOG_LEVEL, LOG_MAX_BYTES

_configured = False
_lock = Lock()

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(threadName)s | %(message)s"


def _configure_root() -> None:
    global _configured
    with _lock:
        if _configured:
            return
        root = logging.getLogger()
        root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

        formatter = logging.Formatter(_FORMAT)

        file_handler = RotatingFileHandler(
            APP_LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

        # Silence noisy third-party libraries a little.
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, configuring the root logger once."""
    _configure_root()
    return logging.getLogger(name)
