#!/usr/bin/env bash
# enable_i2s.sh
# =============
# Enables the native I2S peripheral on a Raspberry Pi 4 for the INMP441
# MEMS microphone, replacing any analog/ADC microphone configuration.
#
# This adds the standard I2S MEMS microphone overlay to the boot
# config so the device shows up as an ALSA capture device (verify
# afterwards with `arecord -l` following a reboot).
set -euo pipefail

CONFIG_CANDIDATES=("/boot/firmware/config.txt" "/boot/config.txt")
CONFIG_FILE=""
for candidate in "${CONFIG_CANDIDATES[@]}"; do
  if [[ -f "${candidate}" ]]; then
    CONFIG_FILE="${candidate}"
    break
  fi
done

if [[ -z "${CONFIG_FILE}" ]]; then
  echo "Could not locate config.txt (checked: ${CONFIG_CANDIDATES[*]})." >&2
  echo "Please enable I2S manually for your OS image." >&2
  exit 1
fi

echo "--> Using boot config: ${CONFIG_FILE}"

add_line_if_missing() {
  local line="$1"
  if ! grep -qxF "${line}" "${CONFIG_FILE}"; then
    echo "${line}" >> "${CONFIG_FILE}"
    echo "    added: ${line}"
  else
    echo "    already present: ${line}"
  fi
}

# Ensure the base I2S interface is on.
add_line_if_missing "dtparam=i2s=on"

# INMP441 is a standard I2S MEMS microphone; the googlevoicehat-soundcard
# overlay is the well-supported community driver for generic I2S MEMS
# mic breakout boards including the INMP441 (mono, left channel).
add_line_if_missing "dtoverlay=googlevoicehat-soundcard"

echo "--> I2S configuration written. A reboot is required for changes to take effect."
echo "    After rebooting, verify with: arecord -l"
