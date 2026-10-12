#!/usr/bin/env bash
set -euo pipefail

# AirPoint installer for Ubuntu 24.04 (X11)
# Installs dependencies, creates venv, and sets up launcher and desktop file.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AIRPOINT_DIR="$SCRIPT_DIR"
AIRPOINT_BIN="$HOME/.local/bin/airpoint"
AIRPOINT_DESKTOP="$HOME/.local/share/applications/airpoint.desktop"
AIRPOINT_ICON="$HOME/.local/share/icons/hicolor/scalable/apps/airpoint.svg"
AUTOSTART_DIR="$HOME/.config/autostart"

# Parse arguments
AUTOSTART=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --autostart)
            AUTOSTART=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 1. Install apt dependencies
echo "Installing apt dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-tk python3-dev xdotool scrot

# 2. Create virtual environment and install requirements
echo "Setting up virtual environment..."
cd "$AIRPOINT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 3. Install launcher script
echo "Installing launcher to $AIRPOINT_BIN"
mkdir -p "$(dirname "$AIRPOINT_BIN")"
cat > "$AIRPOINT_BIN" <<'LAUNCHER_EOF'
#!/bin/bash
# AirPoint launcher
# Checks for X11, webcam, and runs the application

# Check for X11 session
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    notify-send "AirPoint" "AirPoint requires X11. Please log out and choose 'Ubuntu on Xorg' at the login screen."
    echo "AirPoint: Error - Wayland session detected. Switch to 'Ubuntu on Xorg'." >&2
    exit 1
fi

# Check for webcam
if [ ! -e /dev/video0 ]; then
    notify-send "AirPoint" "Webcam not found at /dev/video0"
    echo "AirPoint: Error - Webcam not found at /dev/video0" >&2
    exit 1
fi

# Activate venv and run main.py
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"
exec python3 "$SCRIPT_DIR/main.py"
LAUNCHER_EOF
chmod +x "$AIRPOINT_BIN"

# 4. Install .desktop file
echo "Installing desktop file to $AIRPOINT_DESKTOP"
mkdir -p "$(dirname "$AIRPOINT_DESKTOP")"
cat > "$AIRPOINT_DESKTOP" <<'DESKTOP_EOF'
[Desktop Entry]
Name=AirPoint
Comment=Webcam hand gesture mouse controller
Exec=$AIRPOINT_BIN
Icon=airpoint
Terminal=false
Type=Application
Categories=Utility;
DESKTOP_EOF

# 5. Install icon (simple SVG)
echo "Installing icon to $AIRPOINT_ICON"
mkdir -p "$(dirname "$AIRPOINT_ICON")"
cat > "$AIRPOINT_ICON" <<'ICON_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="30" fill="#4a90e2"/>
  <path d="M20 20 L44 44 M20 44 L44 20" stroke="white" stroke-width="4" stroke-linecap="round"/>
</svg>
ICON_EOF

# 6. Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f "$HOME/.local/share/icons/hicolor" || true
fi

# 7. Optional autostart
if $AUTOSTART; then
    echo "Setting up autostart..."
    mkdir -p "$AUTOSTART_DIR"
    cat > "$AUTOSTART_DIR/airpoint.desktop" <<'AUTOSTART_EOF'
[Desktop Entry]
Type=Application
Name=AirPoint
Exec=$AIRPOINT_BIN
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
AUTOSTART_EOF
else
    # Remove autostart if it exists from a previous run
    rm -f "$AUTOSTART_DIR/airpoint.desktop"
fi

echo "AirPoint installed successfully!"
echo "You can now run it from the application menu or via the command: airpoint"
