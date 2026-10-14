#!/usr/bin/env bash
#
# ipsw-downloader v2
#
# Keeps the latest IPSW for every device listed in models.json downloaded
# in the firmware folder (Apple Configurator cache by default), using
# blacktop's `ipsw` CLI (https://github.com/blacktop/ipsw) for downloading
# and checksum verification.
#
# - Latest firmware is determined with `ipsw download ipsw --latest --urls`
# - Downloads go through ipsw (SHA1 verified, resumable, parallel CDN)
# - Old firmware is pruned only if it appears in the ipsw.me history of a
#   managed device; unrelated files are never touched
# - Summary is POSTed as JSON {subject, body} to WEBHOOK_URL (config.sh)
#
# Usage: ipsw-downloader.sh [--dry-run|--help]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Local configuration (not tracked in git)
if [ -f "$SCRIPT_DIR/config.sh" ]; then
	# shellcheck source=/dev/null
	. "$SCRIPT_DIR/config.sh"
fi

FIRMWARE_DIR="${FIRMWARE_DIR:-$HOME/Library/Group Containers/K36BKF7T3D.group.com.apple.configurator/Library/Caches/Firmware}"
MODELS_FILE="${MODELS_FILE:-$SCRIPT_DIR/models.json}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
NOTIFY_ALWAYS="${NOTIFY_ALWAYS:-0}"

DRY_RUN=0

usage() {
	cat <<EOF
Usage: $(basename "$0") [--dry-run|--help]

  --dry-run   Report what would happen without downloading, pruning
              or sending notifications.
  --help      Show this help.

Configuration lives in config.sh (see config.sh.example) and models.json.
EOF
}

case "${1:-}" in
--dry-run) DRY_RUN=1 ;;
--help | -h)
	usage
	exit 0
	;;
"") ;;
*)
	echo "Unknown option: $1" >&2
	usage >&2
	exit 2
	;;
esac

for cmd in ipsw jq curl; do
	if ! command -v "$cmd" >/dev/null 2>&1; then
		echo "ERROR: '$cmd' not found in PATH. Install it with: brew install $cmd" >&2
		exit 1
	fi
done

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# contains_line <newline-separated-list> <needle>
contains_line() {
	[ -n "${2:-}" ] || return 1
	printf '%s\n' "$1" | grep -qxF -- "$2"
}

count_lines() {
	printf '%s' "$1" | grep -c '^' || true
}

HOSTNAME_SHORT="$(hostname -s)"
KNOWN_FILES=""    # every filename ever published for the managed devices
LATEST_FILES=""   # expected latest filename per managed device
NEW_DOWNLOADS=""
PRUNED_FILES=""
ERRORS=""
DEVICE_COUNT=0

log "=== ipsw-downloader v2 starting on $HOSTNAME_SHORT (dry-run: $DRY_RUN)"
log "firmware folder: $FIRMWARE_DIR"
log "models file:     $MODELS_FILE"

if [ ! -f "$MODELS_FILE" ]; then
	echo "ERROR: models file not found: $MODELS_FILE" >&2
	exit 1
fi

if [ ! -d "$FIRMWARE_DIR" ]; then
	if [ "$DRY_RUN" -eq 1 ]; then
		log "DRY-RUN: firmware folder does not exist, would create it"
	else
		mkdir -p "$FIRMWARE_DIR"
		log "created firmware folder"
	fi
fi

# ---------------------------------------------------------------- devices ---

while IFS=$'\t' read -r DEVICE_ID DEVICE_NAME; do
	[ -n "$DEVICE_ID" ] || continue
	DEVICE_COUNT=$((DEVICE_COUNT + 1))
	log "--- $DEVICE_NAME ($DEVICE_ID)"

	LATEST_URL="$(ipsw download ipsw --device "$DEVICE_ID" --latest --urls </dev/null 2>/dev/null | grep -E -m1 '^https?://' || true)"
	if [ -z "$LATEST_URL" ]; then
		ERRORS="${ERRORS}Could not determine latest firmware for $DEVICE_NAME ($DEVICE_ID)"$'\n'
		log "ERROR: could not determine latest firmware"
		continue
	fi

	LATEST_FILE="${LATEST_URL##*/}"
	LATEST_FILES="${LATEST_FILES}${LATEST_FILE}"$'\n'
	log "latest: $LATEST_FILE"

	# Collect the full filename history for this device so old versions of
	# *managed* devices can be pruned safely later.
	KNOWN="$(curl -fsS --max-time 30 -H 'Accept: application/json' \
		"https://api.ipsw.me/v4/device/${DEVICE_ID}" 2>/dev/null |
		jq -r '.firmwares[].url | split("/")[-1]' 2>/dev/null || true)"
	if [ -n "$KNOWN" ]; then
		KNOWN_FILES="${KNOWN_FILES}${KNOWN}"$'\n'
	else
		log "WARNING: could not fetch firmware history; old files of this device will not be pruned"
	fi

	if [ -f "$FIRMWARE_DIR/$LATEST_FILE" ]; then
		log "OK: already downloaded"
		continue
	fi

	log "NEW: latest firmware not present locally"
	if [ "$DRY_RUN" -eq 1 ]; then
		NEW_DOWNLOADS="${NEW_DOWNLOADS}[dry-run] $DEVICE_NAME → $LATEST_FILE"$'\n'
		continue
	fi

	log "downloading with ipsw..."
	if ! ipsw download ipsw --device "$DEVICE_ID" --latest --confirm \
		--output "$FIRMWARE_DIR" </dev/null; then
		log "download failed, retrying once..."
		ipsw download ipsw --device "$DEVICE_ID" --latest --confirm \
			--output "$FIRMWARE_DIR" </dev/null || true
	fi

	if [ -f "$FIRMWARE_DIR/$LATEST_FILE" ]; then
		log "DONE: downloaded $LATEST_FILE"
		NEW_DOWNLOADS="${NEW_DOWNLOADS}$DEVICE_NAME → $LATEST_FILE"$'\n'
	else
		ERRORS="${ERRORS}Download failed for $DEVICE_NAME ($DEVICE_ID): $LATEST_FILE"$'\n'
		log "ERROR: download failed for $DEVICE_ID"
	fi
done < <(jq -r 'to_entries[] | [.key, .value] | @tsv' "$MODELS_FILE")

# ----------------------------------------------------------------- pruning ---

log "--- pruning old firmware"
if [ -n "$KNOWN_FILES" ]; then
	for f in "$FIRMWARE_DIR"/*.ipsw; do
		[ -e "$f" ] || continue
		base="${f##*/}"
		if contains_line "$LATEST_FILES" "$base"; then
			log "keeping $base (latest)"
			continue
		fi
		if contains_line "$KNOWN_FILES" "$base"; then
			if [ "$DRY_RUN" -eq 1 ]; then
				log "DRY-RUN: would prune $base"
				PRUNED_FILES="${PRUNED_FILES}[dry-run] $base"$'\n'
			elif rm -f "$f"; then
				log "pruned $base"
				PRUNED_FILES="${PRUNED_FILES}$base"$'\n'
			else
				ERRORS="${ERRORS}Could not prune $base"$'\n'
				log "ERROR: could not prune $base"
			fi
		else
			log "keeping $base (not managed by this script)"
		fi
	done
else
	log "no file history available, nothing to prune"
fi

# ------------------------------------------------------- summary / webhook ---

BODY="ipsw-downloader on ${HOSTNAME_SHORT} at $(date '+%Y-%m-%d %H:%M:%S')
Devices checked: ${DEVICE_COUNT}
"
if [ -n "$NEW_DOWNLOADS" ]; then
	BODY="${BODY}
New downloads:
$(printf '%s' "$NEW_DOWNLOADS" | sed 's/^/- /')
"
fi
if [ -n "$PRUNED_FILES" ]; then
	BODY="${BODY}
Pruned (old versions):
$(printf '%s' "$PRUNED_FILES" | sed 's/^/- /')
"
fi
if [ -n "$ERRORS" ]; then
	BODY="${BODY}
Errors:
$(printf '%s' "$ERRORS" | sed 's/^/- /')
"
fi

N_NEW="$(count_lines "$NEW_DOWNLOADS")"
N_PRUNED="$(count_lines "$PRUNED_FILES")"
N_ERR="$(count_lines "$ERRORS")"
SUBJECT="ipsw-downloader: ${N_NEW} new, ${N_PRUNED} pruned"
if [ "$N_ERR" -gt 0 ]; then
	SUBJECT="${SUBJECT}, ${N_ERR} errors"
fi

log "--- summary"
printf '%s\n' "$BODY"

if [ "$DRY_RUN" -eq 1 ]; then
	log "DRY-RUN: would notify: $SUBJECT"
elif [ "$N_NEW" -gt 0 ] || [ "$N_PRUNED" -gt 0 ] || [ "$N_ERR" -gt 0 ] || [ "$NOTIFY_ALWAYS" = "1" ]; then
	if [ -z "$WEBHOOK_URL" ]; then
		log "WEBHOOK_URL not set; skipping notification"
	else
		PAYLOAD="$(jq -n --arg subject "$SUBJECT" --arg body "$BODY" '{subject: $subject, body: $body}')"
		if curl -fsS --max-time 30 -X POST -H 'Content-Type: application/json' \
			--data "$PAYLOAD" "$WEBHOOK_URL" >/dev/null; then
			log "notification sent to webhook"
		else
			log "ERROR: notification failed"
		fi
	fi
else
	log "nothing new; no notification sent"
fi

if [ -n "$ERRORS" ]; then
	exit 1
fi
exit 0
