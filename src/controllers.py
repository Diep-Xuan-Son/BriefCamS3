from app_brief_s3 import *
from track_briefcam_customv2 import track_briefcam, delete_output, PATH_LOG_ABSOLUTE, delete_log
# from search_vehicle import search_vehicle
from merge_video import get_merge_video, get_merge_video_custom
# import uuid

upload_parser = api.parser()
upload_parser.add_argument("object", action='append', type=int, required=True)	# 0: person, 1: vehicle
upload_parser.add_argument("type_vehicle", action='append', type=int)	# [sedan, suv, van, hatchback, mpv, pickup, bus, truck, estate]
upload_parser.add_argument("start_times", action='append', type=int, required=True)
upload_parser.add_argument("end_times", action='append', type=int, required=True)
upload_parser.add_argument("cam_serials", action='append', type=str, required=True)
model = api.model('Item', {
	"error": fields.String(),
	"object": fields.List(fields.Integer()),
	"start_times": fields.List(fields.Float(), required=True),
	"end_times": fields.List(fields.Float(), required=True),
	"cam_serials": fields.List(fields.String(), required=True),
	"type_vehicle": fields.List(fields.Integer()),
}, mask='{error}')
@api.route('/briefCam')
# @api.doc(params={'videos': 'Path of videos'})
@api.expect(upload_parser)
class briefCam(Resource):
	def post(self):
		args = upload_parser.parse_args()
		# inputts = args['videos']
		objectt = args['object']
		print(args['cam_serials'])
		job_id = str(uuid.uuid4())
		print("-------job_id: ", job_id)

		try:
			print("---start_times: ", args['start_times'])
			print("---end_times: ", args['end_times'])
			inputts = get_merge_video_custom(args['start_times'], args['end_times'], args['cam_serials'], url_auth=URL_AUTH, url_access=URL_ACCESS, folder_storage=FOLDER_STORAGE, job_id=job_id)
			print("-------------inputts: ", inputts)
			inputts = inputts["video"]
			# inputts = ["videoTest/video7.mp4"]
			if inputts is None:
				return {"success": False, "error": {"message": f"Authetic token is wrong"}}

			not_exists = []
			for inputt in inputts:
				if os.path.exists(inputt):
					continue
				else:
					not_exists.append(inputt)
			if len(not_exists) > 0:
				not_exists = str(not_exists).strip('][')
				return {"success": False, "error": {"message": f"Path {not_exists} is not correct"}}

			path_jobid = os.path.join(PATH_LOG_ABSOLUTE,job_id)
			if not os.path.exists(path_jobid):
				os.mkdir(path_jobid)

			with open(os.path.join(path_jobid, 'percent.txt'), 'w') as f:
				f.write("0")
			with open(os.path.join(path_jobid, 'result.txt'), 'w') as f:
				f.write("None")
			# data_input = [inputts, classs, weight, q_com, q_output]
			data_input = [inputts, objectt]

			# main(*data_input)
			job = q.enqueue_call(func=track_briefcam, args=(inputts, objectt, args['type_vehicle'], args['start_times'], args['cam_serials'], s.getsockname()[0], 15, job_id, URL_AUTH, URL_ACCESS, FOLDER_SUMMARY), timeout=259200, failure_ttl=30, job_id=job_id)
			print(job.id)
			return {"success": True, "idJob": job.id}

		except Exception as e:
			return {"success": False, "error": str(e)}

upload_parser1 = api.parser()
upload_parser1.add_argument("deleted", type=inputs.boolean, required=True)
upload_parser1.add_argument("jobID", type=str, required=True)
@api.expect(upload_parser1)
@api.route('/checkComplete')
class checkComplete(Resource):
	def post(self):
		args = upload_parser1.parse_args()
		
		try:
			job = Job.fetch(args['jobID'], connection=conn)
			if job.get_status() == 'failed':
				return {"success": False, "error": "No detection"}

			outBrief = []
			with open(os.path.join(PATH_LOG_ABSOLUTE,f"{args['jobID']}/percent.txt"), 'r') as f:
				percentComplete = f.read()
				if percentComplete == "0" or percentComplete == "0\n":
					percentComplete = None
			with open(os.path.join(PATH_LOG_ABSOLUTE,f"{args['jobID']}/result.txt"), 'r') as f:
				list_result = f.readlines()
				if list_result[0] == "None" or list_result[0] == "None\n":
					outBrief = None
				else:
					for result in list_result:
						outBrief.append(result.split("\n")[0])

			# 	delete_output()
			if args['deleted']:
				delete_log(args['jobID'])
			# 	delete_output()

			return {"success": True, "percentComplete": percentComplete, "output": outBrief}

		except Exception as e:
			return {"success": False, "error": str(e)}

upload_parser_stopJob = api.parser()
upload_parser_stopJob.add_argument("jobID", type=str, required=True)
@api.expect(upload_parser_stopJob)
@api.route('/stopJob')
class stopJob(Resource):
	def post(self):
		try:
			args = upload_parser_stopJob.parse_args()
			send_stop_job_command(conn, args['jobID'])
			# with open(os.path.join(PATH_LOG_ABSOLUTE,f'{args['jobID']}/percent.txt'), 'w') as f:
			# 	f.write("0")
			delete_log(args['jobID'])
			delete_output(args['jobID'])
			# registry = q.failed_job_registry
			# print(registry.get_job_ids())
			# registry.remove(registry.get_job_ids()[-1])
			return {"success": True}

		except Exception as e:
			return {"success": False, "error": str(e)}

# upload_parser_searchVehicle = api.parser()
# upload_parser_searchVehicle.add_argument("input", type=str, required=True)
# # upload_parser_searchVehicle.add_argument("colors", action='append', type=int, required=True)
# # upload_parser_searchVehicle.add_argument("types", action='append', type=int, required=True)
# @api.expect(upload_parser_searchVehicle)
# @api.route('/searchVehicle')
# class searchVehicle(Resource):
# 	def post(self):
# 		try:
# 			args = upload_parser_searchVehicle.parse_args()
# 			# color_type = args["colors"] + args["types"]
# 			# color_type_convert = []
# 			# for i in range(19):
# 			# 	if i in color_type:
# 			# 		color_type_convert.append(1)
# 			# 	else:
# 			# 		color_type_convert.append(-1)
# 			# list_image_select = search_vehicle(args["input"], color_type_convert)
# 			colors, types = search_vehicle(args["input"])
# 			return {"success": True, "colors": colors, "types": types}

# 		except Exception as e:
# 			return {"success": False, "error": str(e)}

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=3456, debug=True)
