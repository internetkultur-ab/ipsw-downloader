import requests
import os
import sys
import hashlib
import time
from settings.py import pushover_url, pushover_userkey, pushover_apikey
from settings.py import firmware_folder
from settings.py import identifiers
from settings.py import computer_name

def md5(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


latest_available_files = []





# todo: import pushover settings




keep_files = []
keep_md5sum = []
validated_files = []
fresh_download = False
fresh_downloads = []
print("")
print(" 🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥")
print(" 🟥                                                        🟥")
print(" 🟥 IPSW downloader, a script by                           🟥")
print(" 🟥                                                        🟥")
print(" 🟥            ___                     __   __   __        🟥")
print(" 🟥  /\  |    |__  \_/    |\ | | |    /__` /__` /  \ |\ |  🟥")
print(" 🟥 /~~\ |___ |___ / \    | \| | |___ .__/ .__/ \__/ | \|  🟥")
print(" 🟥                                                        🟥")
print(" 🟥                                🧑‍💻 Internetkultur AB    🟥")
print(" 🟥                                                        🟥")
print(" 🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥")
print("")

print(bcolors.HEADER + "📤 Sending message via Pushover..." + bcolors.ENDC)
pushover_title = "Started script " + computer_name
pushover_priority = "0"
pushover_message = "Let's see if there is anything new to download."
pushover_request = requests.post(pushover_url, data={"token": pushover_apikey, "user": pushover_userkey, "message": pushover_message, "priority": pushover_priority, "title": pushover_title})
pushover_request
print(bcolors.OKGREEN + "📫 Message sent\n" + bcolors.ENDC)


for identifier in identifiers:
	# Create request to ipsw.me api
	headers = { 'Accept': 'application/json' }
	request = requests.get('https://api.ipsw.me/v4/device/' + identifier, headers=headers)
	response_body = request.json()
	latest_available_files.append(response_body['firmwares'][0]['url'].rsplit('/', 1)[-1])
	print(bcolors.HEADER + "❓ Latest available firmware for " + response_body['name'] + ":" + bcolors.ENDC)
	print(bcolors.HEADER + "⌚️ Released " + response_body['firmwares'][0]['releasedate'] + bcolors.ENDC)
	print(bcolors.HEADER + "❗️ " + response_body['firmwares'][0]['url'].rsplit('/', 1)[-1] + bcolors.ENDC)
	if response_body['firmwares'][0]['md5sum'] == "":
		print(bcolors.WARNING + "⚠️  No checksum published!!!\n" + bcolors.ENDC)
	else:
		print(bcolors.HEADER + "❗️ " + response_body['firmwares'][0]['md5sum'] + "\n" + bcolors.ENDC)
	time.sleep(0.5)
	
print(bcolors.HEADER + "🗑  Removing old firmware" + bcolors.ENDC)

for file in os.listdir(firmware_folder):
	if file == ".DS_Store":
		print(bcolors.HEADER + "✅ Keeping .DS_Store" + bcolors.ENDC)
		time.sleep(0.1)
	elif file not in latest_available_files:
		print(bcolors.HEADER + "🧹 Removing " + file  + bcolors.ENDC)
		os.remove(firmware_folder + file)
		time.sleep(0.1)
	elif file in latest_available_files:
		print (bcolors.HEADER + "✅ Keeping " + file + bcolors.ENDC)
		time.sleep(0.1)
print("\n")

for identifier in identifiers:
	
	# Create request to ipsw.me api
	headers = { 'Accept': 'application/json' }
	request = requests.get('https://api.ipsw.me/v4/device/' + identifier, headers=headers)
	response_body = request.json()
	
	# Various variables from response
	latest_available_version = response_body['firmwares'][0]['version']
	latest_available_url = response_body['firmwares'][0]['url']
	latest_available_file = latest_available_url.rsplit('/', 1)[-1]
	latest_available_md5sum = response_body['firmwares'][0]['md5sum']
	
	# Save filename and checksum for cleanup
	keep_md5sum.append(latest_available_md5sum)
	keep_files.append(latest_available_file)
	
	# Lookup latest firmware filename
	print(bcolors.HEADER + "🔎 Looking for new firmware to " + response_body['name'] + bcolors.ENDC)
	print(bcolors.HEADER + "✨ Found version " + latest_available_version + ", filename " + latest_available_file + bcolors.ENDC)

	
	# Check if latest available firmware is already present in local folder
	if os.path.isfile(firmware_folder + latest_available_file):
		# Firmware is present, validating checksum if it's not already validated (duplicate file)
		if latest_available_md5sum == "":
			print(bcolors.WARNING + "⚠️  Firmware already downloaded, but no" + bcolors.ENDC)
			print(bcolors.WARNING + "⚠️  checksum is published, skipping validation\n" + bcolors.ENDC)
		else:
			print(bcolors.HEADER + "🛂 Firmware already downloaded, validating checksum..." + bcolors.ENDC)
			# Is checksum already validated? If not, validate.
			if latest_available_file not in validated_files:
				md5sum = md5(firmware_folder + latest_available_file)
				print(bcolors.HEADER + "🌸 Checksum should be " + latest_available_md5sum + bcolors.ENDC)
				print(bcolors.HEADER + "🟰 Checksum is really " + md5sum + bcolors.ENDC)

				if md5sum in keep_md5sum:
					# Checksum is correct
					print(bcolors.OKGREEN + "✅ Checksum is correct\n" + bcolors.ENDC)
					validated_files.append(latest_available_file)
					download = False
				else:
					# Checksum is wrong, remove file and download
					print(bcolors.FAIL + "❌ Checksum is wrong, removing " + latest_available_file + bcolors.ENDC)
					os.remove(firmware_folder + latest_available_file)
					download = True
			else:
				print(bcolors.OKGREEN + "✅ Checksum is correct\n" + bcolors.ENDC)
	else:
		#Firmware is not present, download
		print(bcolors.HEADER + "❗ Found new firmware")
		download = True

	# Loop download until downloaded file is has a correct checksum
	while download == True:
		with open(firmware_folder + latest_available_file, "wb") as f:
			print(bcolors.OKBLUE + "🚚 Downloading firmware " + latest_available_version + " for " + identifier + bcolors.ENDC)
			response = requests.get(latest_available_url, stream=True)
			total_length = response.headers.get('content-length')
			if total_length is None: # no content length header
				f.write(response.content)
			else:
				dl = 0
				total_length = int(total_length)
				#for data in response.iter_content(chunk_size=4096):
				for data in response.iter_content(chunk_size=int(total_length/100)):
					dl += len(data)
					f.write(data)
					done = int(20 * dl / total_length)
					sys.stdout.write(bcolors.OKBLUE + "\r📈 %s%s" % ('🟢' * done, '⚪' * (20-done)) + bcolors.ENDC)    
					sys.stdout.flush()
		if latest_available_md5sum == "":
			print(bcolors.WARNING + "\n⚠️  No checksum published, skipping validation\n" + bcolors.ENDC)
			validated_files.append(latest_available_file)
			fresh_download = True
			fresh_downloads.append(response_body['name'])
			download = False
		else:
			print(bcolors.HEADER + "\n🛂 Validating checksum of downloaded file..." + bcolors.ENDC)
			md5sum = md5(firmware_folder + latest_available_file)
			if md5sum in keep_md5sum:
				print(bcolors.OKGREEN + "✅ Checksum is correct\n")
				validated_files.append(latest_available_file)
				fresh_download = True
				fresh_downloads.append(response_body['name'])
				download = False
			else:
				print(bcolors.FAIL + "❌ Checksum is wrong, removing " + file + "\n" + bcolors.ENDC)
				os.remove(firmware_folder + latest_available_file)


#print(bcolors.HEADER + "🧹All downloads complete, performing clean up..." + bcolors.ENDC)

#for file in os.listdir(firmware_folder):
#	if file == ".DS_Store":
#		print(bcolors.HEADER + "✅ Keeping .DS_Store" + bcolors.ENDC)
#	elif file not in keep_files:
#		print(bcolors.HEADER + "🧹 Removing " + file  + bcolors.ENDC)
#		os.remove(firmware_folder + file)
#	elif file in keep_files:
#		print (bcolors.HEADER + "✅ Keeping " + file + bcolors.ENDC)
# print(bcolors.OKGREEN + "✅ Cleanup complete\n" + bcolors.ENDC)

# If new files has been downloaded send message via Pushover
if fresh_download == True:
	print(bcolors.HEADER + "📤 Sending message via Pushover..." + bcolors.ENDC)
	pushover_title = "Fresh downloads on " + computer_name
	pushover_priority = "0"
	pushover_message = "Downloaded new firmware:\n"
	for d in fresh_downloads:
		pushover_message += d
		pushover_message += "\n"
	pushover_request = requests.post(pushover_url, data={"token": pushover_apikey, "user": pushover_userkey, "message": pushover_message, "priority": pushover_priority, "title": pushover_title})
	pushover_request
	print(bcolors.OKGREEN + "📫 Message sent" + bcolors.ENDC)
else:
	print(bcolors.HEADER + "📤 Sending message via Pushover..." + bcolors.ENDC)
	pushover_title = "No new downloads on " + computer_name
	pushover_priority = "0"
	pushover_message = "There was nothing new to download."
	pushover_request = requests.post(pushover_url, data={"token": pushover_apikey, "user": pushover_userkey, "message": pushover_message, "priority": pushover_priority, "title": pushover_title})
	pushover_request
	print(bcolors.OKGREEN + "📫 Message sent" + bcolors.ENDC)
