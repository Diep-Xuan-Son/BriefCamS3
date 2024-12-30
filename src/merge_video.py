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
	
#-------------------------------put video to storage-----------------------------------
# url = f"http://s3.openstack.demo.mqsolutions.vn/v1/AUTH_2124913abbf7435da225ded55d7d977f/videos_storage"
# payload = open('videoTest/video4.mp4', 'rb')
# # print(payload)
# starttime = datetime(2023,10,12,13,45).timestamp()
# endtime = datetime(2023,10,12,13,50).timestamp()
# print(url+f"/99/2023-10-12/{starttime}_{endtime}")
# headers = {
# 	'X-Auth-Token': "gAAAAABlKL4PoHhMbifvMHXKITNOSTZokJFOwaSw07febO4cDj1Fc9c4CBFpV5tvdn1sOWUE7DpkrR8U1gJzONTvzTWGIXpp04quNl2tnS-TgRzofuRnumiC9EGDawPEAyXypmE7exDpq5b7jf_je6gvPCh1JjajsduDsyUOKjXglFXBPaJW-Mg"
# }
# response = requests.request("PUT", url+f"/99/2023-10-12/{starttime}_{endtime}.mp4", headers=headers, data=payload)
# print(response.ok)

def get_token(url_auth):
	url = url_auth
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
	subject_token = header["X-Subject-Token"]
	print("------------subject_token:", subject_token)
	catalog = response.json()["token"]["catalog"]

	auth_token = None
	for cat in catalog:
		if cat["type"]=="object-store" and len(cat["endpoints"])!=0:
			for ep in cat["endpoints"]:
				if ep["interface"]=="public":
					url = ep["url"]
					auth_token = url.split("/")[-1]
		else:
			continue
	print("--------------auth_token: ", auth_token)
	return auth_token, subject_token


def get_merge_video(start_times, end_times, camseris, url_auth, url_access, folder_storage="videos_storage"):
	auth_token, subject_token = get_token(url_auth)
	headers = {
	  'X-Auth-Token': subject_token
	}
	if auth_token is not None:
		url = f"{url_access}/{auth_token}/{folder_storage}"

		# starttime = datetime(2023,10,12,13,30).timestamp()
		# endtime = datetime(2023,10,12,13,45).timestamp()
		# camseri = 99

		path_videos = []
		for i, starttime in enumerate(start_times):
			num_vid = int((end_times[i] - starttime)/300)
			print("----------------num_vid: ", num_vid)

			path_video_merged = f'{str(ROOT)}/static/video/video_merged/{starttime}_{end_times[i]}.mp4'
			path_info_merged = f'{os.path.splitext(path_video_merged)[0]}.txt'
			ftxt = open(path_info_merged, 'w')
			for num in range(num_vid):
				ts = starttime + num*300
				r = requests.get(url+f"/{camseris[i]}/{date.fromtimestamp(ts)}/{ts}_{ts+300}.mp4", headers=headers, allow_redirects=True)
				path_video_5m = f'{str(ROOT)}/static/video/video_download/{ts}_{ts+300}.mp4'
				
				open(path_video_5m, 'wb').write(r.content)
				ftxt.write(f"file '{path_video_5m}'\n")
			ftxt.close()

			subprocess.call(['ffmpeg', '-f', 'concat', '-safe', '0', '-y', '-i', path_info_merged, '-c', 'copy', path_video_merged])
			path_videos.append(path_video_merged)
		return {"video": path_videos}

	else:
		return {"video": None, "error": "Authentication token is None"}

def get_merge_video_custom(start_times, end_times, camseris, url_auth, url_access, folder_storage="videos_storage", job_id=""):
	if url_access.startswith(("http","https")):
		auth_token, subject_token = get_token(url_auth)
		headers = {
		  'X-Auth-Token': subject_token
		}
		if auth_token is not None:
			url = f"{url_access}/{auth_token}/{folder_storage}"

			# starttime = datetime(2023,10,12,13,30).timestamp()
			# endtime = datetime(2023,10,12,13,45).timestamp()
			# camseri = 99
			path_merged = f'{str(ROOT)}/static/video/video_merged/{job_id}'
			if not os.path.exists(path_merged):
				os.mkdir(path_merged)
			path_download = f'{str(ROOT)}/static/video/video_download/{job_id}'
			if not os.path.exists(path_download):
				os.mkdir(path_download)

			path_videos = []
			for i, starttime in enumerate(start_times):
				endtime = end_times[i]
				camseri = camseris[i]
				# camseri = "99"
				path_video_merged = f'{path_merged}/{starttime}_{endtime}.mp4'
				path_info_merged = f'{os.path.splitext(path_video_merged)[0]}.txt'
				ftxt = open(path_info_merged, 'w')

				list_date = pd.date_range(start=date.fromtimestamp(starttime), end=date.fromtimestamp(endtime))
				# print("----list_date: ", list_date)
				for dt in list_date.values:
					dt = str(dt).split("T")[0]
					response = requests.request("GET", f"{url}?prefix={camseri}/{dt}", headers=headers, data={})
					list_file = response.text.split("\n")
					# print(list_file)
					if len(list_file)==0:
						return {"video": None, "error": "File video playback in this duration does not exist"}
					for file in list_file:
						if not file.endswith(".mp4"):
							continue
						# print(file)
						name_vid = os.path.splitext(os.path.basename(file))[0]
						stts = int(name_vid.split("_")[0])
						ents = int(name_vid.split("_")[1])
						# print(stts)
						if (starttime <= stts and stts < endtime) or (starttime < ents and ents <= endtime): 
							# print(stts)
							r = requests.get(url+f"/{camseri}/{date.fromtimestamp(stts)}/{stts}_{ents}.mp4", headers=headers, allow_redirects=True)
							path_video_5m = f'{path_download}/{stts}_{ents}.mp4'
							if not os.path.exists(path_video_5m):
								return {"video": None, "error": "File video playback in this duration does not exist"}
							open(path_video_5m, 'wb').write(r.content)

							if endtime < ents:
								targetname = f'{path_download}/{stts}_{endtime}.mp4'
								ffmpeg_extract_subclip(path_video_5m, 0, int(endtime-stts), targetname=targetname)
								path_video_5m = targetname
							if starttime > stts:
								targetname = f'{path_download}/{starttime}_{ents}.mp4'
								ffmpeg_extract_subclip(path_video_5m, int(starttime-stts), int(ents-stts), targetname=targetname)
								path_video_5m = targetname

							ftxt.write(f"file '{path_video_5m}'\n")
						elif (stts < starttime < ents) and (stts < endtime < ents):
							r = requests.get(url+f"/{camseri}/{date.fromtimestamp(stts)}/{stts}_{ents}.mp4", headers=headers, allow_redirects=True)
							path_video_5m = f'{path_download}/{stts}_{ents}.mp4'
							if not os.path.exists(path_video_5m):
								return {"video": None, "error": "File video playback in this duration does not exist"}
							open(path_video_5m, 'wb').write(r.content)

							targetname = f'{path_download}/{starttime}_{endtime}.mp4'
							ffmpeg_extract_subclip(path_video_5m, int(starttime-stts), int(endtime-stts), targetname=targetname)
							path_video_5m = targetname

							ftxt.write(f"file '{path_video_5m}'\n")

				ftxt.close()

				subprocess.call(['ffmpeg', '-f', 'concat', '-safe', '0', '-y', '-i', path_info_merged, '-c', 'copy', path_video_merged])
				path_videos.append(path_video_merged)
			return {"video": path_videos}

		else:
			return {"video": None, "error": "Authentication token is None"}

	else:
		path_merged = f'{str(ROOT)}/static/video/video_merged/{job_id}'
		if not os.path.exists(path_merged):
			os.mkdir(path_merged)
		path_download = f'{str(ROOT)}/static/video/video_download/{job_id}'
		if not os.path.exists(path_download):
			os.mkdir(path_download)

		path_videos = []
		for i, starttime in enumerate(start_times):
			endtime = end_times[i]
			camseri = camseris[i]
			# camseri = "99"
			path_video_merged = f'{path_merged}/{starttime}_{endtime}.mp4'
			path_info_merged = f'{os.path.splitext(path_video_merged)[0]}.txt'
			ftxt = open(path_info_merged, 'w')

			list_date = pd.date_range(start=date.fromtimestamp(starttime), end=date.fromtimestamp(endtime))
			for dt in list_date.values:
				dt = str(dt).split("T")[0]
				# path_video_storage = f"{url_access}/{folder_storage}/{camseri}/{dt}".replace("-", "_")
				path_video_storage = f"{url_access}/{folder_storage}/{camseri}/{dt.replace('-', '_')}"
				list_file = os.listdir(path_video_storage)
				if len(list_file)==0:
					return {"video": None, "error": "File video playback in this duration does not exist"}
				# print(list_file)
				# exit()
				# print(list_file)
				for file in list_file:
					if not file.endswith(".mp4"):
						continue
					# print(file)
					name_vid = os.path.splitext(os.path.basename(file))[0]
					stts = int(name_vid.split("_")[1])
					ents = int(name_vid.split("_")[2])
					# print(stts)
					if (starttime <= stts and stts < endtime) or (starttime < ents and ents <= endtime): 
						# print(stts)
						# r = requests.get(url+f"/{camseri}/{date.fromtimestamp(stts)}/{stts}_{ents}.mp4", headers=headers, allow_redirects=True)
						path_video_5m = f'{path_video_storage}/video_{stts}_{ents}.mp4'
						if len(list_file)==0:
							return {"video": None, "error": "File video playback in this duration does not exist"}
						# open(path_video_5m, 'wb').write(r.content)

						if endtime < ents:
							targetname = f'{path_download}/{stts}_{endtime}.mp4'
							ffmpeg_extract_subclip(path_video_5m, 0, int(endtime-stts), targetname=targetname)
							path_video_5m = targetname
						if starttime > stts:
							targetname = f'{path_download}/{starttime}_{ents}.mp4'
							ffmpeg_extract_subclip(path_video_5m, int(starttime-stts), int(ents-stts), targetname=targetname)
							path_video_5m = targetname

						ftxt.write(f"file '{path_video_5m}'\n")
					elif (stts < starttime < ents) and (stts < endtime < ents):
						# r = requests.get(url+f"/{camseri}/{date.fromtimestamp(stts)}/{stts}_{ents}.mp4", headers=headers, allow_redirects=True)
						path_video_5m = f'{path_video_storage}/video_{stts}_{ents}.mp4'
						if len(list_file)==0:
							return {"video": None, "error": "File video playback in this duration does not exist"}
						# open(path_video_5m, 'wb').write(r.content)

						targetname = f'{path_download}/{starttime}_{endtime}.mp4'
						ffmpeg_extract_subclip(path_video_5m, int(starttime-stts), int(endtime-stts), targetname=targetname)
						path_video_5m = targetname

						ftxt.write(f"file '{path_video_5m}'\n")

			ftxt.close()

			subprocess.call(['ffmpeg', '-f', 'concat', '-safe', '0', '-y', '-i', path_info_merged, '-c', 'copy', path_video_merged])
			path_videos.append(path_video_merged)
		return {"video": path_videos}


if __name__=="__main__":
	param = {"start_times": [1716188543], "end_times": [1716188563], "camseris": ["7M09FDDGAJ96B00"], "url_auth": "sad", "url_access": f"{str(ROOT)}/videoTest", "folder_storage": "storage", "job_id": "abcd1234"}
	path_video = get_merge_video_custom(**param)
	print(path_video)