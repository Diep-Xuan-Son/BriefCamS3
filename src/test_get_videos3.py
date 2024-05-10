import requests
import json
from datetime import datetime, date
import time
import os
import subprocess
from pathlib import Path
import pandas as pd
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
FILE = Path(__file__).parents
ROOT = FILE[0]

url = "http://identity.openstack.demo.mqsolutions.vn/identity/v3/auth/tokens"

payload = json.dumps({
  "auth": {
    "identity": {
      "methods": [
        "password"
      ],
      "password": {
        "user": {
          "name": "admin",
          "domain": {
            "id": "default"
          },
          "password": "123456"
        }
      }
    },
    "scope": {
      "project": {
        "domain": {
          "id": "default"
        },
        "name": "demo"
      }
    }
  }
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

header = response.headers
auth_token = header["X-Subject-Token"]
print(auth_token)
catalog = response.json()["token"]["catalog"]

http_token = None
for cat in catalog:
	if cat["type"]=="object-store" and len(cat["endpoints"])!=0:
		for ep in cat["endpoints"]:
			if ep["interface"]=="public":
				url = ep["url"]
				print(url)
				http_token = url.split("/")[-1]
	else:
		continue

if http_token is not None:
	print(http_token)
#-------------------------------get video storage------------------------------------
#-------------------------
	url = f"http://s3.openstack.demo.mqsolutions.vn/v1/{http_token}/videos_storage"
	camseri = 99
	payload = {}
	headers = {
	  'X-Auth-Token': auth_token
	}
	starttime = int(datetime(2023,10,12,13,34).timestamp())
	endtime = int(datetime(2023,10,12,13,44).timestamp())

	path_video_merged = f'{str(ROOT)}/static/video/video_merged/{starttime}_{endtime}.mp4'
	path_info_merged = f'{os.path.splitext(path_video_merged)[0]}.txt'
	ftxt = open(path_info_merged, 'w')
	
	list_date = pd.date_range(start=date.fromtimestamp(starttime), end=date.fromtimestamp(endtime))
	# print(list_date)
	for dt in list_date.values:
		# print(str(dt).split("T")[0])
		dt = str(dt).split("T")[0]

		response = requests.request("GET", f"{url}?prefix={camseri}/{dt}", headers=headers, data=payload)
		list_file = response.text.split("\n")
		# print(list_file)
		for file in list_file:
			if not file.endswith(".mp4"):
				continue
			# print(file)
			name_vid = os.path.splitext(os.path.basename(file))[0]
			stts = int(name_vid.split("_")[0])
			ents = int(name_vid.split("_")[1])
			if (starttime <= stts and stts < endtime) or (starttime < ents and ents <= endtime): 
				# print(stts)
				r = requests.get(url+f"/{camseri}/{date.fromtimestamp(stts)}/{stts}_{ents}.mp4", headers=headers, allow_redirects=True)
				path_video_5m = f'{str(ROOT)}/static/video/video_download/{stts}_{ents}.mp4'
				open(path_video_5m, 'wb').write(r.content)
				if endtime < ents:
					targetname = f'{str(ROOT)}/static/video/video_download/{stts}_{endtime}.mp4'
					ffmpeg_extract_subclip(path_video_5m, 0, int(endtime-stts), targetname=targetname)
					path_video_5m = targetname
				if starttime > stts:
					targetname = f'{str(ROOT)}/static/video/video_download/{starttime}_{ents}.mp4'
					ffmpeg_extract_subclip(path_video_5m, int(starttime-stts), int(ents-stts), targetname=targetname)
					path_video_5m = targetname
				ftxt.write(f"file '{path_video_5m}'\n")

	ftxt.close()
	subprocess.call(['ffmpeg', '-f', 'concat', '-safe', '0', '-y', '-i', path_info_merged, '-c', 'copy', path_video_merged])
#-----------------------------------
#-----------------------------------

#-----------------------------------
	# num_vid = int((endtime - starttime)/300)
	# print(num_vid)

	# path_video_merged = f'{str(ROOT)}/static/video/video_merged/{starttime}_{endtime}.mp4'
	# path_info_merged = f'{os.path.splitext(path_video_merged)[0]}.txt'
	# ftxt = open(path_info_merged, 'w')
	# for num in range(num_vid):
	# 	ts = starttime + num*300
	# 	r = requests.get(url+f"/{camseri}/{date.fromtimestamp(ts)}/{ts}_{ts+300}.mp4", headers=headers, allow_redirects=True)
	# 	path_video_5m = f'{str(ROOT)}/static/video/video_download/{ts}_{ts+300}.mp4'
		
	# 	open(path_video_5m, 'wb').write(r.content)
	# 	ftxt.write(f"file '{path_video_5m}'\n")
	# ftxt.close()

	# subprocess.call(['ffmpeg', '-f', 'concat', '-safe', '0', '-y', '-i', path_info_merged, '-c', 'copy', path_video_merged])
	
#-------------------------------put video to storage-----------------------------------
	# url = f"http://s3.openstack.demo.mqsolutions.vn/v1/{http_token}/videos_storage"
	# payload = open('videoTest/video4.mp4', 'rb')
	# print(payload)
	# starttime = int(datetime(2023,10,12,13,45).timestamp())
	# endtime = int(datetime(2023,10,12,13,50).timestamp())
	# print(url+f"/99/2023-10-12/{starttime}_{endtime}")
	# response = requests.request("PUT", url+f"/99/2023-10-12/{starttime}_{endtime}.mp4", headers=headers, data=payload)
	# print(response.ok)

