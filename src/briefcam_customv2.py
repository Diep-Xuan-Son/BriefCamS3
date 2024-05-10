import os, sys
import cv2
import numpy as np
from pathlib import Path
import json
from PIL import Image
import shutil
import time
from datetime import datetime, date
import skvideo.io as skv

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
PATH_DATA = os.path.join(ROOT,"data_render")
PATH_RESULT = os.path.join(ROOT,"static/assets")
if str(ROOT) not in sys.path:
	sys.path.append(str(ROOT))  # add ROOT to PATH

class BriefCam():
	def __init__(self, n_person=5, name_vid="", path_result="", job_id=None):
		self.name_vid = name_vid
		self.path_result = path_result
		self.job_id = job_id
		if not os.path.exists(self.path_result):
			os.mkdir(self.path_result)

		self.path_data = PATH_DATA
		if not os.path.exists(self.path_data):
			os.mkdir(self.path_data)

		self.path_each_data = os.path.join(self.path_data,job_id)
		if not os.path.exists(self.path_each_data):
			os.mkdir(self.path_each_data)
		else:
			shutil.rmtree(self.path_each_data)
			os.mkdir(self.path_each_data)

		self.path_background_data = self.path_each_data + "_bgr"
		if not os.path.exists(self.path_background_data):
			os.mkdir(self.path_background_data)
		else:
			shutil.rmtree(self.path_background_data)
			os.mkdir(self.path_background_data)

		self.dict_data = {"information": {}, "data":{}}
		self.n_person = n_person
		self.data_convert = None
		self.data_n_person_remain = []
		self.data_check_overlap = None
		self.percent_total_frame = 0.1    # %
		self.bgr_pre = ""
		self.images = []
		self.bgrs = []
		# global percentCompleteBrief
		# percentCompleteBrief = 0.75

	def create_bgr(self, count, image, total_frame):	# b1
		# images = []
		# bgrs = []
		if total_frame>52630:
			scale_save_image = (52630/total_frame)/100
		else:
			scale_save_image = 1/100
		image = cv2.resize(image, (image.shape[1]//4, image.shape[0]//4), interpolation=cv2.INTER_AREA)
		self.images.append(image)
		if (count+1) % int(total_frame*scale_save_image) == 0:
			self.bgrs.append(np.median(self.images, axis = 0))
			self.images.clear()
		if (count+1) % (int(total_frame*self.percent_total_frame)) == 0:
			bgr_pth = os.path.join(self.path_background_data, f"bgr_{count}.jpg")
			bgr_subtract = np.median(self.bgrs, axis = 0)
			bgr_subtract = cv2.resize(bgr_subtract, (image.shape[1]*4, image.shape[0]*4), interpolation=cv2.INTER_AREA)
			cv2.imwrite(bgr_pth, bgr_subtract)
			self.bgrs.clear()
			

	def chooes_bgs(self, current_frame_count, frame_total):
		count_bgr = int(frame_total*self.percent_total_frame)
		# if( int(current_frame_count//2000) <=  int(frame_total//2000) - 1 ):
		if( int(current_frame_count//count_bgr) <=  int(frame_total//count_bgr) - 1 ):
			# count = 2000 + 2000 * int(current_frame_count//2000)
			count = count_bgr + count_bgr * int(current_frame_count//count_bgr) - 1
		else:
			# count = 2000 * int(current_frame_count//2000)
			count = count_bgr * int(current_frame_count//count_bgr) - 1
		path_background = os.path.join(self.path_background_data, f"bgr_{int(count)}.jpg")
		# print(path_background)
		
		if os.path.exists(path_background):
			bgr = cv2.imread(path_background)
			self.bgr_pre = bgr.copy()
		else:
			print("Don't have background image")
			bgr = self.bgr_pre

		return bgr

	def render(self, id, time, cls, bbox, im0):	#b2
		x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
		path_id_each_data = os.path.join(self.path_each_data, str(id))
		if id not in self.dict_data["data"]:
			self.dict_data["data"][id] = []
			if not os.path.exists(path_id_each_data):
				os.mkdir(path_id_each_data)
		id_obj = str(id) + "_" + str(len(self.dict_data["data"][id]))	#id-index of object
		data_obj = [id_obj, time, cls, x1, y1, x2, y2]
		self.dict_data["data"][id].append(data_obj)
		cv2.imwrite(os.path.join(path_id_each_data,id_obj+".jpg"), im0[y1:y2, x1:x2])

	def iou(self, bbox, other_bbox, i):
		a,b,c = other_bbox.shape
		bbox = np.expand_dims(bbox, axis=1)
		bbox = np.broadcast_to(bbox,(a,b,c))
		bboxes = np.concatenate((bbox, other_bbox), axis=2)
		overlaps_x0 = np.nanmax(bboxes[:,:,[0,4]], axis=2)
		overlaps_y0 = np.nanmax(bboxes[:,:,[1,5]], axis=2)
		overlaps_x1 = np.nanmin(bboxes[:,:,[2,6]], axis=2)
		overlaps_y1 = np.nanmin(bboxes[:,:,[3,7]], axis=2)
		check_overlap_x = overlaps_x1 - overlaps_x0
		check_overlap_y = overlaps_y1 - overlaps_y0
		check_overlap = np.all([check_overlap_x>0, check_overlap_y>0], axis=0)

		check_overlap_bbox = np.any(check_overlap, axis=1)
		check_overlap = np.insert(check_overlap, i, check_overlap_bbox, axis=1)

		self.data_check_overlap[check_overlap] += 1

	def convert_data(self, list_num_action, index_sort_num_action, data_n_person):
		if self.data_convert is None:
			self.data_convert = data_n_person
			self.index_sort_num_action_pre = index_sort_num_action
			a = np.argsort([len(d) for d in self.data_convert])
			
		else:
			for i, isort in enumerate(reversed(index_sort_num_action)):
				self.data_convert[self.index_sort_num_action_pre[i]] += data_n_person[isort]

			self.index_sort_num_action_pre = np.argsort([len(d) for d in self.data_convert])

	def plot(self, x1, y1, x2, y2, time, img_background, color):
		img0 = img_background
		xyxy = [x1, y1, x2, y2]
		label = f'{time}'
		self.plot_one_box(xyxy, img0, label=label, color=color , line_thickness=2)
		# img_background = Image.fromarray(img0)
		return img_background

	def plot_one_box(self, x, im, color=None, label=None, line_thickness=3):
		# Plots one bounding box on image 'im' using OpenCV
		assert im.data.contiguous, 'Image not contiguous. Apply np.ascontiguousarray(im) to plot_on_box() input image.'
		tl = line_thickness or round(0.002 * (im.shape[0] + im.shape[1]) / 2) + 1  # line/font thickness
		color = color or [random.randint(0, 255) for _ in range(3)]
		c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
		cv2.rectangle(im, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
		if label:
			tf = max(tl - 1, 1)  # font thickness
			t_size = cv2.getTextSize(label, 0, fontScale=tl / 4, thickness=tf)[0]
			c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
			cv2.rectangle(im, c1, c2, color, -1, cv2.LINE_AA)  # filled
			cv2.putText(im, label, (c1[0], c1[1] - 2), 0, tl / 4, [255,255,255], thickness=tf, lineType=cv2.LINE_AA)
			# cv2.putText(im, label, (c1[0], c1[1] + int((x[3]-x[1])/4)), 0, tl / 3, color, thickness=tf, lineType=cv2.LINE_AA)

	# def brief(self, data, information, q_com, scale_percent, add_percent):	#b3
	def brief(self, data, information, scale_percent, add_percent, path_log, start_time):	#b3
		print(information["fps"])
		count = 0
		list_num_action = []
		data_n_person = []
		list_key = list(data)
		#----------------------------------
		for id in list_key:
			data_n_person.append(data[id])
			list_num_action.append(len(data[id]))
			count += 1
			if count > self.n_person-1:
				# print(list_num_action)
				index_sort_num_action = np.argsort(list_num_action)
				# print(index_sort_num_action)
				self.convert_data(list_num_action, index_sort_num_action, data_n_person)
				# exit()
				count = 0
				list_num_action = []
				data_n_person = []
		if count > 0:
			index_sort_num_action = np.argsort(list_num_action)
			for i, isort in enumerate(reversed(index_sort_num_action)):
				self.data_convert[self.index_sort_num_action_pre[i]] += data_n_person[isort]
		# print(len(self.data_convert))
		max_tube = max(len(x) for x in self.data_convert)
		# print(max_tube)
		for j in range(len(self.data_convert)):
			self.data_convert[j] += [[np.nan]*3 + [0]*4]*(max_tube-len(self.data_convert[j]))
		self.data_convert = np.array(self.data_convert, dtype=object).transpose(1,0,2)
		# print(self.data_convert.shape)
		# exit()
		#-----------------------------------------------

		self.data_check_overlap = np.zeros((self.data_convert.shape[0], self.data_convert.shape[1]), dtype=int)
		# print("--------data_check_overlap: ", self.data_check_overlap.shape)
		for i in range(1, self.n_person):
			bbox = self.data_convert[:,i,3:]
			other_bbox = np.delete(self.data_convert[:,:,3:], i, axis=1)
			self.iou(bbox, other_bbox, i)

		self.data_convert = self.data_convert.reshape(-1, 7)
		# print(self.data_convert.shape)
		self.data_check_overlap = self.data_check_overlap.reshape(-1)
		# print(self.data_check_overlap.shape)
		#create image brief
		out = cv2.VideoWriter(os.path.join(self.path_result,f'{self.name_vid}_brief.mp4'),cv2.VideoWriter_fourcc(*'mp4v'), information["fps"], (information["width"], information["height"]))
		# out = skv.FFmpegWriter(os.path.join(self.path_result,f'{self.name_vid}_brief.mp4'), \
		# 	inputdict={'-r': str(information["fps"]), '-s': f'{information["width"]}x{information["height"]}'}, \
		# 	outputdict={'-r': str(information["fps"]), '-vcodec': 'libx264'})
		color = [np.random.randint(0, 255) for _ in range(3)]
		# bgr = cv2.imread(os.path.join(self.path_background_data, "bgr_0.jpg"))
		ren_time_pre = self.data_convert[0][1]

		num_data = len(self.data_convert)
		# global percentCompleteBrief
		for i, ren in enumerate(self.data_convert):
			# if not q_com.empty():
			# 	q_com.get()
			# q_com.put(add_percent + scale_percent*(0.75 + (i+1)*0.25/num_data))
			percentComplete = (add_percent + scale_percent*(0.70 + (i+1)*0.25/num_data))*100
			with open(os.path.join(path_log,f'{self.job_id}/percent.txt'), 'w') as f:
				f.write(f"{percentComplete:.2f}")
			# percentCompleteBrief = 0.75 + (i+1)*0.25/len(self.data_convert)

			if i%self.n_person == 0:
				if np.isnan(ren[2]):
					ren[1] = ren_time_pre
				current_frame_count = int(ren[1]*information["fps"])
				bgr = self.chooes_bgs(current_frame_count, information["total_frame"])

			if np.isnan(ren[2]):
				if (i+1)%self.n_person == 0:
					out.write(bgr)
					# bgr = cv2.cvtColor(bgr, cv2.COLOR_RGB2BGR)
					# out.writeFrame(bgr)
				continue

			minute = 0
			hour = 0
			bgr = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

			# ren[1] = ren[1] + start_time
			# if(ren[1] >= 60):
			# 	minute = ren[1]//60
			# 	if minute >= 60:
			# 		hour = minute//60
			# 		minute = minute - 60*hour
			# 	ren[1] = ren[1] - 60*minute - 3600*hour
			# time = '{hour}:{minute}:{second:.2f}'.format(hour = int(hour), minute = int(minute), second = ren[1])
			time = datetime.fromtimestamp(start_time + ren[1])
			time = str(datetime.strftime(time, "%m/%d %H:%M:%S"))
			id = ren[0].split("_")[0]
			path_id_each_data = os.path.join(self.path_each_data, id)
			img_render = Image.open(os.path.join(path_id_each_data, ren[0] + ".jpg"))
			if self.data_check_overlap[i] > 0:
				img_render.putalpha(80)
				bgr.paste(img_render, (int(ren[3]), int(ren[4])), img_render)
			else:
				bgr.paste(img_render, (int(ren[3]), int(ren[4])))
			bgr = cv2.cvtColor(np.asarray(bgr), cv2.COLOR_RGB2BGR)
			# cv2.rectangle(bgr, (ren[3], ren[4]), (ren[5], ren[6]), color, 2, cv2.LINE_AA)  # filled
			bgr = self.plot(ren[3], ren[4], ren[5], ren[6], time, bgr, color=color)

			if (i+1)%self.n_person == 0:
				out.write(bgr)
				# bgr = cv2.cvtColor(bgr, cv2.COLOR_RGB2BGR)
				# out.writeFrame(bgr)
			ren_time_pre = ren[1]

		out.release()
		# out.close()
		if os.path.exists(self.path_each_data):
			shutil.rmtree(self.path_each_data)
		if os.path.exists(self.path_background_data):
			shutil.rmtree(self.path_background_data)
		print("--------count: ", count)
		print("--------output: ", os.path.join(self.path_result,f'{self.name_vid}_brief.mp4'))
		print("--------data_n_person_remain:", len(self.data_n_person_remain))
		print("Done!!!!!!!!!!!")

# def check_complete_brief():
# 	global percentCompleteBrief
# 	return percentCompleteBrief

if __name__=="__main__":
	n_person = 3
	BC = BriefCam(n_person, "video10")
	f = open(BC.path_each_data+".json")
	BC.dict_data = json.load(f)
	# print(BC.dict_data)
	information = BC.dict_data['information']
	if information['num_person'] > n_person:
		BC.n_person = n_person
	data = BC.dict_data['data']
	BC.brief(data, information, 1, 0, os.path.join(ROOT,"static/log"))
