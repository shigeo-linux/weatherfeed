import requests
import datetime

GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'

WMO_CODES = {
    0: ('Clear sky', '☀️'),
    1: ('Mainly clear', '🌤'),
    2: ('Partly cloudy', '⛅'),
    3: ('Overcast', '☁️'),
    45: ('Fog', '🌫'),
    48: ('Icy fog', '🌫'),
    51: ('Light drizzle', '🌦'),
    53: ('Drizzle', '🌦'),
    55: ('Heavy drizzle', '🌦'),
    56: ('Freezing drizzle', '🧊'),
    57: ('Heavy freezing drizzle', '🧊'),
    61: ('Light rain', '🌧'),
    63: ('Rain', '🌧'),
    65: ('Heavy rain', '🌧'),
    66: ('Freezing rain', '🧊'),
    67: ('Heavy freezing rain', '🧊'),
    71: ('Light snow', '🌨'),
    73: ('Snow', '🌨'),
    75: ('Heavy snow', '❄️'),
    77: ('Snow grains', '❄️'),
    80: ('Light showers', '🌦'),
    81: ('Showers', '🌧'),
    82: ('Heavy showers', '⛈'),
    85: ('Snow showers', '🌨'),
    86: ('Heavy snow showers', '❄️'),
    95: ('Thunderstorm', '⛈'),
    96: ('Thunderstorm with hail', '⛈'),
    99: ('Thunderstorm with heavy hail', '⛈'),
}

# Weather codes that warrant a severe alert
SEVERE_CODES = {56, 57, 66, 67, 75, 82, 86, 95, 96, 99}


def geocode(city_name):
    """Search for a city and return (name, latitude, longitude) or raise."""
    # Try queries: full input, then just the first part before any comma
    queries = [city_name.strip()]
    if ',' in city_name:
        queries.append(city_name.split(',')[0].strip())

    for query in queries:
        resp = requests.get(GEOCODE_URL, params={'name': query, 'count': 5}, timeout=10)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        if results:
            r = results[0]
            parts = [r['name']]
            if r.get('admin1'):
                parts.append(r['admin1'])
            if r.get('country'):
                parts.append(r['country'])
            full_name = ', '.join(parts)
            return full_name, r['latitude'], r['longitude']

    raise ValueError(f"Location '{city_name}' not found. Try just the city name e.g. 'Winchester'")


def get_forecast(lat, lon, metric=True):
    """Fetch 3-day forecast from Open-Meteo."""
    wind_unit = 'kmh' if metric else 'mph'
    temp_unit = 'celsius' if metric else 'fahrenheit'

    params = {
        'latitude': lat,
        'longitude': lon,
        'hourly': 'temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,snowfall',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset',
        'timezone': 'auto',
        'forecast_days': 3,
        'temperature_unit': temp_unit,
        'wind_speed_unit': wind_unit,
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def wmo_label(code):
    return WMO_CODES.get(code, ('Unknown', '🌡'))


def is_severe(code, wind_gusts, precip_mm):
    """Return (is_severe, reason) based on weather conditions."""
    reasons = []
    if code >= 95:
        reasons.append(f'⛈ {wmo_label(code)[0]} expected')
    if wind_gusts and wind_gusts >= 60:
        reasons.append(f'💨 Wind gusts up to {wind_gusts:.0f} km/h')
    if precip_mm and precip_mm >= 10:
        reasons.append(f'🌧 Heavy rain: {precip_mm:.0f}mm expected')
    return bool(reasons), reasons
