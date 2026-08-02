# -*- coding: utf-8 -*-
"""
tgbot/commands.py
====================
Command and callback handlers for the BeeHive Monitor Telegram bot,
built on `python-telegram-bot` v20+ (async `Application` API).

Responsibilities:
    * Member/admin authorization
    * Start / stop / restart the monitor subprocess
    * Guided calibration flow (initial + change)
    * Status, sensor readings, CSV download
    * Pi health: CPU temp/usage, memory, disk, uptime, system info
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import signal
import subprocess
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Dict, Optional

import psutil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import (
    CALIBRATION_FILE,
    HIVE_DATA_CSV,
    MEMBERS_FILE,
    MONITOR_SCRIPT,
    PYTHON_EXECUTABLE,
    TELEGRAM_AUTHORIZED_USER_ID,
    TELEGRAM_LOG_CHANNEL,
    TELEGRAM_PUBLIC_CHANNEL_LINK,
)
from tgbot import keyboards
from utils.calibration import save_calibration
from utils.logger import get_logger

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# Process/runtime state (single-process bot, so module-level state is
# fine; guarded implicitly by the asyncio event loop being single
# threaded for handler execution).
# ----------------------------------------------------------------------
_state: Dict[str, Optional[object]] = {
    "process": None,       # subprocess.Popen | None
    "runner_id": None,     # int | None
    "runner_name": None,   # str | None
}
_start_time = time.time()


# ----------------------------------------------------------------------
# Member management
# ----------------------------------------------------------------------
def load_members() -> dict:
    if not MEMBERS_FILE.exists():
        return {}
    try:
        with open(MEMBERS_FILE, "r") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to load members file: %s", exc)
        return {}


def save_members(members: dict) -> None:
    try:
        MEMBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMBERS_FILE, "w") as fh:
            json.dump(members, fh, indent=4)
    except OSError as exc:
        logger.error("Failed to save members file: %s", exc)


def is_member(user_id: int) -> bool:
    return str(user_id) in load_members()


def _actor(update: Update):
    if update.effective_user:
        return update.effective_user
    return None


def restricted_admin(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **kw):
        user = _actor(update)
        if user is None:
            return
        if user.id != TELEGRAM_AUTHORIZED_USER_ID:
            if update.message:
                await update.message.reply_text("🛑 Admin only access.")
            elif update.callback_query:
                await update.callback_query.answer("🛑 Admin only access.", show_alert=True)
            return
        return await func(update, context, *a, **kw)

    return wrapper


def member_required(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **kw):
        user = _actor(update)
        if user is None:
            return
        if user.id != TELEGRAM_AUTHORIZED_USER_ID and not is_member(user.id):
            if update.message:
                await update.message.reply_text("🛑 Access Denied. Only approved members can send commands.")
            elif update.callback_query:
                await update.callback_query.answer(
                    "🛑 Access Denied. Only approved members can send commands.", show_alert=True
                )
            return
        return await func(update, context, *a, **kw)

    return wrapper


# ----------------------------------------------------------------------
# Monitor process control
# ----------------------------------------------------------------------
def _is_running() -> bool:
    proc = _state["process"]
    return proc is not None and proc.poll() is None


def _launch_monitor(weight_g: float, user_name: str, user_id: str) -> None:
    _state["process"] = subprocess.Popen(
        [PYTHON_EXECUTABLE, str(MONITOR_SCRIPT), str(weight_g), user_name, user_id],
        text=True,
        cwd=str(MONITOR_SCRIPT.parent),
    )
    _state["runner_id"] = int(user_id) if str(user_id).isdigit() else None
    _state["runner_name"] = user_name.split("(")[0].strip()


def _stop_monitor() -> None:
    proc = _state["process"]
    if proc is not None:
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error stopping monitor process: %s", exc)
    _state["process"] = None
    _state["runner_id"] = None
    _state["runner_name"] = None


# ----------------------------------------------------------------------
# /start and main menu
# ----------------------------------------------------------------------
@member_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_calibration"] = False
    context.user_data["awaiting_calibration_change"] = False
    await update.message.reply_text(
        "*Member Command Center*\n\nUse the buttons below to open the live web dashboard, check sensor telemetry, and control the monitoring script.",
        reply_markup=keyboards.main_menu(_is_running()),
        parse_mode=ParseMode.MARKDOWN,
    )


@restricted_admin
async def channeltest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.send_message(
            chat_id=TELEGRAM_LOG_CHANNEL, text="✅ Channel test message", parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text("Sent test message to channel.")
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"Failed to post: {exc}")


# ----------------------------------------------------------------------
# System info helpers
# ----------------------------------------------------------------------
def _cpu_temperature_c() -> Optional[float]:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as fh:
            return round(int(fh.read().strip()) / 1000.0, 1)
    except (OSError, ValueError):
        return None


def _uptime_str() -> str:
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    days, rem = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"


def _bot_uptime_str() -> str:
    delta = timedelta(seconds=int(time.time() - _start_time))
    return str(delta)


def _pi_health_text() -> str:
    temp = _cpu_temperature_c()
    temp_str = f"{temp:.1f}°C" if temp is not None else "N/A"
    cpu_pct = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return (
        "⚙️ *System Health*\n\n"
        f"🌡️ CPU Temp: `{temp_str}`\n"
        f"🧮 CPU Usage: `{cpu_pct:.1f}%`\n"
        f"💾 Memory: `{mem.percent:.1f}%` used ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)\n"
        f"💿 Disk: `{disk.percent:.1f}%` used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
        f"⏱️ System Uptime: `{_uptime_str()}`\n"
        f"🤖 Bot Uptime: `{_bot_uptime_str()}`"
    )


def _system_info_text() -> str:
    return (
        "🖥️ *System Information*\n\n"
        f"Platform: `{platform.system()} {platform.release()}`\n"
        f"Machine: `{platform.machine()}`\n"
        f"Python: `{platform.python_version()}`\n"
        f"Hostname: `{platform.node()}`\n"
        f"CPU Cores: `{psutil.cpu_count(logical=True)}`"
    )


def _latest_sensor_row() -> Optional[str]:
    """Return the last CSV row (most recent sensor reading) as text."""
    if not HIVE_DATA_CSV.exists():
        return None
    try:
        with open(HIVE_DATA_CSV, "r") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        if len(lines) < 2:
            return None
        headers = lines[0].split(",")
        values = lines[-1].split(",")
        pairs = zip(headers, values)
        return "\n".join(f"*{h}:* `{v}`" for h, v in pairs)
    except OSError as exc:
        logger.error("Failed to read latest sensor row: %s", exc)
        return None


# ----------------------------------------------------------------------
# Callback query router
# ----------------------------------------------------------------------
async def manage_script(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data
    uid = query.from_user.id

    restricted_actions = {
        "start_init_member", "stop_script_member", "change_calibration",
    }
    if action in restricted_actions and uid != TELEGRAM_AUTHORIZED_USER_ID and not is_member(uid):
        await query.answer("🛑 Access Denied.", show_alert=True)
        return

    if action == "start_init_member":
        await _handle_start_request(update, context)
    elif action == "stop_script_member":
        await _handle_stop(update, context)
    elif action == "status_check":
        status = f"🟢 Running (by {_state['runner_name']})" if _is_running() else "🔴 Stopped"
        await query.answer(f"System Status: {status}", show_alert=True)
    elif action == "change_calibration":
        await _handle_change_calibration(update, context)
    elif action == "download_data_csv":
        await _handle_download_csv(update, context)
    elif action == "check_pi_health":
        await query.edit_message_text(
            _pi_health_text(), reply_markup=keyboards.back_to_menu(), parse_mode=ParseMode.MARKDOWN
        )
    elif action == "system_info":
        await query.edit_message_text(
            _system_info_text(), reply_markup=keyboards.back_to_menu(), parse_mode=ParseMode.MARKDOWN
        )
    elif action == "uptime_info":
        await query.answer(f"System: {_uptime_str()} | Bot: {_bot_uptime_str()}", show_alert=True)
    elif action == "sensor_readings":
        row = _latest_sensor_row()
        text = row if row else "ℹ️ No sensor data logged yet."
        await query.edit_message_text(
            f"📈 *Latest Sensor Readings*\n\n{text}",
            reply_markup=keyboards.back_to_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif action == "main_menu":
        await query.edit_message_text(
            "*Member Command Center*\n\nUse the buttons below to open the live web dashboard, check sensor telemetry, and control the monitoring script.",
            reply_markup=keyboards.main_menu(_is_running()),
            parse_mode=ParseMode.MARKDOWN,
        )


async def _handle_start_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if _is_running():
        await query.answer(f"🔴 Already running by {_state['runner_name']}", show_alert=True)
        return

    cal = {}
    try:
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, "r") as fh:
                cal = json.load(fh)
    except (OSError, json.JSONDecodeError):
        pass

    user = query.from_user
    user_name = f"{user.full_name} (@{user.username or user.id})"
    user_id_str = str(user.id)

    if "weight_g" in cal:
        weight = cal["weight_g"]
        _launch_monitor(weight, user_name, user_id_str)
        await query.edit_message_text(
            f"🚀 *Monitor STARTED* using stored calibration `{weight}`g.", parse_mode=ParseMode.MARKDOWN
        )
    else:
        context.user_data["starting_user_info"] = user_name
        context.user_data["starting_user_id"] = user_id_str
        context.user_data["awaiting_calibration"] = True
        await query.edit_message_text(
            "⚖️ *Calibration*\n\nType known weight (g).\nExample: `650`", parse_mode=ParseMode.MARKDOWN
        )


async def _handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = query.from_user.id
    if not _is_running():
        await query.edit_message_text("ℹ️ Script was not running.")
        return
    is_admin = uid == TELEGRAM_AUTHORIZED_USER_ID
    is_owner = uid == _state["runner_id"]
    if not (is_admin or is_owner):
        await query.answer(f"🛑 Only Admin or {_state['runner_name']} can stop.", show_alert=True)
        return
    _stop_monitor()
    await query.edit_message_text("🛑 *Script Stopped safely.*", parse_mode=ParseMode.MARKDOWN)


async def _handle_change_calibration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = query.from_user.id

    cal_owner_id = None
    try:
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, "r") as fh:
                cal_owner_id = json.load(fh).get("owner_id")
    except (OSError, json.JSONDecodeError):
        pass

    is_admin = uid == TELEGRAM_AUTHORIZED_USER_ID
    is_owner = cal_owner_id is None or uid == cal_owner_id
    is_runner = _state["runner_id"] is not None and uid == _state["runner_id"]

    if not (is_admin or is_owner or is_member(uid)):
        await query.answer("🛑 Access Denied.", show_alert=True)
        return

    if _is_running():
        if not (is_admin or is_runner):
            await query.answer(
                f"🛑 Only Admin or the current runner ({_state['runner_name']}) can stop to recalibrate.",
                show_alert=True,
            )
            return
        _stop_monitor()

    context.user_data["awaiting_calibration_change"] = True
    await query.edit_message_text(
        "⚖️ *Change Calibration*\n\nType new known weight (g).\nExample: `650`", parse_mode=ParseMode.MARKDOWN
    )


async def _handle_download_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not HIVE_DATA_CSV.exists():
        await query.answer("❌ No data file yet.", show_alert=True)
        return
    try:
        with open(HIVE_DATA_CSV, "rb") as fh:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=fh,
                filename=f"hive_data_{datetime.now().strftime('%Y%m%d')}.csv",
                caption="📊 *Hive Sensor Log*",
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as exc:  # noqa: BLE001
        await context.bot.send_message(chat_id=query.from_user.id, text=f"❌ Error: {exc}")


# ----------------------------------------------------------------------
# Free-text message handling (calibration weight entry)
# ----------------------------------------------------------------------
@member_required
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    user = update.effective_user

    if context.user_data.get("awaiting_calibration"):
        await _apply_calibration_and_start(
            update, context, text,
            user_name=context.user_data.get("starting_user_info", "Unknown"),
            user_id=context.user_data.get("starting_user_id", "N/A"),
            flag="awaiting_calibration",
            success_msg="✅ *Calibration Complete!*\n\nMonitor RUNNING with `{w}`g.",
        )
        return

    if context.user_data.get("awaiting_calibration_change"):
        user_name = f"{user.full_name} (@{user.username or user.id})"
        await _apply_calibration_and_start(
            update, context, text,
            user_name=user_name,
            user_id=str(user.id),
            flag="awaiting_calibration_change",
            success_msg="✅ *Calibration Updated.* Monitor STARTED with `{w}`g.",
        )
        return


async def _apply_calibration_and_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_name: str,
    user_id: str,
    flag: str,
    success_msg: str,
) -> None:
    try:
        weight = float(text)
    except ValueError:
        await update.message.reply_text("❌ Invalid number.")
        return

    try:
        owner_id = int(user_id) if str(user_id).isdigit() else update.effective_user.id
        save_calibration(weight, 1.0, owner_name=user_name, owner_id=owner_id)
        _launch_monitor(weight, user_name, user_id)
        await update.message.reply_text(success_msg.format(w=text), parse_mode=ParseMode.MARKDOWN)
        context.user_data[flag] = False
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"❌ Failed: {exc}")


# ----------------------------------------------------------------------
# /set_ratio — direct scale ratio tuning
# ----------------------------------------------------------------------
@member_required
async def set_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/set_ratio <float_value> — directly update the HX711 scale ratio
    without running a full calibration cycle. The new ratio is persisted
    to ``data/calibration.json`` so it survives reboots.

    Restricted to admins and approved members.
    """
    if not context.args:
        await update.message.reply_text(
            "Usage: `/set_ratio <float_value>`\n"
            "Example: `/set_ratio 423.567890`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        new_ratio = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Provide a float value.")
        return

    if new_ratio == 0.0:
        await update.message.reply_text("❌ Ratio cannot be zero.")
        return

    user = update.effective_user
    user_name = f"{user.full_name} (@{user.username or user.id})"

    # Load existing calibration to preserve the weight_g field
    cal = {}
    try:
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, "r") as fh:
                cal = json.load(fh)
    except (OSError, json.JSONDecodeError):
        pass

    weight_g = cal.get("weight_g", 0.0)
    save_calibration(weight_g, new_ratio, owner_name=user_name, owner_id=user.id)

    await update.message.reply_text(
        f"✅ *Scale ratio updated*\n\n"
        f"New ratio: `{new_ratio:.6f}`\n"
        f"Persisted to `calibration.json`\n\n"
        f"_Note: The running monitor will pick up the new ratio on next restart._",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("Scale ratio set to %.6f by %s", new_ratio, user_name)

