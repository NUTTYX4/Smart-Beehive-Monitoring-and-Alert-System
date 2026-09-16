# 🐝 Smart Beehive Monitoring & Alert System (SIH Edition)

An enterprise-grade, edge-computing IoT platform for real-time apiary management. This system leverages local sensor fusion and edge AI to monitor colony health, predict honey yields, and detect anomalies—all with **Zero-Cloud Processing Dependency**.

## 🚀 Core Innovations (SIH Focus)

### 1. Edge AI Acoustic Classification
- **Zero-Cloud Processing:** Neural acoustic analysis runs entirely on the Raspberry Pi edge node using a quantized TFLite model.
- **Hardware:** INMP441 MEMS microphone streaming raw I2S digital audio directly into the edge pipeline.
- **Insights:** Detects queenless roar, swarming preparation, and normal hive activity instantly without relying on external cloud compute.

### 2. Multi-Sensor Fusion Engine
Instead of analyzing isolated data streams, the system correlates multiple sensors to identify complex states:
- **Thermodynamic Differential Alerts:** Correlates internal hive temperature (DHT22) with ambient weather APIs to detect structural breaches.
- **Theft / Vandalism Detection:** Fuses MPU6050 accelerometer spikes with sudden HX711 weight drops to trigger immediate tampering alerts.
- **Yield Forecasting:** Analyzes historical weight gain rates from local CSV logs to predict harvest timelines and output volumes.

### 3. Integrated Varroa Management
- **Automated Treatment Tracking:** Logs vaporizer activation, mite counts, and treatment duration to a localized `treatment_log.csv`.
- **Conversational UX:** Admins can query treatment statistics and trigger manual visual scans directly via the localized Telegram Bot.

---

## 🏗️ Hardware Architecture

| Sensor  | Purpose                        | Interface        |
|---------|---------------------------------|-------------------|
| HX711   | Load cell (hive weight)         | 2-wire (DOUT/SCK) |
| DHT22   | Temperature & humidity          | 1-wire GPIO       |
| MPU6050 | Accelerometer / gyroscope       | I2C               |
| INMP441 | MEMS microphone (bee acoustics) | I2S (native)      |

*(No analog circuitry or external ADCs required. 100% digital I2S and GPIO interfaces ensure maximum signal integrity).*

### Default Pin Assignments

- **HX711:** `DOUT` -> GPIO5, `SCK` -> GPIO6
- **DHT22:** data -> GPIO4
- **MPU6050:** I2C bus 1 (SDA/SCL), address `0x68`
- **INMP441:** `SD` -> GPIO20, `WS` -> GPIO19, `SCK` -> GPIO18

---

## 🛠️ Installation & Deployment

```bash
git clone <this-repo> BeeHiveMonitor
cd BeeHiveMonitor
chmod +x install.sh enable_i2s.sh
sudo ./install.sh
sudo reboot   # Required for I2C/I2S overlays
```

The installer configures system packages, I2S overlays, Python environments, and installs the orchestrator as a resilient `systemd` background service (`beehive.service`).

---

## 📱 Telegram Command Center

The system provides a localized ChatOps interface for administrators. Send `/start` to the bot to access:
- **System Control:** Start, stop, and recalibrate sensors.
- **Varroa Management:** View treatment logs and manually trigger AI camera scans.
- **Yield Forecasting:** Query estimated harvest dates based on recent weight telemetry.
- **Diagnostics:** Check Pi CPU, RAM, disk, and sensor health.

---

## 📡 ThingSpeak IoT Dashboard

While computation happens on the edge, lightweight telemetry is synced to ThingSpeak for real-time visualization:
- Custom HTML/JS dashboard (`frontend/index.html`) renders synchronized charts and data tables.
- Network-resilient uploaders cache and retry submissions during connectivity drops.

## 🛡️ Reliability & Fault Tolerance
- **Graceful Degradation:** If a sensor disconnects (e.g., I2C bus error), the orchestrator flags the data point but continues processing the remaining sensors.
- **Watchdog Recovery:** Continuous heartbeat monitoring automatically restarts services if the main thread hangs.
- **Persistent State:** Calibrations and logs are synced to local JSON and CSV stores.
