# BeeHive Monitor

A production-ready Raspberry Pi 4 hive monitoring system: acoustic bee
behaviour classification, weight, temperature/humidity, and motion
sensing, with Telegram control and ThingSpeak dashboards.

## Hardware

| Sensor  | Purpose                        | Interface        |
|---------|---------------------------------|-------------------|
| HX711   | Load cell (hive weight)         | 2-wire (DOUT/SCK) |
| DHT22   | Temperature & humidity          | 1-wire GPIO       |
| MPU6050 | Accelerometer / gyroscope       | I2C               |
| INMP441 | MEMS microphone (bee acoustics) | I2S (native)      |

No analog microphone circuitry, MCP3008 ADC, TL072 op-amp, or ADS1115
ADC is used anywhere in this project -- the INMP441 is a digital I2S
device read directly by the Pi's native I2S peripheral via
`sounddevice`/PortAudio.

### Default pin assignments (override via environment variables, see `config.py`)

- HX711: `DOUT` -> GPIO5, `SCK` -> GPIO6
- DHT22: data -> GPIO4
- MPU6050: I2C bus 1 (SDA/SCL), address `0x68`
- INMP441: `SD` -> GPIO20 (I2S DIN), `WS` -> GPIO19 (I2S LRCLK), `SCK` -> GPIO18 (I2S BCLK), `L/R` -> GND (left channel), `VDD` -> 3.3V, `GND` -> GND

## Project layout

```
BeeHiveMonitor/
├── monitor.py            # sensor loop, alerts, CSV, ThingSpeak, Telegram posting
├── bot.py                 # Telegram bot: control panel, health, calibration
├── config.py               # all configuration, secrets, thresholds, GPIO pins
├── requirements.txt
├── install.sh              # one-shot Raspberry Pi installer (apt + venv + systemd)
├── enable_i2s.sh            # configures native I2S for the INMP441
├── services/beehive.service  # systemd unit template
├── audio/                   # I2S capture, filtering, FFT
│   ├── capture.py
│   ├── fft.py
│   └── filters.py
├── sensors/                  # per-sensor drivers
│   ├── hx711_sensor.py
│   ├── mpu6050_sensor.py
│   ├── dht22_sensor.py
│   └── inmp441_sensor.py
├── tgbot/                     # Telegram integration (named to avoid
│   │                            shadowing the python-telegram-bot package)
│   ├── alerts.py
│   ├── commands.py
│   └── keyboards.py
├── utils/                      # logging, calibration, CSV, ThingSpeak, network, watchdog
├── tests/                       # unit tests (hardware-free, run anywhere)
└── logs/
```

## Installation

```bash
git clone <this-repo> BeeHiveMonitor   # or copy the extracted folder to the Pi
cd BeeHiveMonitor
chmod +x install.sh enable_i2s.sh
sudo ./install.sh
sudo reboot   # required the first time, for I2C/I2S overlay changes
```

`install.sh` will:

1. Install system packages (`i2c-tools`, PortAudio, build tools, etc.)
2. Enable I2C (`raspi-config nonint do_i2c 0`)
3. Run `enable_i2s.sh` to add the I2S microphone overlay to
   `/boot/firmware/config.txt`
4. Create a Python virtual environment and install `requirements.txt`
5. Install and enable `beehive.service` (runs `bot.py`, which launches
   `monitor.py` as a managed subprocess)

After rebooting, verify the microphone is visible with `arecord -l`.

## Configuration & secrets

All configuration lives in `config.py` and can be overridden with
environment variables (see the top of that file for the full list),
which is the recommended way to set secrets rather than editing the
file directly, e.g. in `/etc/systemd/system/beehive.service.d/override.conf`:

```ini
[Service]
Environment=BEEHIVE_TELEGRAM_TOKEN=123456:your-new-token
Environment=BEEHIVE_ADMIN_ID=111111111
Environment=BEEHIVE_TS_ENV_KEY=your-thingspeak-write-key
Environment=BEEHIVE_TS_WA_KEY=your-other-thingspeak-write-key
```

**Rotate your credentials.** The Telegram bot token and ThingSpeak
write keys carried over from the legacy scripts were previously stored
in plain Python source. Generate new ones (BotFather `/revoke`,
ThingSpeak channel API settings) and set them only via environment
variables or a systemd override, never by committing them to source
control.

## Telegram bot

`/start` opens the member command center:

- Start / Stop the monitor
- Change calibration (guided, weight-based)
- Check status, Pi health (CPU temp/usage, memory, disk, uptime),
  system info
- View latest sensor readings
- Download the CSV log

Membership is controlled via `data/members.json` (Telegram user IDs);
the configured `BEEHIVE_ADMIN_ID` always has full access.

## Recovery & reliability

- **Network retries**: ThingSpeak and Telegram calls use a retrying
  HTTP session with exponential backoff (`utils/network.py`).
- **Sensor failures**: each sensor module degrades to a safe default
  (0.0 / not-available) rather than crashing, and automatically
  retries hardware connections on the next cycle (I2C, HX711, I2S).
- **Reboot recovery**: calibration is persisted to `data/calibration.json`
  and reloaded automatically if `monitor.py` is started with no
  arguments.
- **Internet outage recovery**: `monitor.py` and `bot.py` wait for
  connectivity at startup and continue looping through outages,
  logging and alerting rather than crashing.
- **Watchdog**: `monitor.py` writes a heartbeat file each cycle
  (`utils/watchdog.py`); pair this with a cron job or systemd timer
  that restarts `beehive.service` if the heartbeat goes stale for
  longer than `BEEHIVE_WATCHDOG_STALE` seconds (default 180s).
- **Process supervision**: `beehive.service` uses `Restart=on-failure`
  so the bot (and therefore the ability to restart the monitor) comes
  back automatically after a crash or reboot.

## Running tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

All tests run without any Raspberry Pi hardware attached -- each
hardware interface is faked/mocked.

## Manual run (development)

```bash
source venv/bin/activate
python3 bot.py
```

`monitor.py` is normally launched by the bot, but can also be run
directly for debugging:

```bash
python3 monitor.py 650 "Dev User" 123456789
```
