# ipsw-downloader (v2)

Bash script that keeps the latest IPSW firmware for your iPhones and iPads
downloaded on your Mac, using [blacktop/ipsw](https://github.com/blacktop/ipsw)
for downloading and checksum verification.

Firmware is stored in the Apple Configurator cache folder, so Configurator
finds it when you restore a device offline.

## What it does

For every device in `MODELS` (defined in your local `config.sh`) it:

1. Asks ipsw what the latest firmware is (no bytes transferred).
2. Downloads it with `ipsw download ipsw --latest` if it's not already in the
   firmware folder. ipsw verifies the SHA1 checksum and resumes partial
   downloads automatically.
3. Prunes old firmware — but only files that ipsw.me lists in the history of a
   *managed* device. Files it doesn't recognize are never touched.
4. POSTs a summary (`{"subject": ..., "body": ...}`) to your webhook endpoint,
   which can turn it into an email.

## Requirements

```bash
brew install ipsw jq
```

(`curl` ships with macOS.)

## Setup

1. Clone the repository and check out the `v2` branch.
2. Create your local config (gitignored):

   ```bash
   cp config.sh.example config.sh
   ```

3. Edit `config.sh`:

   - `MODELS` — the devices you want, as a JSON object. Keys are identifiers
     (find yours at https://ipsw.me or with `ipsw device list`), values are
     friendly names used in notifications:

     ```json
     {
       "iPhone14,6": "iPhone SE (3rd gen)",
       "iPad12,2": "iPad (9th Gen) Cellular"
     }
     ```

   - `WEBHOOK_URL` — your email webhook endpoint (see below), or leave empty
     to disable notifications.
   - Optional: `NOTIFY_ALWAYS`, `FIRMWARE_DIR`.

### Webhook / email

The script POSTs JSON to `WEBHOOK_URL`:

```json
{
  "subject": "ipsw-downloader: 1 new, 2 pruned",
  "body": "ipsw-downloader on my-mac at 2026-10-14 02:00:01\nDevices checked: 2\n\nNew downloads:\n- iPhone SE (3rd gen) → iPhone14,6_27.0.1_24A446_Restore.ipsw\n..."
}
```

A minimal PHP endpoint that forwards it as email:

```php
<?php
$input = json_decode(file_get_contents('php://input'), true);
mail('you@example.com', $input['subject'], $input['body'],
     'From: ipsw-downloader@example.com');
http_response_code(204);
```

No notification is sent when there is nothing new, unless you set
`NOTIFY_ALWAYS=1`.

## Usage

```bash
# Report what would happen without downloading, pruning or notifying
./ipsw-downloader.sh --dry-run

# Real run
./ipsw-downloader.sh
```

## Automatic checks (launchd)

```bash
./install-launchd.sh
```

This installs a LaunchAgent that runs the script daily at 02:00. Unlike cron,
launchd also runs a missed job after the Mac wakes from sleep. Logs go to
`~/Library/Logs/ipsw-downloader.log`.

```bash
# Run it right now
launchctl kickstart gui/$(id -u)/com.internetkultur.ipsw-downloader

# Remove the LaunchAgent
./uninstall-launchd.sh
```

## Notes

- Only the latest firmware per device is kept (one IPSW per device, a few GB).
- The v1 Python script (`ipsw-downloader.py`, `settings_*.py`) lives on the
  `main` branch; v2 replaced it completely.
