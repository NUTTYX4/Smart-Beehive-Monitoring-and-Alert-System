# -*- coding: utf-8 -*-
"""
tgbot/keyboards.py
====================
Inline keyboard layouts for the BeeHive Monitor Telegram bot.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import TELEGRAM_PUBLIC_CHANNEL_LINK, TELEGRAM_WEB_DASHBOARD


def main_menu(is_running: bool) -> InlineKeyboardMarkup:
    """Primary member command center keyboard."""
    status_icon = "🟢" if is_running else "🔴"
    keyboard = [
        [InlineKeyboardButton("🌐 Open Live Web Dashboard", url=TELEGRAM_WEB_DASHBOARD)],
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
        [
            InlineKeyboardButton("📈 Sensor Readings", callback_data="sensor_readings"),
            InlineKeyboardButton("👥 Manage Admins", callback_data="manage_admins"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def guest_menu() -> InlineKeyboardMarkup:
    """Public / Guest command center keyboard with read-only access and admin request button."""
    keyboard = [
        [InlineKeyboardButton("🌐 Open Live Web Dashboard", url=TELEGRAM_WEB_DASHBOARD)],
        [
            InlineKeyboardButton("📈 Sensor Readings", callback_data="sensor_readings"),
            InlineKeyboardButton("📄 Check Status", callback_data="status_check"),
        ],
        [InlineKeyboardButton("🔗 Join Channel", url=TELEGRAM_PUBLIC_CHANNEL_LINK)],
        [InlineKeyboardButton("🙋 Request Admin Access", callback_data="request_admin_access")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_approval_keyboard(user_id: int, user_name: str) -> InlineKeyboardMarkup:
    """Inline buttons sent to root admin when a guest requests access."""
    clean_name = user_name.replace("_", " ")[:20]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve Admin Access", callback_data=f"approve_{user_id}_{clean_name}"),
            InlineKeyboardButton("❌ Deny", callback_data=f"deny_{user_id}"),
        ]
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])


def calibration_mode_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for choosing between static bottle tare or standard calibration."""
    keyboard = [
        [InlineKeyboardButton("🍾 Option 1: Static Bottle Attached (~284g)", callback_data="cal_mode_bottle")],
        [InlineKeyboardButton("⚖️ Option 2: No (Standard Calibration)", callback_data="cal_mode_standard")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
