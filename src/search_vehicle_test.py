import paddleclas
import ast
import numpy as np
import time
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

def search_vehicle(data_inputs, color_type_convert):
	model = paddleclas.PaddleClas(model_name="vehicle_attribute", batch_size=16)
	list_image_select = []
	start_time = time.time()
	for data_input in data_inputs:
		result = model.predict(input_data=data_input)
		# result = model.predict(input_data=img)
		for r in result:
			print(r)
			print("---------------")
			for b in r:
				if (np.array(b['output']) == np.array(color_type_convert)).any():
					list_image_select.append(b['filename'])
				# index_result = [i for i, x in enumerate(b['output']) if x]
				# if any(index in color_type for index in index_result):
					# list_image_select.append(b['filename'])
	# print(list_image_select)
	# print(len(list_image_select))
	print("----_Duration: ", time.time() - start_time)
	return list_image_select

if __name__=="__main__":
	colors = [0,1,2,3,4,5,6,7,8,9]
	types = [10,11,12,13,14,15,16,17,18]
	data_input = ["30-05-2023"]
	color_type = colors + types
	color_type_convert = []
	for i in range(19):
		if i in color_type:
			color_type_convert.append(1)
		else:
			color_type_convert.append(-1)
	list_image_select = search_vehicle(data_input, color_type_convert)
	print(list_image_select)
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