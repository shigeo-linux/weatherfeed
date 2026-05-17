# Weatherfeed

Weather forecasts and severe weather alerts sent to your Telegram chat. Every morning at your chosen time you get a 3-day forecast. Every hour Weatherfeed silently checks for dangerous conditions and sends an alert only when something serious is coming.

Uses [Open-Meteo](https://open-meteo.com/) — completely free, no API key required.

---

## Features

- **Daily morning report** — 3-day forecast with temperature, wind, precipitation and conditions
- **Severe weather alerts** — hourly checks, alerts sent only when conditions warrant it
- **Configurable** — set your location, report time, and metric/imperial in the app
- **Smart alerting** — won't spam you with repeated alerts for the same event
- **Runs automatically** — systemd timer runs every hour in the background
- **GTK settings window** — easy setup and a Run Now button to test

### Severe weather alerts cover

| Condition | Threshold |
|---|---|
| ⛈ Thunderstorm | Any |
| 🧊 Freezing rain / ice storm | Any |
| ❄️ Heavy snow | >2cm/hr |
| 💨 High wind gusts | >60 km/h / 37 mph |
| 🌧 Heavy rain | >10mm/hr |
| 🌊 Flash flood risk | >20mm/hr |
| 🌡 Extreme heat | >38°C / 100°F |
| 🥶 Extreme cold | <-15°C / 5°F |

---

## Requirements

- Ubuntu 24.04 / Linux Mint 22.x (or any systemd-based Linux)
- Python 3.10+
- A Telegram bot token and chat ID

---

## Installation

```bash
cd weatherfeed/
chmod +x install.sh
./install.sh
```

Then launch the settings window:
```bash
weatherfeed
```

---

## Setup Guide

### Step 1 — Create a Telegram Bot (if you don't have one)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Save your **bot token**
4. Start a chat with your bot and send any message
5. Visit `https://api.telegram.org/botYOUR_TOKEN/getUpdates` to find your **chat ID**

### Step 2 — Configure Weatherfeed

1. Launch `weatherfeed`
2. Enter your **Telegram bot token** and **chat ID**
3. Type your city in the **Location** field and click **Look up**
4. Set your **morning report time** (24h format — e.g. `7` for 7:00am)
5. Choose **Metric** or **Imperial**
6. Click **Save Settings**
7. Click **Send Morning Report Now** to test

---

## Telegram message examples

### Morning report
```
🌤 Good Morning — Winchester, Virginia, United States
📅 Saturday 17 May 2026

⛅ Today: 24/12°C  💨 18km/h  🌧 2.1mm  — Partly cloudy
🌧 Tomorrow: 19/10°C  💨 25km/h  🌧 8.4mm  — Rain
🌤 Day after tomorrow: 22/11°C  💨 12km/h  — Mainly clear

🕐 Weatherfeed — updated at 07:00
```

### Severe weather alert
```
⚠️ WEATHER ALERT — Winchester, Virginia, United States

⛈ Thunderstorm expected around 14:00
💨 Wind gusts up to 72 km/h around 15:00
🌊 Flash flood risk — 22mm/hr around 14:00

Stay safe! 🌩
Weatherfeed alert at 13:00 on 17 May
```

---

## Data storage

| Data | Location |
|---|---|
| Settings | `~/.config/weatherfeed/config.json` |
| Activity log | `~/.config/weatherfeed/weatherfeed.log` |

---

## Managing the timer

```bash
# Check timer status
systemctl --user status weatherfeed.timer

# Stop the timer
systemctl --user stop weatherfeed.timer

# Disable the timer
systemctl --user disable weatherfeed.timer
```

---

## Uninstall

```bash
systemctl --user stop weatherfeed.timer
systemctl --user disable weatherfeed.timer
rm ~/.config/systemd/user/weatherfeed.*
sudo rm -rf /opt/weatherfeed
sudo rm -f /usr/local/bin/weatherfeed
sudo rm -f /usr/share/applications/weatherfeed.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/weatherfeed.svg
rm -rf ~/.config/weatherfeed
```
