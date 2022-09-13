# Pushover settings
pushover_url = "https://api.pushover.net/1/messages.json"
pushover_userkey = "xxx"
pushover_apikey = "xxx"

# Change xxx to local username
firmware_folder = "/Users/xxx/Library/Group Containers/K36BKF7T3D.group.com.apple.configurator/Library/Caches/Firmware/"

# Specify what devices to include
identifiers = ['iPhone14,6','iPhone12,8','iPhone10,1','iPhone9,1','iPad7,6','iPad7,12','iPad11,7','iPad12,2', 'iPad13,2', 'iPad11,4']

# Computer name, used when sending messages
computer_name = "Computer name"


# Crontab config
# 30 0 * * * curl https://raw.githubusercontent.com/internetkultur-ab/ipsw-downloader/master/ipsw-downloader.py -fsS -m 10 --retry 5 -o /Users/xxx/scripts/ipsw.py
# 0 1 * * * /usr/local/bin/python3 /Users/xxx/scripts/ipsw.py > /Users/xxx/scripts/latest.log 2>&1