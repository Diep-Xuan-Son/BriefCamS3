
import argparse

import os
# limit the number of cpus used by high performance libraries
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import numpy as np
from pathlib import Path
import shutil

import pandas as pd
from collections import Counter
from collections import deque

import warnings
warnings.filterwarnings('ignore')

import torch
import torch.backends.cudnn as cudnn

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # yolov5 strongsort root directory
WEIGHTS = ROOT / 'weights'

if str(ROOT) not in sys.path:
	sys.path.append(str(ROOT))  # add ROOT to PATH
if str(ROOT / 'yolov5') not in sys.path:
	sys.path.append(str(ROOT / 'yolov5'))  # add yolov5 ROOT to PATH
if str(ROOT / 'strong_sort') not in sys.path:
	sys.path.append(str(ROOT / 'strong_sort'))  # add strong_sort ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

import logging
from yolov5.models.common import DetectMultiBackend
try:
	from yolov5.utils.dataloaders import VID_FORMATS, LoadImages, LoadStreams
except:
	import sys
	sys.path.append('yolov5/utils')
	from dataloaders import VID_FORMATS, LoadImages, LoadStreams
from yolov5.utils.general import (LOGGER, check_img_size, non_max_suppression, scale_coords, check_requirements, cv2,
								  check_imshow, xyxy2xywh, increment_path, strip_optimizer, colorstr, print_args, check_file)
from yolov5.utils.torch_utils import select_device, time_sync
from yolov5.utils.plots import Annotator, colors, save_one_box
from strong_sort.utils.parser import get_config
from strong_sort.strong_sort import StrongSORT

from briefcam_customv2 import BriefCam, PATH_DATA
import json
from datetime import datetime, date
from merge_video import get_token
import requests
# remove duplicated stream handler to avoid duplicated logging
#logging.getLogger().removeHandler(logging.getLogger().handlers[0])

PATH_LOG_ABSOLUTE = os.path.join(ROOT,"static/log")
PATH_RESULT = "static/video/video_brief"
PATH_RESULT_ABSOLUTE = os.path.join(ROOT,PATH_RESULT)
PATH_INPUT_DOWNLOAD = "static/video/video_download"
PATH_INPUT_MERGE = "static/video/video_merged"

@torch.no_grad()
def run(
		source='0',
		yolo_weights=WEIGHTS / 'yolov5m.pt',  # model.pt path(s),
		strong_sort_weights=WEIGHTS / 'osnet_x0_25_msmt17.pt',  # model.pt path,
		config_strongsort=ROOT / 'strong_sort/configs/strong_sort.yaml',
		imgsz=(640, 640),  # inference size (height, width)
		conf_thres=0.25,  # confidence threshold
		iou_thres=0.45,  # NMS IOU threshold
		max_det=1000,  # maximum detections per image
		device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
		show_vid=False,  # show results
		save_txt=False,  # save results to *.txt
		save_conf=False,  # save confidences in --save-txt labels
		save_crop=False,  # save cropped prediction boxes
		save_vid=False,  # save confidences in --save-txt labels
		nosave=False,  # do not save images/videos
		classes=None,  # filter by class: --class 0, or --class 0 2 3
		agnostic_nms=False,  # class-agnostic NMS
		augment=False,  # augmented inference
		visualize=False,  # visualize features
		update=False,  # update all models
		project=ROOT / 'runs/track',  # save results to project/name
		name='exp',  # save results to project/name
		exist_ok=False,  # existing project/name ok, do not increment
		line_thickness=2,  # bounding box thickness (pixels)
		hide_labels=False,  # hide labels
		hide_conf=False,  # hide confidences
		hide_class=False,  # hide IDs
		half=False,  # use FP16 half-precision inference
		dnn=False,  # use OpenCV DNN for ONNX inference
		count=False,  # get counts of every obhects
		draw=False,  # draw object trajectory lines
		# q_com='',
		ipaddress = '',
		scale_percent = 1,
		add_percent = 0,
		start_time = 0,
		fps_result = 15,
		job_id = None
):
	# global percentComplete
	# percentComplete = 0
	source = str(source)
	save_img = not nosave and not source.endswith('.txt')  # save inference images
	is_file = Path(source).suffix[1:] in (VID_FORMATS)
	is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
	webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
	if is_url and is_file:
		source = check_file(source)  # download

	name_vid = os.path.splitext(os.path.basename(source))[0]
	path_vid = os.path.dirname(source)
	BC = BriefCam(name_vid=name_vid, path_result=os.path.join(PATH_RESULT_ABSOLUTE, job_id), job_id=job_id)

	# Directories
	if not isinstance(yolo_weights, list):  # single yolo model
		exp_name = yolo_weights.stem
	elif type(yolo_weights) is list and len(yolo_weights) == 1:  # single models after --yolo_weights
		exp_name = Path(yolo_weights[0]).stem
	else:  # multiple models after --yolo_weights
		exp_name = 'ensemble'
	exp_name = name if name else exp_name + "_" + strong_sort_weights.stem
	save_dir = increment_path(Path(project) / exp_name, exist_ok=exist_ok)  # increment run
	# (save_dir / 'tracks' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

	# Load model
	device = select_device(device)
	model = DetectMultiBackend(yolo_weights, device=device, dnn=dnn, data=None, fp16=half)
	stride, names, pt = model.stride, model.names, model.pt
	imgsz = check_img_size(imgsz, s=stride)  # check image size
	trajectory = {}


	# Dataloader
	if webcam:
		show_vid = check_imshow()
		cudnn.benchmark = True  # set True to speed up constant image size inference
		dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt)
		nr_sources = len(dataset)
	else:
		dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt)
		nr_sources = 1
	vid_path, vid_writer, txt_path = [None] * nr_sources, [None] * nr_sources, [None] * nr_sources

	# initialize StrongSORT
	cfg = get_config()
	cfg.merge_from_file(config_strongsort)

	# Create as many strong sort instances as there are video sources
	strongsort_list = []
	for i in range(nr_sources):
		strongsort_list.append(
			StrongSORT(
				strong_sort_weights,
				device,
				max_dist=cfg.STRONGSORT.MAX_DIST,
				max_iou_distance=cfg.STRONGSORT.MAX_IOU_DISTANCE,
				max_age=cfg.STRONGSORT.MAX_AGE,
				n_init=cfg.STRONGSORT.N_INIT,
				nn_budget=cfg.STRONGSORT.NN_BUDGET,
				mc_lambda=cfg.STRONGSORT.MC_LAMBDA,
				ema_alpha=cfg.STRONGSORT.EMA_ALPHA,

			)
		)
	outputs = [None] * nr_sources

	# Run tracking
	model.warmup(imgsz=(1 if pt else nr_sources, 3, *imgsz))  # warmup
	dt, seen = [0.0, 0.0, 0.0, 0.0], 0
	curr_frames, prev_frames = [None] * nr_sources, [None] * nr_sources
	#-------------------------
	v = cv2.VideoCapture(source)
	fpsss = v.get(cv2.CAP_PROP_FPS)
	video_width = int(v.get(3))
	video_height = int(v.get(4))
	total_frame = int(v.get(7))
	num_person = 5
	fps_scale = round(fpsss/fps_result) if fpsss > fps_result else 1

	BC.dict_data["information"]["total_frame"] = total_frame
	BC.dict_data["information"]["fps"] = round(fpsss/fps_scale)
	BC.dict_data["information"]["width"] = video_width
	BC.dict_data["information"]["height"] = video_height
	#--------------------------
	for frame_idx, (path, im, im0s, vid_cap, s) in enumerate(dataset):
		# if not q_com.empty():
		# 	q_com.get()
		# q_com.put(add_percent + (frame_idx+1)*0.75*scale_percent/total_frame)
		percentComplete = (add_percent + (frame_idx+1)*0.70*scale_percent/total_frame)*100
		with open(os.path.join(PATH_LOG_ABSOLUTE,f'{job_id}/percent.txt'), 'w') as f:
			f.write(f"{percentComplete:.2f}")
		BC.create_bgr(frame_idx, im0s, total_frame)
		if frame_idx%fps_scale != 0:
			continue

		t1 = time_sync()
		im = torch.from_numpy(im).to(device)
		im = im.half() if half else im.float()  # uint8 to fp16/32
		im /= 255.0  # 0 - 255 to 0.0 - 1.0

		if len(im.shape) == 3:
			im = im[None]  # expand for batch dim
		t2 = time_sync()
		dt[0] += t2 - t1

		# Inference
		visualize = increment_path(save_dir / Path(path[0]).stem, mkdir=True) if visualize else False
		pred = model(im, augment=augment, visualize=visualize)
		t3 = time_sync()
		dt[1] += t3 - t2

		# Apply NMS
		pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)
		dt[2] += time_sync() - t3

		# Process detections
		for i, det in enumerate(pred):  # detections per image
			seen += 1
			if webcam:  # nr_sources >= 1
				p, im0, _ = path[i], im0s[i].copy(), dataset.count
				p = Path(p)  # to Path
				s += f'{i}: '
				txt_file_name = p.name
				save_path = str(save_dir / p.name)  # im.jpg, vid.mp4, ...
			else:
				p, im0, _ = path, im0s.copy(), getattr(dataset, 'frame', 0)
				p = Path(p)  # to Path
				# video file
				if source.endswith(VID_FORMATS):
					txt_file_name = p.stem
					save_path = str(save_dir / p.name)  # im.jpg, vid.mp4, ...
				# folder with imgs
				else:
					txt_file_name = p.parent.name  # get folder name containing current img
					save_path = str(save_dir / p.parent.name)  # im.jpg, vid.mp4, ...
			curr_frames[i] = im0

			txt_path = str(save_dir / 'tracks' / txt_file_name)  # im.txt
			s += '%gx%g ' % im.shape[2:]  # print string
			imc = im0.copy() if save_crop else im0  # for save_crop

			annotator = Annotator(im0, line_width=2, pil=not ascii)
			if cfg.STRONGSORT.ECC:  # camera motion compensation
				strongsort_list[i].tracker.camera_update(prev_frames[i], curr_frames[i])

			if det is not None and len(det):
				# Rescale boxes from img_size to im0 size
				det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

				# Print results
				for c in det[:, -1].unique():
					n = (det[:, -1] == c).sum()  # detections per class
					s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

				xywhs = xyxy2xywh(det[:, 0:4])
				confs = det[:, 4]
				clss = det[:, 5]

				# pass detections to strongsort
				t4 = time_sync()
				outputs[i] = strongsort_list[i].update(xywhs.cpu(), confs.cpu(), clss.cpu(), im0)
				t5 = time_sync()
				dt[3] += t5 - t4

				# draw boxes for visualization
				if len(outputs[i]) > 0:
					#---------------------------
					if len(outputs[i]) > num_person:
						num_person = len(outputs[i])
					#----------------------------
					for j, (output, conf) in enumerate(zip(outputs[i], confs)):
	
						bboxes = output[0:4]
						id = output[4]
						cls = output[5]
						bbox_left, bbox_top, bbox_right, bbox_bottom = bboxes
						#-----------------------------------------
						BC.render(int(id), frame_idx/fpsss, int(cls), bboxes, imc)
						#-----------------------------------------
						if draw:
							# object trajectory
							center = ((int(bboxes[0]) + int(bboxes[2])) // 2,(int(bboxes[1]) + int(bboxes[3])) // 2)
							if id not in trajectory:
								trajectory[id] = []
							trajectory[id].append(center)
							for i1 in range(1,len(trajectory[id])):
								if trajectory[id][i1-1] is None or trajectory[id][i1] is None:
									continue
								# thickness = int(np.sqrt(1000/float(i1+10))*0.3)
								thickness = 2
								try:
									cv2.line(im0, trajectory[id][i1 - 1], trajectory[id][i1], (0, 0, 255), thickness)
								except:
									pass


						if save_txt:
							# to MOT format
							bbox_left = output[0]
							bbox_top = output[1]
							bbox_w = output[2] - output[0]
							bbox_h = output[3] - output[1]
							# Write MOT compliant results to file
							with open(txt_path+'.txt', 'a') as f:
								f.write(('%g ' * 11 + '\n') % (frame_idx + 1, cls, id, bbox_left,  # MOT format
															   bbox_top, bbox_w, bbox_h, -1, -1, -1, -1))

						if save_vid or save_crop or show_vid:  # Add bbox to image
							c = int(cls)  # integer class
							id = int(id)  # integer id
							label = None if hide_labels else (f'{id} {names[c]}' if hide_conf else \
								(f'{id} {conf:.2f}' if hide_class else f'{id} {names[c]} {conf:.2f}'))
							annotator.box_label(bboxes, label, color=colors(c, True))


							if save_crop:
								txt_file_name = txt_file_name if (isinstance(path, list) and len(path) > 1) else ''
								save_one_box(bboxes, imc, file=save_dir / 'crops' / txt_file_name / names[c] / f'{id}' / f'{p.stem}.jpg', BGR=True)

				LOGGER.info(f'{s}Done. YOLO:({t3 - t2:.3f}s), StrongSORT:({t5 - t4:.3f}s)')

			else:
				strongsort_list[i].increment_ages()
				LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1] * 1E3:.1f}ms")


			if count:
				itemDict={}
				## NOTE: this works only if save-txt is true
				try:
					df = pd.read_csv(txt_path +'.txt' , header=None, delim_whitespace=True)
					df = df.iloc[:,0:3]
					df.columns=["frameid" ,"class","trackid"]
					df = df[['class','trackid']]
					df = (df.groupby('trackid')['class']
							  .apply(list)
							  .apply(lambda x:sorted(x))
							 ).reset_index()

					df.colums = ["trackid","class"]
					df['class']=df['class'].apply(lambda x: Counter(x).most_common(1)[0][0])
					vc = df['class'].value_counts()
					vc = dict(vc)

					vc2 = {}
					for key, val in enumerate(names):
						vc2[key] = val
					itemDict = dict((vc2[key], value) for (key, value) in vc.items())
					itemDict  = dict(sorted(itemDict.items(), key=lambda item: item[0]))
					# print(itemDict)

				except:
					pass

				if save_txt:
					## overlay
					display = im0.copy()
					h, w = im0.shape[0], im0.shape[1]
					x1 = 10
					y1 = 10
					x2 = 10
					y2 = 70

					txt_size = cv2.getTextSize(str(itemDict), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
					cv2.rectangle(im0, (x1, y1 + 1), (txt_size[0] * 2, y2),(0, 0, 0),-1)
					cv2.putText(im0, '{}'.format(itemDict), (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX,0.7, (210, 210, 210), 2)
					cv2.addWeighted(im0, 0.7, display, 1 - 0.7, 0, im0)


			# #current frame // tesing
			# cv2.imwrite('testing.jpg',im0)


			if show_vid:
				cv2.imshow(str(p), im0)
				if cv2.waitKey(1) == ord('q'):  # q to quit
					break

			# Save results (image with detections)
			if save_vid:
				if vid_path[i] != save_path:  # new video
					vid_path[i] = save_path
					if isinstance(vid_writer[i], cv2.VideoWriter):
						vid_writer[i].release()  # release previous video writer
					if vid_cap:  # video
						fps = vid_cap.get(cv2.CAP_PROP_FPS)
						w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
						h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
					else:  # stream
						fps, w, h = 30, im0.shape[1], im0.shape[0]
					save_path = str(Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
					vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
				vid_writer[i].write(im0)

			prev_frames[i] = curr_frames[i]

	#----------------------------------
	print(len(os.listdir(BC.path_each_data)))
	if num_person > len(os.listdir(BC.path_each_data)):
		num_person = len(os.listdir(BC.path_each_data))
	BC.n_person = num_person
	BC.dict_data["information"]["num_person"] = BC.n_person

	# with open(BC.path_each_data+".json", "w") as outfile:
	# 	json.dump(BC.dict_data, outfile)
	print("---------n_person: ", BC.n_person)
	# BC.brief(BC.dict_data['data'], BC.dict_data['information'], q_com, scale_percent, add_percent)
	BC.brief(BC.dict_data['data'], BC.dict_data['information'], scale_percent, add_percent, PATH_LOG_ABSOLUTE, start_time)
	#----------------------------------
	# Print results
	t = tuple(x / seen * 1E3 for x in dt)  # speeds per image
	LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS, %.1fms strong sort update per image at shape {(1, 3, *imgsz)}' % t)
	if save_txt or save_vid:
		s = f"\n{len(list(save_dir.glob('tracks/*.txt')))} tracks saved to {save_dir / 'tracks'}" if save_txt else ''
		LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
	if update:
		strip_optimizer(yolo_weights)  # update model (to fix SourceChangeWarning)
	# return os.path.join(f"http://{ipaddress}:3456/" + PATH_RESULT,f'{BC.name_vid}_brief.mp4')
	return os.path.join(PATH_RESULT_ABSOLUTE,f'{job_id}/{BC.name_vid}_brief.mp4')


def parse_opt():
	parser = argparse.ArgumentParser()
	parser.add_argument('--yolo-weights', nargs='+', type=str, default=WEIGHTS / 'yolov5n.pt', help='model.pt path(s)')
	parser.add_argument('--strong-sort-weights', type=str, default=WEIGHTS / 'osnet_x0_25_msmt17.pt')
	parser.add_argument('--config-strongsort', type=str, default='strong_sort/configs/strong_sort.yaml')
	parser.add_argument('--source', type=str, default='./datasets/video4.mp4', help='file/dir/URL/glob, 0 for webcam')  
	parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='inference size h,w')
	parser.add_argument('--conf-thres', type=float, default=0.6, help='confidence threshold')
	parser.add_argument('--iou-thres', type=float, default=0.25, help='NMS IoU threshold')
	parser.add_argument('--max-det', type=int, default=1000, help='maximum detections per image')
	parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
	parser.add_argument('--show-vid', action='store_true', help='display tracking video results')
	parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
	parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
	parser.add_argument('--save-crop', action='store_true', help='save cropped prediction boxes')
	parser.add_argument('--save-vid', action='store_true', help='save video tracking results')
	parser.add_argument('--nosave', default=True, action='store_true', help='do not save images/videos')
	parser.add_argument('--count', action='store_true', help='display all MOT counts results on screen')
	parser.add_argument('--draw', action='store_true', help='display object trajectory lines')
	# class 0 is person, 1 is bycicle, 2 is car... 79 is oven
	parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --classes 0, or --classes 0 2 3')
	parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
	parser.add_argument('--augment', action='store_true', help='augmented inference')
	parser.add_argument('--visualize', action='store_true', help='visualize features')
	parser.add_argument('--update', action='store_true', help='update all models')
	parser.add_argument('--project', default=ROOT / 'runs/track', help='save results to project/name')
	parser.add_argument('--name', default='exp', help='save results to project/name')
	parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
	parser.add_argument('--line-thickness', default=2, type=int, help='bounding box thickness (pixels)')
	parser.add_argument('--hide-labels', default=False, action='store_true', help='hide labels')
	parser.add_argument('--hide-conf', default=False, action='store_true', help='hide confidences')
	parser.add_argument('--hide-class', default=False, action='store_true', help='hide IDs')
	parser.add_argument('--half', action='store_true', help='use FP16 half-precision inference')
	parser.add_argument('--dnn', action='store_true', help='use OpenCV DNN for ONNX inference')
	opt = parser.parse_args()
	opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
	print_args(vars(opt))
	return opt


# def main(inputts, classs, weight, q_com, q_output):
def track_briefcam(inputts, objectt, type_vehicle, start_times, camseris, ipaddress, fps_result, job_id, url_auth, url_access, folder_summary):
	# check_requirements(requirements=ROOT / 'requirements.txt', exclude=('tensorboard', 'thop'))
	if objectt[0]==0:
		classs = [0]
		weight = WEIGHTS / "crowdhuman_yolov5m.pt"
	elif objectt[0]==1:
		classs = type_vehicle
		weight = WEIGHTS / "vhc_test.pt"
	opt = parse_opt()
	opt.yolo_weights = weight
	opt.classes = classs
	opt.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
	# opt.q_com = q_com
	opt.ipaddress = ipaddress
	opt.fps_result = fps_result
	opt.job_id = job_id
	print(opt)

	opt.scale_percent = 1/len(inputts)
	outputt = []
	for i, inputt in enumerate(inputts):
		opt.source = inputt
		opt.add_percent = i*1/len(inputts)
		opt.start_time = start_times[i]
		outputt.append(run(**vars(opt)))
	# return path_output
	# q_output.put(outputt)
	if url_access.startswith(("http","https")):
		#because of limited time in token, need to get token again after finished briefcam
		auth_token, subject_token = get_token(url_auth)
		headers = {'X-Auth-Token': subject_token}
		URL_VIDEOBRIEF_STORAGE = f"{url_access}/{auth_token}/{folder_summary}"
		percentComplete = 95
		with open(os.path.join(PATH_LOG_ABSOLUTE,f'{job_id}/result.txt'), 'w') as f:
			for i, output in enumerate(outputt):
				# url = URL_VIDEOBRIEF_STORAGE + f"/{camseris[i]}/{date.fromtimestamp(start_times[i])}/{os.path.basename(inputts[i])}"
				url = URL_VIDEOBRIEF_STORAGE + f"/{camseris[i]}/{date.fromtimestamp(start_times[i])}/{os.path.basename(inputts[i])}"
				payload = open(output, 'rb')
				response = requests.request("PUT", url, headers=headers, data=payload)
				# if response.ok:
				f.write("%s\n" % url)

				percentComplete = (0.95 + (i+1)*0.05)*100
		print("-------response: ", response.ok)
		if response.ok:
			delete_output(job_id)
	else:
		URL_VIDEOBRIEF_STORAGE = f"{url_access}/{folder_summary}"
		if not os.path.exists(URL_VIDEOBRIEF_STORAGE):
			os.makedirs(URL_VIDEOBRIEF_STORAGE, exist_ok=True)
		percentComplete = 95
		with open(os.path.join(PATH_LOG_ABSOLUTE,f'{job_id}/result.txt'), 'w') as f:
			for i, output in enumerate(outputt):
				url = URL_VIDEOBRIEF_STORAGE + f"/{camseris[i]}/{date.fromtimestamp(start_times[i])}/{os.path.basename(inputts[i])}"
				if not os.path.exists(os.path.dirname(url)):
					os.makedirs(os.path.dirname(url), exist_ok=True)
				shutil.copy(output, url)
				f.write("%s\n" % url)
				percentComplete = (0.95 + (i+1)*0.05)*100
		delete_output(job_id)

	with open(os.path.join(PATH_LOG_ABSOLUTE,f'{job_id}/percent.txt'), 'w') as f:
		f.write(f"{percentComplete:.2f}")


def delete_log(job_id):
	try:
		shutil.rmtree(os.path.join(PATH_LOG_ABSOLUTE,job_id))
	except OSError:
		os.remove(os.path.join(PATH_LOG_ABSOLUTE,job_id))

	try:
		shutil.rmtree(os.path.join(PATH_DATA,job_id))
		shutil.rmtree(os.path.join(PATH_DATA,job_id)+"_bgr")
	except OSError:
		os.remove(os.path.join(PATH_DATA,job_id))

def delete_output(job_id):
	# for resultName in os.listdir(ROOT/PATH_RESULT):
	# 	resultPath = os.path.join(ROOT/PATH_RESULT, resultName)
	try:
		if os.path.exists(ROOT/PATH_RESULT/job_id):
			shutil.rmtree(ROOT/PATH_RESULT/job_id)
	except OSError:
		os.remove(ROOT/PATH_RESULT/job_id)

	# for resultName in os.listdir(ROOT/PATH_INPUT_MERGE):
	# 	resultPath = os.path.join(ROOT/PATH_INPUT_MERGE, resultName)
	try:
		if os.path.exists(ROOT/PATH_INPUT_MERGE/job_id):
			shutil.rmtree(ROOT/PATH_INPUT_MERGE/job_id)
	except OSError:
		os.remove(ROOT/PATH_INPUT_MERGE/job_id)

	# for resultName in os.listdir(ROOT/PATH_INPUT_DOWNLOAD):
	# 	resultPath = os.path.join(ROOT/PATH_INPUT_DOWNLOAD, resultName)
	try:
		if os.path.exists(ROOT/PATH_INPUT_DOWNLOAD/job_id):
			shutil.rmtree(ROOT/PATH_INPUT_DOWNLOAD/job_id)
	except OSError:
		os.remove(ROOT/PATH_INPUT_DOWNLOAD/job_id)


if __name__ == "__main__":
	# opt = parse_opt()
	inputts = ["videoTest/video4.mp4", "videoTest/video5.mp4", "videoTest/video6.mp4"]
	inputts = [os.path.join(ROOT, inputt) for inputt in inputts] 
	objectt  = 0
	if objectt==0:
		classs = [0]
		weight = WEIGHTS / "crowdhuman_yolov5m.pt"
	elif objectt==1:
		classs = [0,1,2]
		weight = WEIGHTS / "vhc_test.pt"
	outputs = []
	for inputt in inputts:
		data_input = [inputt, classs, weight]	
		outputs.append(main(*data_input))
