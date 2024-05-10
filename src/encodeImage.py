import os
import ffmpeg
import shutil

input_path = "./image_vehicle"
output_image = "./image_vehicle"
output_label = "./label_full"
for image in sorted(os.listdir(input_path)):
	print(image)
	if(image.endswith(('.png', '.jpg'))):
		stream = ffmpeg.input(os.path.join(input_path, image))
		# stream = ffmpeg.hflip(stream)
		if len(image.split('.')[0]) == 2:
			name_image = image.split('.')[0]
		else:
			name_image = ".".join(image.split('.')[0:-1])
		stream = ffmpeg.output(stream, os.path.join(output_image, name_image + '.jpg'))
		ffmpeg.run(stream, overwrite_output=True)
	#elif(image.endswith('.txt')):
		#shutil.copy(os.path.join(input_path, image), os.path.join(output_label, image))
