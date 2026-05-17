import datetime
from weather_client import wmo_label, is_severe, SEVERE_CODES


def _temp_unit(metric):
    return '°C' if metric else '°F'


def _wind_unit(metric):
    return 'km/h' if metric else 'mph'


def format_morning_report(data, location_name, metric=True):
    """Format a morning weather report for Telegram (HTML)."""
    tu = _temp_unit(metric)
    wu = _wind_unit(metric)

    daily = data['daily']
    hourly = data['hourly']
    times = hourly['time']

    now = datetime.datetime.now()
    today_str = now.strftime('%A %-d %B %Y')

    lines = [
        f'🌤 <b>Good Morning — {location_name}</b>',
        f'📅 {today_str}',
        '',
    ]

    day_names = ['Today', 'Tomorrow', 'Day after tomorrow']
    for i in range(min(3, len(daily['time']))):
        date = daily['time'][i]
        code = daily['weather_code'][i]
        tmax = daily['temperature_2m_max'][i]
        tmin = daily['temperature_2m_min'][i]
        precip = daily['precipitation_sum'][i] or 0
        wind_max = daily['wind_speed_10m_max'][i] or 0
        label, icon = wmo_label(code)

        day_label = day_names[i] if i < len(day_names) else date

        line = f'{icon} <b>{day_label}</b>: {tmax:.0f}/{tmin:.0f}{tu}'
        if wind_max:
            line += f'  💨 {wind_max:.0f}{wu}'
        if precip > 0.2:
            line += f'  🌧 {precip:.1f}mm'
        line += f'  — {label}'
        lines.append(line)

    # Check next 12 hours for alerts
    now_str = now.strftime('%Y-%m-%dT%H:00')
    alert_lines = _check_upcoming_severe(hourly, now_str, metric)
    if alert_lines:
        lines.append('')
        lines.append('⚠️ <b>Heads up:</b>')
        lines.extend(alert_lines)

    lines.append('')
    lines.append(f'🕐 <i>Weatherfeed — updated at {now.strftime("%H:%M")}</i>')
    return '\n'.join(lines)


def format_alert(data, location_name, metric=True, reasons=None):
    """Format a severe weather alert for Telegram (HTML)."""
    now = datetime.datetime.now().strftime('%H:%M on %-d %B')
    lines = [
        f'⚠️ <b>WEATHER ALERT — {location_name}</b>',
        '',
    ]
    if reasons:
        lines.extend(reasons)
    lines.append('')
    lines.append('Stay safe! 🌩')
    lines.append(f'<i>Weatherfeed alert at {now}</i>')
    return '\n'.join(lines)


def _check_upcoming_severe(hourly, from_time, metric):
    """Check next 12 hours for severe conditions, return list of warning strings."""
    wu = _wind_unit(metric)
    tu = _temp_unit(metric)
    times = hourly['time']
    warnings = set()

    gust_thresh = 60 if metric else 37
    heat_thresh = 38 if metric else 100
    cold_thresh = -15 if metric else 5

    try:
        start_idx = next(i for i, t in enumerate(times) if t >= from_time)
    except StopIteration:
        return []

    for i in range(start_idx, min(start_idx + 12, len(times))):
        code  = hourly['weather_code'][i] or 0
        gusts = hourly['wind_gusts_10m'][i] or 0
        precip = hourly['precipitation'][i] or 0
        snow  = hourly.get('snowfall', [0]*len(times))[i] or 0
        temp  = hourly.get('temperature_2m', [None]*len(times))[i]

        if code in SEVERE_CODES:
            label, icon = wmo_label(code)
            warnings.add(f'{icon} {label} possible today')
        if gusts >= gust_thresh:
            warnings.add(f'💨 Wind gusts up to {gusts:.0f} {wu}')
        if precip >= 20 if metric else 0.8:
            warnings.add(f'🌊 Flash flood risk')
        elif precip >= 5:
            warnings.add(f'🌧 Heavy rain possible')
        if snow >= 2 if metric else 0.8:
            warnings.add(f'❄️ Heavy snow possible')
        if temp is not None and temp >= heat_thresh:
            warnings.add(f'🌡 Extreme heat: {temp:.0f}{tu}')
        if temp is not None and temp <= cold_thresh:
            warnings.add(f'🥶 Extreme cold: {temp:.0f}{tu}')

    return list(warnings)


def check_severe_now(data, metric=True):
    """Check next 6 hours for severe conditions. Returns (is_severe, reasons, alert_key)."""
    hourly = data['hourly']
    times = hourly['time']
    wu = _wind_unit(metric)
    tu = _temp_unit(metric)

    # Thresholds
    gust_thresh  = 60 if metric else 37    # km/h or mph
    rain_thresh  = 10 if metric else 0.4   # mm/hr or in/hr
    snow_thresh  = 2  if metric else 0.8   # cm/hr or in/hr
    heat_thresh  = 38 if metric else 100   # °C or °F
    cold_thresh  = -15 if metric else 5    # °C or °F
    flood_thresh = 20 if metric else 0.8   # mm/hr or in/hr

    now = datetime.datetime.now().strftime('%Y-%m-%dT%H:00')
    try:
        start_idx = next(i for i, t in enumerate(times) if t >= now)
    except StopIteration:
        return False, [], ''

    reasons = []
    alert_key_parts = set()

    for i in range(start_idx, min(start_idx + 6, len(times))):
        code    = hourly['weather_code'][i] or 0
        gusts   = hourly['wind_gusts_10m'][i] or 0
        precip  = hourly['precipitation'][i] or 0
        snow    = hourly.get('snowfall', [0]*len(times))[i] or 0
        temp    = hourly['temperature_2m'][i] if 'temperature_2m' in hourly else None
        hour    = times[i][11:16]

        # Severe weather codes (thunderstorm, freezing rain, heavy snow, etc.)
        if code in SEVERE_CODES and f'code_{code}' not in alert_key_parts:
            label, icon = wmo_label(code)
            reasons.append(f'{icon} {label} expected around {hour}')
            alert_key_parts.add(f'code_{code}')

        # High wind gusts
        if gusts >= gust_thresh and 'gusts' not in alert_key_parts:
            reasons.append(f'💨 Wind gusts up to {gusts:.0f} {wu} around {hour}')
            alert_key_parts.add('gusts')

        # Flash flood risk
        if precip >= flood_thresh and 'flood' not in alert_key_parts:
            reasons.append(f'🌊 Flash flood risk — {precip:.0f}{"mm" if metric else "in"}/hr around {hour}')
            alert_key_parts.add('flood')
        elif precip >= rain_thresh and 'heavyrain' not in alert_key_parts:
            reasons.append(f'🌧 Heavy rain: {precip:.1f}{"mm" if metric else "in"}/hr around {hour}')
            alert_key_parts.add('heavyrain')

        # Heavy snow
        if snow >= snow_thresh and 'snow' not in alert_key_parts:
            reasons.append(f'❄️ Heavy snow: {snow:.1f}{"cm" if metric else "in"}/hr around {hour}')
            alert_key_parts.add('snow')

        # Extreme heat
        if temp is not None and temp >= heat_thresh and 'heat' not in alert_key_parts:
            reasons.append(f'🌡 Extreme heat: {temp:.0f}{tu}')
            alert_key_parts.add('heat')

        # Extreme cold
        if temp is not None and temp <= cold_thresh and 'cold' not in alert_key_parts:
            reasons.append(f'🥶 Extreme cold: {temp:.0f}{tu}')
            alert_key_parts.add('cold')

    alert_key = ','.join(sorted(alert_key_parts))
    return bool(reasons), reasons, alert_key
