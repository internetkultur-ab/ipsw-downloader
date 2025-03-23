# ipsw-downloader
simple script to download wanted ipsw files when available

## Installing
1. Clone the repository and `cd` to it
2. Create a local python enviroment and activate it
```bash
python3 -m venv .venv && source .venv/bin/activate
```
3. Install `requests`
```bash
pip install requests
```
4. Copy `settings_template.py` to `settings.py` and put in the identifiers you want firmware for. If you don't do this you will use whatever I wrote in `settings_standard.py`. 
5. Run the script with `python ipsw-downloader.py`

## Cronjob
I put it my crontab like this
```bash
0 2 * * * ~/git/ipsw-downloader/.venv/bin/python3 ~/git/ipsw-downloader/ipsw-downloader.py > /dev/null 2>&1
```