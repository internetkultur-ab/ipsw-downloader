#!/usr/bin/env bash
#
# Removes the LaunchAgent installed by install-launchd.sh.

set -euo pipefail

LABEL="com.internetkultur.ipsw-downloader"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"

echo "Uninstalled LaunchAgent: $LABEL"
