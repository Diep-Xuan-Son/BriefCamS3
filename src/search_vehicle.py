import paddleclas
import ast
import numpy as np
import torch
import cv2

# model = paddleclas.PaddleClas(model_name="vehicle_attribute", batch_size=8)
# # print(model.__dict__)
# # print(model.predictor.__dict__)
# result = model.predict(input_data="image_vehicle")
# # a = next(result)[1]
# # print(a)
# # b = ast.literal_eval(a['attributes'])
# # print(b)
# for r in result:
#     print(r)
# BATCH_SIZE = 8

def search_vehicle(data_input):
	attribute = {0: "yellow", 1: "orange", 2: "green", 3: "grey", 4: "red", 5: "blue",\
				6: "white", 7: "gold", 8: "brown", 9: "black", 10: "sedan", 11: "suv",\
				12: "van", 13: "hatchback", 14: "mpv", 15: "pickup", 16: "bus", 17: "truck",\
				18: "estate"}
	img = cv2.imread(data_input)
	img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
	result = model_vehicle_det(img)
	print(result.xyxy)
	if len(result.xyxy[0])==0:
		img_crop = img
	else:
	# start_point = [int(x) for x in result.xyxy[0][0].tolist()[0:2]]
	# end_point = [int(x) for x in result.xyxy[0][0].tolist()[2:4]]
		xyxy = [int(x) for x in result.xyxy[0][0].tolist()[0:4]]
		img_crop = img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]

	model = paddleclas.PaddleClas(model_name="vehicle_attribute", batch_size=16)
	result = model.predict(input_data=img_crop)
	colors = []
	types = []
	for r in result:
		# print(r[0]['output'])
		index_result = [i for i, x in enumerate(r[0]['output']) if x]
		for index in index_result:
			if index < 10:
				colors.append(attribute[index])
			else:
				types.append(attribute[index])

		# for b in r:
		# 	if (np.array(b['output']) == np.array(color_type_convert)).any():
		# 		list_image_select.append(b['filename'])
			# index_result = [i for i, x in enumerate(b['output']) if x]
			# if any(index in color_type for index in index_result):
			# 	list_image_select.append(b['filename'])
	return colors, types

model_vehicle_det = torch.hub.load('ultralytics/yolov5', 'custom', path="weights/vehicle_continuetrain_d3m3y2023.pt", \
									force_reload=True, device='cpu')

if __name__=="__main__":
	colors = [0,1,2,3,4,5,6,7,8,9]
	types = [10,11,12,13,14,15,16,17,18]
	data_input = "image_vehicle/AZ1mBnse.jpg"
	# img = cv2.imread(data_input)
	# img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
	# result = model_vehicle(img)
	# start_point = [int(x) for x in result.xyxy[0][0].tolist()[0:2]]
	# end_point = [int(x) for x in result.xyxy[0][0].tolist()[2:4]]
	# # cv2.rectangle(img, start_point, end_point, (0,255,0), 2)
	# img_crop = img[start_point[1]:end_point[1], start_point[0]:end_point[0]]
	# cv2.imshow("dvdvsv", img_crop)
	# cv2.waitKey(0)
	color_type = colors + types
	colors, types = search_vehicle(data_input)
	print(colors, types)
# "vàng"
# "cam"
# "xanh lá cây"
# "xám"
# "đỏ"
# "xanh nước biển"
# "trắng"
# "vàng kim"
# "nâu"
# "đen"

# "sedan"
# "suv"
# "van"
# "hatchback"
# "mpv"
# "pickup"
# "bus"
# "truck"
# "estate"
