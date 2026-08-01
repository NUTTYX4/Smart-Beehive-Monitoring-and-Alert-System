#!/usr/bin/env bash
# install.sh
# ==========
# One-shot installer for BeeHive Monitor on a Raspberry Pi 4 (Raspberry
# Pi OS Bookworm or later). Installs system + Python dependencies,
# enables I2C and I2S, sets up a Python virtual environment, and
# installs/starts the systemd services for the monitor and the bot.
#
# Usage:
#   cd BeeHiveMonitor
#   chmod +x install.sh enable_i2s.sh
#   ./install.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo "=============================================="
echo " BeeHive Monitor Installer"
echo " Project directory: ${PROJECT_DIR}"
echo " Service user:      ${SERVICE_USER}"
echo "=============================================="

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo (needed for apt, I2C/I2S config, and systemd)." >&2
  echo "Try: sudo ./install.sh" >&2
  exit 1
fi

echo "--> Updating apt package index..."
apt-get update -y

echo "--> Installing system packages..."
apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  i2c-tools libatlas-base-dev \
  portaudio19-dev libportaudio2 libasound2-dev \
  git build-essential

echo "--> Enabling I2C interface (for MPU6050)..."
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_i2c 0 || true
else
  echo "raspi-config not found; ensure 'dtparam=i2c_arm=on' is set in /boot/firmware/config.txt manually."
fi

echo "--> Configuring I2S (for INMP441)..."
bash "${PROJECT_DIR}/enable_i2s.sh"

echo "--> Creating Python virtual environment..."
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"

echo "--> Creating data/logs directories..."
mkdir -p "${PROJECT_DIR}/data" "${PROJECT_DIR}/logs"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${PROJECT_DIR}"

echo "--> Installing systemd service (bot.py manages monitor.py as a subprocess)..."
SERVICE_SRC="${PROJECT_DIR}/services/beehive.service"
SERVICE_DST="/etc/systemd/system/beehive.service"

sed \
  -e "s#__PROJECT_DIR__#${PROJECT_DIR}#g" \
  -e "s#__VENV_DIR__#${VENV_DIR}#g" \
  -e "s#__SERVICE_USER__#${SERVICE_USER}#g" \
  "${SERVICE_SRC}" > "${SERVICE_DST}"

systemctl daemon-reload
systemctl enable beehive.service
systemctl restart beehive.service

echo "=============================================="
echo " Installation complete."
echo " Check status with: sudo systemctl status beehive.service"
echo " Tail logs with:    journalctl -u beehive.service -f"
echo "                     or tail -f ${PROJECT_DIR}/logs/beehive.log"
echo ""
echo " IMPORTANT: A reboot is required for I2S/I2C overlay changes"
echo " to take full effect if this is the first install:"
echo "   sudo reboot"
echo "=============================================="
