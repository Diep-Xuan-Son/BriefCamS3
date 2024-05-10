import requests
from tqdm import tqdm
import time
import os
import cv2
import json

# url = "http://192.168.6.86:8421/api/registerFace"

# for i in tqdm(range(100000), desc="creating data face"):
# 	params = {"code": f"{101099008839 + i}", "name":"Son", "birthday":"29/04/1999"}
# 	files = [("images", open("data_test/thao.jpg", "rb"))]
# 	resp = requests.post(url=url, params=params, files=files)
# 	# print(resp.json())


# for i, img in enumerate(tqdm(os.listdir("./data_test/face_hcm"), desc="creating data face")):
# 	# params = {"code": f"{101099008839 + i}", "name":f"{img}", "birthday":"29/04/1999"}
# 	img_path = os.path.join("./data_test/face_hcm", img)
# 	# files = [("images", open(img_path, "rb"))]
# 	# resp = requests.post(url=url, params=params, files=files)
# 	if (img=="face_22520720.jpg"):
# 		image = cv2.imread(img_path)
# 		cv2.imshow("dsfasdf", image)
# 		cv2.waitKey(0)
# 		exit()


url = "http://192.168.6.142:4444/api/searchUser"
files = [("image", open("src/testing.jpg", "rb"))]
payload = {}
# payload = {
# 	"code": "23414",
# 	"name": "tabad",
# 	"birthday": "3243423"
# 	}
resp = requests.post(url=url, files=files, data=payload)
print(resp.json())
