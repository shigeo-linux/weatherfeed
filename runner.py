#!/usr/bin/env python3
"""
Weatherfeed runner — called every hour by systemd timer.
Sends morning report at configured time, alerts for severe weather.
"""
import sys
import os
import datetime
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, LOG_FILE
from weather_client import get_forecast
from formatter import format_morning_report, format_alert, check_severe_now
from telegram_client import send_message, TelegramError

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)


def run():
    config = Config()
    now = datetime.datetime.now()
    now_str = now.isoformat(sep=' ', timespec='seconds')

    if not config.latitude or not config.longitude:
        logging.error("No location configured.")
        config.set('last_status', 'Error: No location configured — open Weatherfeed to set up')
        config.save()
        sys.exit(1)

    try:
        logging.info("Fetching forecast")
        data = get_forecast(config.latitude, config.longitude, metric=config.is_metric)

        sent_anything = False

        # ── Morning report ─────────────────────────────────────────
        last_morning = config.get('last_morning_sent', '')
        today_date = now.strftime('%Y-%m-%d')
        if now.hour == config.morning_hour and last_morning != today_date:
            logging.info("Sending morning report")
            msg = format_morning_report(data, config.location_name, metric=config.is_metric)
            send_message(config.telegram_token, config.telegram_chat_id, msg)
            config.set('last_morning_sent', today_date)
            sent_anything = True

        # ── Severe weather alert ───────────────────────────────────
        severe, reasons, alert_key = check_severe_now(data, metric=config.is_metric)
        last_alert_key = config.get('last_alert_type', '')
        last_alert_sent = config.get('last_alert_sent', '')

        # Only send if new alert type or last alert was > 6 hours ago
        should_alert = severe and alert_key and (
            alert_key != last_alert_key or
            not last_alert_sent or
            (now - datetime.datetime.fromisoformat(last_alert_sent)).seconds > 21600
        )

        if should_alert:
            logging.info(f"Sending severe weather alert: {alert_key}")
            msg = format_alert(data, config.location_name, metric=config.is_metric, reasons=reasons)
            send_message(config.telegram_token, config.telegram_chat_id, msg)
            config.set('last_alert_sent', now_str)
            config.set('last_alert_type', alert_key)
            sent_anything = True

        status = 'OK'
        if sent_anything:
            status = 'OK — report sent' if now.hour == config.morning_hour else 'OK — alert sent'
        else:
            status = f'OK — checked at {now.strftime("%H:%M")}, no alerts'

        config.set('last_run', now_str)
        config.set('last_status', status)
        config.save()
        logging.info(status)

    except TelegramError as e:
        msg = f'Telegram error: {str(e)[:120]}'
        logging.error(msg)
        config.set('last_run', now_str)
        config.set('last_status', f'Error: {msg}')
        config.save()
        sys.exit(1)

    except Exception as e:
        msg = str(e)[:120]
        logging.error(f"Error: {msg}")
        config.set('last_run', now_str)
        config.set('last_status', f'Error: {msg}')
        config.save()
        sys.exit(1)


if __name__ == '__main__':
    run()
