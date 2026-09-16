import os
import re

# 1. Modify vision_engine.py
f = "ai_module/camera_model/vision_engine.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

content = content.replace(
    '_DEFAULT_MODEL_PATH  = "ai_module/camera_model/varroa_nano.pt"',
    '_DEFAULT_MODEL_PATH  = "ai_module/camera_model/varroa_nano.onnx"'
)

infer_search = """                with self._lock:
                    self._latest_result = {"""
infer_replace = """                try:
                    out_path = Path("data/latest_vision.jpg")
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(out_path), results[0].plot())
                except Exception as exc:
                    logger.error("Failed to save vision frame: %s", exc)

                with self._lock:
                    self._latest_result = {"""

content = content.replace(infer_search, infer_replace)

with open(f, "w", encoding="utf-8") as file:
    file.write(content)

# 2. Modify tgbot/alerts.py
f = "tgbot/alerts.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

send_photo_code = """
def send_photo(chat_id: str, photo_path: str, caption: str = "") -> bool:
    \"\"\"Send a photo via raw Bot API HTTPS call.\"\"\"
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            resp = _session.post(url, data=payload, files=files, timeout=15)
        if resp.status_code != 200:
            logger.warning("Telegram sendPhoto non-200: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as exc:
        logger.error("Telegram sendPhoto failed: %s", exc)
        return False
"""
content += send_photo_code

with open(f, "w", encoding="utf-8") as file:
    file.write(content)

# 3. Modify tgbot/keyboards.py
f = "tgbot/keyboards.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

kb_search = """        [InlineKeyboardButton("📊 Download Log (CSV)", callback_data="download_data_csv"),
         InlineKeyboardButton("🌡️ Check Sensor Telemetry", callback_data="sensor_readings")],
        [InlineKeyboardButton("👥 Manage Admins", callback_data="manage_admins"),"""

kb_replace = """        [InlineKeyboardButton("📊 Download Log (CSV)", callback_data="download_data_csv"),
         InlineKeyboardButton("🌡️ Check Sensor Telemetry", callback_data="sensor_readings")],
        [InlineKeyboardButton("📷 Request Photo & AI Scan", callback_data="request_photo")],
        [InlineKeyboardButton("👥 Manage Admins", callback_data="manage_admins"),"""

content = content.replace(kb_search, kb_replace)
with open(f, "w", encoding="utf-8") as file:
    file.write(content)

# 4. Modify tgbot/commands.py
f = "tgbot/commands.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

cmd_restrict_s = '"cal_mode_bottle", "cal_mode_standard",'
cmd_restrict_r = '"cal_mode_bottle", "cal_mode_standard", "request_photo",'
content = content.replace(cmd_restrict_s, cmd_restrict_r)

cmd_handler_s = """    elif action == "main_menu":"""
cmd_handler_r = """    elif action == "request_photo":
        await query.answer("📷 Capturing... this might take a moment.", show_alert=True)
        photo_path = "data/latest_vision.jpg"
        if not os.path.exists(photo_path):
            await query.edit_message_text(
                "❌ No recent photo available. Ensure the monitor is running.",
                reply_markup=keyboards.back_to_menu()
            )
            return
        try:
            with open(photo_path, "rb") as f:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=f,
                    caption="*📷 LATEST HIVE CAMERA SCAN*\\nHere is the most recent AI analysis.",
                    parse_mode=ParseMode.MARKDOWN
                )
            # Send an empty menu text so we can show the back button below the photo
            await context.bot.send_message(
                chat_id=uid,
                text="_Photo sent above._",
                reply_markup=keyboards.back_to_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as exc:
            logger.error("Failed to send photo: %s", exc)
            await query.edit_message_text(f"❌ Failed to send photo: {exc}", reply_markup=keyboards.back_to_menu())
    elif action == "main_menu":"""

content = content.replace(cmd_handler_s, cmd_handler_r)
with open(f, "w", encoding="utf-8") as file:
    file.write(content)

# 5. Modify monitor.py
f = "monitor.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

mon_s = """    message = _build_hive_update_message(sensor, behavior)
    send_data_and_alerts(TELEGRAM_LOG_CHANNEL, message, alerts)

    csv_logger.log(sensor, behavior=behavior)"""

mon_r = """    message = _build_hive_update_message(sensor, behavior)
    send_data_and_alerts(TELEGRAM_LOG_CHANNEL, message, alerts)

    if vaporizer_active:
        from tgbot.alerts import send_photo
        photo_path = "data/latest_vision.jpg"
        if os.path.exists(photo_path):
            send_photo(TELEGRAM_LOG_CHANNEL, photo_path, caption=f"🚨 *VAPORIZER TRIGGERED*\\nMite count: {mite_count}")

    csv_logger.log(sensor, behavior=behavior)"""

content = content.replace(mon_s, mon_r)
with open(f, "w", encoding="utf-8") as file:
    file.write(content)

print("PYTHON SCRIPT EXECUTED SUCCESSFULLY.")
