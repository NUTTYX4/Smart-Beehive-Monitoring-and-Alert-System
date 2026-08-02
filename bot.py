#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py
======
BeeHive Monitor Telegram bot entry point. Launches and controls
`monitor.py` as a managed subprocess, provides a member command
center with inline keyboards, and exposes Pi health/system info.

Run directly (`python3 bot.py`) or via the provided systemd service.
"""

from __future__ import annotations

import os
import subprocess
import time

import certifi

# Ensure TLS verification uses a trusted, up-to-date CA bundle even on
# minimal Raspberry Pi OS images where the system store may be stale.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from telegram import Update
from telegram.error import NetworkError, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    MEMBERS_FILE,
    TELEGRAM_API_BASE,
    TELEGRAM_AUTHORIZED_USER_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_LOG_CHANNEL,
    TELEGRAM_POLL_TIMEOUT,
    TELEGRAM_READ_TIMEOUT,
    validate_secrets,
)
from tgbot import commands
from tgbot.alerts import send_message
from utils.logger import get_logger
from utils.network import is_internet_reachable, wait_for_internet

logger = get_logger(__name__)

CALLBACK_PATTERN = (
    "^(start_init_member|stop_script_member|status_check|change_calibration|"
    "download_data_csv|check_pi_health|system_info|uptime_info|"
    "sensor_readings|main_menu|manage_admins|request_admin_access|approve_.*|deny_.*)$"
)


def _check_timesync_status() -> dict:
    status = {"synced": False, "ntp": "unknown"}
    try:
        out = subprocess.check_output(
            ["bash", "-lc", "timedatectl status"], timeout=6
        ).decode()
        lines = out.splitlines()
        status["synced"] = any("System clock synchronized: yes" in ln for ln in lines)
        status["ntp"] = "active" if any(
            "NTP service: active" in ln or "systemd-timesyncd.service active: yes" in ln
            for ln in lines
        ) else "inactive"
    except Exception as exc:  # noqa: BLE001
        logger.warning("timedatectl status failed: %s", exc)
    return status


def _enable_timesync_best_effort() -> None:
    for cmd in (
        "sudo -n timedatectl set-ntp true",
        "sudo -n systemctl restart systemd-timesyncd.service",
    ):
        try:
            subprocess.check_call(["bash", "-lc", cmd], timeout=8)
        except Exception as exc:  # noqa: BLE001
            logger.warning("NTP command failed (%s): %s", cmd, exc)


def _ensure_time_sync_and_alert() -> None:
    status = _check_timesync_status()
    if not status["synced"]:
        _enable_timesync_best_effort()
        time.sleep(3.0)
        status = _check_timesync_status()

    if status["synced"]:
        send_message(TELEGRAM_LOG_CHANNEL, f"🕒 *Time sync OK* — NTP: `{status['ntp']}`; clock synchronized.")
    else:
        send_message(
            TELEGRAM_LOG_CHANNEL,
            "⚠️ *Time sync NOT confirmed.*\n"
            "Run the following commands and restart the bot:\n"
            "`sudo timedatectl set-ntp true`\n"
            "`sudo systemctl restart systemd-timesyncd`",
        )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Dispatcher error", exc_info=context.error)
    try:
        await context.bot.send_message(
            chat_id=TELEGRAM_AUTHORIZED_USER_ID, text=f"❌ Bot error: {context.error}"
        )
        await context.bot.send_message(
            chat_id=TELEGRAM_LOG_CHANNEL, text="⚠️ Network hiccup detected. Retrying …", parse_mode="Markdown"
        )
    except TelegramError:
        pass
    if isinstance(context.error, NetworkError):
        time.sleep(5.0)


def build_application() -> Application:
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .base_url(f"{TELEGRAM_API_BASE}/bot")
        .base_file_url(f"{TELEGRAM_API_BASE}/file/bot")
        .read_timeout(TELEGRAM_READ_TIMEOUT)
        .connect_timeout(TELEGRAM_CONNECT_TIMEOUT)
        .build()
    )

    application.add_handler(CommandHandler("start", commands.start, filters=filters.ChatType.PRIVATE))
    application.add_handler(
        CommandHandler("channeltest", commands.channeltest, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("set_ratio", commands.set_ratio, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("addadmin", commands.addadmin, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("deladmin", commands.deladmin, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("admins", commands.list_admins, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(CallbackQueryHandler(commands.manage_script, pattern=CALLBACK_PATTERN))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, commands.handle_message)
    )
    application.add_error_handler(on_error)
    return application


def main() -> None:
    missing = validate_secrets()
    if missing:
        logger.critical("Missing required secrets: %s — set them in environment or token.md", ", ".join(missing))
        raise SystemExit(1)

    logger.info("Starting BeeHive Monitor Telegram bot")

    if not is_internet_reachable():
        logger.warning("No internet detected at startup; waiting for connectivity...")
        wait_for_internet()

    _ensure_time_sync_and_alert()

    if not MEMBERS_FILE.exists():
        commands.save_members({})

    application = build_application()

    send_message(TELEGRAM_LOG_CHANNEL, "🤖 *BeeHive Monitor bot is online.*")
    logger.info("Bot polling started")
    application.run_polling(timeout=TELEGRAM_POLL_TIMEOUT, drop_pending_updates=True)


if __name__ == "__main__":
    main()
