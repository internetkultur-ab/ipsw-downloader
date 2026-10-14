#!/usr/bin/env bash
#
# Installs a LaunchAgent that runs ipsw-downloader.sh every day at 02:00.
# launchd (unlike cron) also runs a missed job after the Mac wakes from sleep.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.internetkultur.ipsw-downloader"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_FILE="$HOME/Library/Logs/ipsw-downloader.log"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$LABEL</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>$SCRIPT_DIR/ipsw-downloader.sh</string>
	</array>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
	</dict>
	<key>StartCalendarInterval</key>
	<dict>
		<key>Hour</key>
		<integer>2</integer>
		<key>Minute</key>
		<integer>0</integer>
	</dict>
	<key>StandardOutPath</key>
	<string>$LOG_FILE</string>
	<key>StandardErrorPath</key>
	<string>$LOG_FILE</string>
	<key>LowPriorityBackgroundIO</key>
	<true/>
	<key>Nice</key>
	<integer>10</integer>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed LaunchAgent: $PLIST"
echo "Runs daily at 02:00, logs to: $LOG_FILE"
echo "Run it right now with: launchctl kickstart gui/$(id -u)/$LABEL"
