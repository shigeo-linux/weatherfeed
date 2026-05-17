import os
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from config import Config, LOG_FILE
from weather_client import geocode, get_forecast
from formatter import format_morning_report, check_severe_now
from telegram_client import send_message, test_connection, TelegramError

STYLE_PATH = os.path.join(os.path.dirname(__file__), 'style.css')


def _load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE_PATH)
    except Exception:
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def field_label(text):
    lbl = Gtk.Label(label=text, xalign=1)
    lbl.get_style_context().add_class('field-label')
    return lbl


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Weatherfeed')
        self.set_default_size(520, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_icon_name('weatherfeed')
        _load_css()

        self.config = Config()
        self._busy = False
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('Weatherfeed')
        header.set_subtitle('Weather → Telegram')
        self.set_titlebar(header)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_border_width(20)
        main.pack_start(content, True, True, 0)

        # ── Status card ───────────────────────────────────────────
        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_card.get_style_context().add_class('status-card')

        status_title = Gtk.Label(label='Status', xalign=0)
        status_title.get_style_context().add_class('section-title')
        status_card.pack_start(status_title, False, False, 0)

        self._status_label = Gtk.Label(label='Not yet run', xalign=0)
        self._status_label.set_line_wrap(True)
        self._status_label.set_max_width_chars(55)
        self._status_label.get_style_context().add_class('status-pending')
        status_card.pack_start(self._status_label, False, False, 0)

        self._last_run_label = Gtk.Label(label='', xalign=0)
        self._last_run_label.set_ellipsize(3)
        self._last_run_label.set_max_width_chars(55)
        self._last_run_label.get_style_context().add_class('meta-label')
        status_card.pack_start(self._last_run_label, False, False, 0)

        content.pack_start(status_card, False, False, 0)

        # ── Run now ───────────────────────────────────────────────
        run_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._run_btn = Gtk.Button(label='Send Morning Report Now')
        self._run_btn.get_style_context().add_class('action-btn')
        self._run_btn.connect('clicked', self._on_run_now)
        run_row.pack_start(self._run_btn, False, False, 0)
        self._spinner = Gtk.Spinner()
        run_row.pack_start(self._spinner, False, False, 0)
        content.pack_start(run_row, False, False, 0)

        sep = Gtk.Separator()
        content.pack_start(sep, False, False, 0)

        # ── Settings ─────────────────────────────────────────────
        settings_title = Gtk.Label(label='Settings', xalign=0)
        settings_title.get_style_context().add_class('section-title')
        content.pack_start(settings_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # Telegram token
        grid.attach(field_label('Telegram Token:'), 0, 0, 1, 1)
        self._tg_token_entry = Gtk.Entry()
        self._tg_token_entry.set_hexpand(True)
        self._tg_token_entry.set_visibility(False)
        self._tg_token_entry.set_text(self.config.telegram_token)
        self._tg_token_entry.set_placeholder_text('123456789:ABCdef...')
        grid.attach(self._tg_token_entry, 1, 0, 1, 1)

        # Telegram chat ID
        grid.attach(field_label('Telegram Chat ID:'), 0, 1, 1, 1)
        self._tg_chat_entry = Gtk.Entry()
        self._tg_chat_entry.set_text(self.config.telegram_chat_id)
        self._tg_chat_entry.set_placeholder_text('e.g. 7369835363')
        grid.attach(self._tg_chat_entry, 1, 1, 1, 1)

        # Location
        grid.attach(field_label('Location:'), 0, 2, 1, 1)
        loc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._location_entry = Gtk.Entry()
        self._location_entry.set_hexpand(True)
        self._location_entry.set_text(self.config.location_name)
        self._location_entry.set_placeholder_text('e.g. Oslo, Norway')
        self._location_entry.connect('activate', self._on_lookup_location)
        loc_box.pack_start(self._location_entry, True, True, 0)
        lookup_btn = Gtk.Button(label='Look up')
        lookup_btn.connect('clicked', self._on_lookup_location)
        loc_box.pack_start(lookup_btn, False, False, 0)
        grid.attach(loc_box, 1, 2, 1, 1)

        self._location_found_label = Gtk.Label(label='', xalign=0)
        self._location_found_label.get_style_context().add_class('meta-label')
        grid.attach(self._location_found_label, 1, 3, 1, 1)
        if self.config.latitude:
            self._location_found_label.set_markup(
                f'<span color="#2e7d32">✓ {self.config.location_name} ({self.config.latitude}, {self.config.longitude})</span>'
            )

        # Morning report time
        grid.attach(field_label('Morning report time:'), 0, 4, 1, 1)
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self._hour_spin.set_value(self.config.morning_hour)
        self._hour_spin.set_size_request(60, -1)
        time_box.pack_start(self._hour_spin, False, False, 0)
        colon_label = Gtk.Label(label=':00  (24h)')
        colon_label.get_style_context().add_class('field-label')
        time_box.pack_start(colon_label, False, False, 0)
        grid.attach(time_box, 1, 4, 1, 1)

        # Units
        grid.attach(field_label('Units:'), 0, 5, 1, 1)
        units_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._metric_radio = Gtk.RadioButton.new_with_label(None, 'Metric (°C, km/h)')
        self._imperial_radio = Gtk.RadioButton.new_with_label_from_widget(
            self._metric_radio, 'Imperial (°F, mph)')
        if self.config.units == 'imperial':
            self._imperial_radio.set_active(True)
        units_box.pack_start(self._metric_radio, False, False, 0)
        units_box.pack_start(self._imperial_radio, False, False, 0)
        grid.attach(units_box, 1, 5, 1, 1)

        content.pack_start(grid, False, False, 0)

        # Buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        save_btn = Gtk.Button(label='Save Settings')
        save_btn.get_style_context().add_class('action-btn')
        save_btn.connect('clicked', self._on_save)
        btn_row.pack_start(save_btn, False, False, 0)

        test_btn = Gtk.Button(label='Test Telegram')
        test_btn.connect('clicked', self._on_test_telegram)
        btn_row.pack_start(test_btn, False, False, 0)

        log_btn = Gtk.Button(label='View Log')
        log_btn.connect('clicked', self._on_view_log)
        btn_row.pack_end(log_btn, False, False, 0)

        content.pack_start(btn_row, False, False, 0)

        # Status bar
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._status_bar.get_style_context().add_class('status-bar')
        self._bar_label = Gtk.Label(label='', xalign=0)
        self._status_bar.pack_start(self._bar_label, True, True, 0)
        main.pack_start(self._status_bar, False, False, 0)

    def _refresh_status(self):
        last_run = self.config.get('last_run', '')
        last_status = self.config.get('last_status', '')

        ctx = self._status_label.get_style_context()
        if last_status.startswith('OK'):
            self._status_label.set_text(last_status)
            ctx.add_class('status-ok')
            ctx.remove_class('status-error')
            ctx.remove_class('status-pending')
        elif last_status.startswith('Error'):
            self._status_label.set_text(last_status)
            ctx.add_class('status-error')
            ctx.remove_class('status-ok')
            ctx.remove_class('status-pending')
        else:
            self._status_label.set_text('Not yet run')

        self._last_run_label.set_text(f'Last run: {last_run}' if last_run else 'Last run: never')

    def _on_lookup_location(self, widget):
        city = self._location_entry.get_text().strip()
        if not city:
            return
        self._location_found_label.set_text('Looking up…')

        def run():
            try:
                name, lat, lon = geocode(city)
                GLib.idle_add(self._on_lookup_done, name, lat, lon)
            except Exception as e:
                GLib.idle_add(self._on_lookup_error, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_lookup_done(self, name, lat, lon):
        self.config.set('location_name', name)
        self.config.set('latitude', lat)
        self.config.set('longitude', lon)
        self.config.save()
        self._location_entry.set_text(name)
        self._location_found_label.set_markup(
            f'<span color="#2e7d32">✓ Found: {name} ({lat:.4f}, {lon:.4f})</span>'
        )
        self._set_bar(f'Location set to {name}')

    def _on_lookup_error(self, error):
        self._location_found_label.set_markup(f'<span color="#c62828">✗ {error}</span>')
        self._set_bar(f'Location lookup failed: {error}')

    def _on_save(self, btn):
        self.config.set('telegram_token', self._tg_token_entry.get_text().strip())
        self.config.set('telegram_chat_id', self._tg_chat_entry.get_text().strip())
        self.config.set('morning_hour', int(self._hour_spin.get_value()))
        self.config.set('units', 'imperial' if self._imperial_radio.get_active() else 'metric')
        self.config.save()
        self._set_bar('Settings saved.')

    def _on_test_telegram(self, btn):
        token = self._tg_token_entry.get_text().strip()
        chat_id = self._tg_chat_entry.get_text().strip()
        if not token or not chat_id:
            self._show_error('Missing details', 'Enter your Telegram token and chat ID first.')
            return
        try:
            test_connection(token, chat_id)
            self._set_bar('Test message sent to Telegram.')
        except TelegramError as e:
            self._show_error('Telegram test failed', str(e))

    def _on_run_now(self, btn):
        if self._busy or not self.config.latitude:
            if not self.config.latitude:
                self._show_error('No location set', 'Look up and save a location first.')
            return
        self._busy = True
        self._run_btn.set_sensitive(False)
        self._spinner.start()

        def run():
            try:
                data = get_forecast(self.config.latitude, self.config.longitude,
                                    metric=self.config.is_metric)
                msg = format_morning_report(data, self.config.location_name,
                                            metric=self.config.is_metric)
                send_message(self.config.telegram_token, self.config.telegram_chat_id, msg)
                GLib.idle_add(self._on_run_done, True, 'Morning report sent to Telegram.')
            except Exception as e:
                GLib.idle_add(self._on_run_done, False, str(e)[:120])

        threading.Thread(target=run, daemon=True).start()

    def _on_run_done(self, success, msg):
        self._busy = False
        self._spinner.stop()
        self._run_btn.set_sensitive(True)
        self._set_bar(msg)

    def _on_view_log(self, btn):
        if os.path.exists(LOG_FILE):
            subprocess.Popen(['xdg-open', LOG_FILE])
        else:
            self._set_bar('No log file yet.')

    def _set_bar(self, msg):
        self._bar_label.set_text(msg)

    def _show_error(self, title, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()
