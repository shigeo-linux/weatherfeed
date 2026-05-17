import json
import os

CONFIG_DIR = os.path.expanduser('~/.config/weatherfeed')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(CONFIG_DIR, 'weatherfeed.log')

DEFAULTS = {
    'telegram_token': '',
    'telegram_chat_id': '',
    'location_name': '',
    'latitude': '',
    'longitude': '',
    'morning_hour': 7,
    'units': 'metric',
    'last_morning_sent': '',
    'last_alert_sent': '',
    'last_alert_type': '',
    'last_run': '',
    'last_status': '',
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, fallback=None):
        return self._data.get(key, fallback if fallback is not None else DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value

    @property
    def telegram_token(self):
        return self._data.get('telegram_token', '')

    @property
    def telegram_chat_id(self):
        return self._data.get('telegram_chat_id', '')

    @property
    def location_name(self):
        return self._data.get('location_name', '')

    @property
    def latitude(self):
        return self._data.get('latitude', '')

    @property
    def longitude(self):
        return self._data.get('longitude', '')

    @property
    def morning_hour(self):
        return int(self._data.get('morning_hour', 7))

    @property
    def units(self):
        return self._data.get('units', 'metric')

    @property
    def is_metric(self):
        return self.units == 'metric'
