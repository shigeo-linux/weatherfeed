#!/bin/bash
set -e

APP_NAME="weatherfeed"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_DIR="/usr/share/applications"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=== Installing ${APP_NAME} ==="

sudo apt-get update -qq
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-requests python3-venv librsvg2-bin

echo "Copying application files..."
sudo mkdir -p "${INSTALL_DIR}"
sudo cp -r "$(dirname "$0")"/* "${INSTALL_DIR}/"
sudo chmod +x "${INSTALL_DIR}/weatherfeed.py"
sudo chmod +x "${INSTALL_DIR}/runner.py"

echo "Creating virtual environment..."
sudo python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"

echo "Installing icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
sudo mkdir -p /usr/share/icons/hicolor/256x256/apps
sudo cp "${INSTALL_DIR}/weatherfeed.svg" /usr/share/icons/hicolor/scalable/apps/weatherfeed.svg
rsvg-convert -w 48 -h 48 "${INSTALL_DIR}/weatherfeed.svg" | sudo tee /usr/share/icons/hicolor/48x48/apps/weatherfeed.png > /dev/null
rsvg-convert -w 256 -h 256 "${INSTALL_DIR}/weatherfeed.svg" | sudo tee /usr/share/icons/hicolor/256x256/apps/weatherfeed.png > /dev/null
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo "Installing desktop entry..."
sudo cp "${INSTALL_DIR}/weatherfeed.desktop" "${DESKTOP_DIR}/"
sudo update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Creating launcher..."
sudo tee /usr/local/bin/weatherfeed > /dev/null << 'EOF'
#!/bin/bash
exec /opt/weatherfeed/venv/bin/python3 /opt/weatherfeed/weatherfeed.py "$@"
EOF
sudo chmod +x /usr/local/bin/weatherfeed

echo "Creating config directory..."
mkdir -p "$HOME/.config/${APP_NAME}"

echo "Installing systemd user timer..."
mkdir -p "${SYSTEMD_USER_DIR}"
cp "${INSTALL_DIR}/weatherfeed.service" "${SYSTEMD_USER_DIR}/weatherfeed.service"
cp "${INSTALL_DIR}/weatherfeed.timer" "${SYSTEMD_USER_DIR}/weatherfeed.timer"
sudo loginctl enable-linger "$(whoami)"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
if systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable weatherfeed.timer
    systemctl --user start weatherfeed.timer
else
    echo "Note: Timer files installed. Run 'systemctl --user enable --now weatherfeed.timer' after logging in."
fi

echo ""
echo "=== Installation complete! ==="
echo "Run: weatherfeed"
echo ""
echo "Next steps:"
echo "  1. Enter your Telegram bot token and chat ID"
echo "  2. Type your city and click 'Look up'"
echo "  3. Set your morning report time and units"
echo "  4. Click 'Send Morning Report Now' to test"
