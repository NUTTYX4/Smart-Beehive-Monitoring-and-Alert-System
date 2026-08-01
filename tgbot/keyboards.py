# -*- coding: utf-8 -*-
"""
tgbot/keyboards.py
====================
Inline keyboard layouts for the BeeHive Monitor Telegram bot.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import TELEGRAM_PUBLIC_CHANNEL_LINK


def main_menu(is_running: bool) -> InlineKeyboardMarkup:
    """Primary member command center keyboard."""
    status_icon = "🟢" if is_running else "🔴"
    keyboard = [
        [InlineKeyboardButton(f"{status_icon} Start Hive Monitor", callback_data="start_init_member")],
        [InlineKeyboardButton("🛑 Stop Monitor", callback_data="stop_script_member")],
        [InlineKeyboardButton("⚖️ Change Calibration", callback_data="change_calibration")],
        [
            InlineKeyboardButton("📄 Check Status", callback_data="status_check"),
            InlineKeyboardButton("🔗 Join Channel", url=TELEGRAM_PUBLIC_CHANNEL_LINK),
        ],
        [
            InlineKeyboardButton("📊 Hive Data (CSV)", callback_data="download_data_csv"),
            InlineKeyboardButton("⚙️ Pi Health", callback_data="check_pi_health"),
        ],
        [
            InlineKeyboardButton("🖥️ System Info", callback_data="system_info"),
            InlineKeyboardButton("⏱️ Uptime", callback_data="uptime_info"),
        ],
        [InlineKeyboardButton("📈 Sensor Readings", callback_data="sensor_readings")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
