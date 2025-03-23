import requests
import os
import sys
import hashlib
import time
import socket
from settings import identifiers

home_directory = os.environ.get("HOME")
computer_name = socket.gethostname().split(".")[0]

firmware_folder = (
    home_directory
    + "/Library/Group Containers/K36BKF7T3D.group.com.apple.configurator/Library/Caches/Firmware/"
)

ntfytopic = "https://ntfy.sh/ipsw-" + computer_name


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def notify_admin(message):
    requests.post(ntfytopic, data=message.encode(encoding="utf-8"), headers={})
    time.sleep(0.5)
    print(message)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


latest_available_files = []
keep_files = []
keep_md5sum = []
validated_files = []
fresh_download = False
fresh_downloads = []


notify_admin("Started script on " + computer_name)
print("Pushing messages to " + ntfytopic + "\n")
message = "Checking for firmware folder, should exist at \n" + firmware_folder + "\n"
if os.path.exists(firmware_folder):
    message = message + "👍 Yes, folder exists\n"
else:
    message = message + "👎 No, folder does not exist. Creating folder...\n"
    os.mkdir(firmware_folder)
    message = message + "👍 Folder created\n"

notify_admin(message)

message = ""
for identifier in identifiers:
    message = message + identifier + "\n"
notify_admin(message)

# Go through device list and collect filenames to know which files to not delete
for identifier in identifiers:
    # Create request to ipsw.me api
    headers = {"Accept": "application/json"}
    request = requests.get(
        "https://api.ipsw.me/v4/device/" + identifier, headers=headers
    )
    response_body = request.json()
    latest_available_files.append(
        response_body["firmwares"][0]["url"].rsplit("/", 1)[-1]
    )

    message = "❓ Latest available firmware for " + response_body["name"] + ":\n"
    message = (
        message
        + "⌚️ Version "
        + response_body["firmwares"][0]["version"]
        + ", build "
        + response_body["firmwares"][0]["buildid"]
        + "\n"
    )
    message = (
        message + "⌚️ Released " + response_body["firmwares"][0]["releasedate"] + "\n"
    )
    message = (
        message
        + "❗️ Filename: "
        + response_body["firmwares"][0]["url"].rsplit("/", 1)[-1]
        + "\n"
    )
    # Print checksum if one is available
    if response_body["firmwares"][0]["md5sum"] == "":
        message = message + "⚠️  No checksum available!!!\n"
    else:
        message = (
            message + "❗️ Checksum: " + response_body["firmwares"][0]["md5sum"] + "\n"
        )
    time.sleep(0.5)
    notify_admin(message)

# To make space we need to first remove all unwanted firmware
message = "🗑  Removing old firmware\n"

for file in os.listdir(firmware_folder):
    if file == ".DS_Store":
        message = message + "✅ Keeping .DS_Store\n"
        time.sleep(0.1)
    elif file not in latest_available_files:
        message = message + "🧹 Removing " + file + "\n"
        os.remove(firmware_folder + file)
        time.sleep(0.1)
    elif file in latest_available_files:
        message = message + "✅ Keeping " + file + "\n"
        time.sleep(0.1)

notify_admin(message)

# Go through device list again. Validate already downloaded firmware and download new firmware.

for identifier in identifiers:
    # Create request to ipsw.me api
    headers = {"Accept": "application/json"}
    request = requests.get(
        "https://api.ipsw.me/v4/device/" + identifier, headers=headers
    )
    response_body = request.json()

    # Various variables from response
    latest_available_version = response_body["firmwares"][0]["version"]
    latest_available_url = response_body["firmwares"][0]["url"]
    latest_available_file = latest_available_url.rsplit("/", 1)[-1]
    latest_available_md5sum = response_body["firmwares"][0]["md5sum"]

    # Save filename and checksum for cleanup
    keep_md5sum.append(latest_available_md5sum)
    keep_files.append(latest_available_file)

    # Lookup latest firmware filename
    message = "🔎 Looking for new firmware to " + response_body["name"] + "\n"
    message = (
        message
        + "✨ Latest version is "
        + latest_available_version
        + ", filename "
        + latest_available_file
        + "\n"
    )

    # Check if latest available firmware is already present in local folder
    if os.path.isfile(firmware_folder + latest_available_file):
        # Firmware is present, validating checksum if it's not already validated (duplicate file)
        if latest_available_md5sum == "":
            message = (
                message
                + "⚠️  Firmware already downloaded, but no checksum is available, skipping validation\n"
            )
            download = False
        else:
            message = (
                message + "🛂 Firmware already downloaded, validating checksum...\n"
            )
            # Is checksum already validated? If not, validate.
            if latest_available_file not in validated_files:
                md5sum = md5(firmware_folder + latest_available_file)
                message = (
                    message + "🌸 Checksum should be " + latest_available_md5sum + "\n"
                )
                message = message + "🟰 Checksum is really " + md5sum + "\n"

                if md5sum in keep_md5sum:
                    # Checksum is correct
                    message = message + "✅ Checksum is correct\n"
                    validated_files.append(latest_available_file)
                    download = False
                else:
                    # Checksum is wrong, remove file and download
                    message = (
                        message
                        + "❌ Checksum is wrong, removing "
                        + latest_available_file
                        + "\n"
                    )
                    os.remove(firmware_folder + latest_available_file)
                    download = True
            else:
                message = message + "✅ Checksum is correct\n"
    else:
        # Firmware is not present, download
        message = message + "❗ Found new firmware\n"
        download = True
    notify_admin(message)

    # Loop download until downloaded file is has a correct checksum
    while download == True:
        # The downloading part
        with open(firmware_folder + latest_available_file, "wb") as f:
            message = (
                "🚚 Downloading firmware "
                + latest_available_version
                + " for "
                + identifier
                + "\n"
            )
            notify_admin(message)
            response = requests.get(latest_available_url, stream=True)
            total_length = response.headers.get("content-length")

            # Nice looking download graph if content length header is present
            if total_length is None:
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=int(total_length / 100)):
                    dl += len(data)
                    f.write(data)
                    done = int(20 * dl / total_length)
                    sys.stdout.write(
                        bcolors.OKBLUE
                        + "\r📈 %s%s" % ("🟢" * done, "⚪" * (20 - done))
                        + bcolors.ENDC
                    )
                    sys.stdout.flush()

        # Validate checksum of downloaded file, if checksum is available
        if latest_available_md5sum == "":
            message = "⚠️  No checksum available, skipping validation\n"
            validated_files.append(latest_available_file)
            fresh_download = True
            fresh_downloads.append(response_body["name"])
            download = False
            notify_admin(message)
        else:
            message = "🛂 Validating checksum of downloaded file...\n"
            md5sum = md5(firmware_folder + latest_available_file)
            # Exit loop if checksum is valid, if not remove and download again
            if md5sum in keep_md5sum:
                message = message + "✅ Checksum is correct\n"
                validated_files.append(latest_available_file)
                fresh_download = True
                fresh_downloads.append(response_body["name"])
                download = False
                notify_admin(message)
            else:
                message = message + "❌ Checksum is wrong, removing " + file + "\n"
                os.remove(firmware_folder + latest_available_file)
                notify_admin(message)


# Notify admin
if fresh_download == True:
    admin_message = "Downloaded new firmware:\n"
    for d in fresh_downloads:
        admin_message += d
        admin_message += "\n"
    notify_admin(admin_message)
else:
    notify_admin("There was nothing new to download.")
