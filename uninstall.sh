#!/usr/bin/env bash
set -euo pipefail

# AirPoint uninstaller
# Removes launcher, desktop file, icon, and optionally config/logs (with confirmation)

AIRPOINT_BIN="$HOME/.local/bin/airpoint"
AIRPOINT_DESKTOP="$HOME/.local/share/applications/airpoint.desktop"
AIRPOINT_ICON="$HOME/.local/share/icons/hicolor/scalable/apps/airpoint.svg"
AUTOSTART_DIR="$HOME/.config/autostart"
AIRPOINT_CONFIG="$HOME/.config/airpoint"
AIRPOINT_LOG="$HOME/.local/state/airpoint"

echo "This will remove AirPoint from your system."
echo "Launcher: $AIRPOINT_BIN"
echo "Desktop file: $AIRPOINT_DESKTOP"
echo "Icon: $AIRPOINT_ICON"
echo "Autostart entry: $AUTOSTART_DIR/airpoint.desktop"
echo ""
echo "Optional: Configuration and logs will be kept unless you choose to delete them."
echo "Config directory: $AIRPOINT_CONFIG"
echo "Log directory: $AIRPOINT_LOG"
echo ""

read -p "Do you want to delete the configuration and log files as well? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing configuration and logs..."
    rm -rf "$AIRPOINT_CONFIG" "$AIRPOINT_LOG"
else
    echo "Keeping configuration and logs."
fi

# Remove launcher, desktop, icon, and autostart
echo "Removing AirPoint files..."
rm -f "$AIRPOINT_BIN" "$AIRPOINT_DESKTOP" "$AIRPOINT_ICON"
rm -f "$AUTOSTART_DIR/airpoint.desktop"

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f "$HOME/.local/share/icons/hicolor" || true
fi

echo "AirPoint has been uninstalled."
