import os
# from pathlib import Path
# FILE = Path(__file__).resolve()
# ROOT = FILE.parents[0]  # yolov5 strongsort root directory
# WEIGHTS = ROOT / 'weights'

from flask            import Flask, session, Blueprint, json
from flask_restx import Resource, Api, fields, inputs
from flask_cors 	  import CORS
from rq import Queue
from rq.command import send_stop_job_command
from rq.job import Job
from worker import conn
from datetime import timedelta
import socket
import uuid

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
# print(s.getsockname()[0])

URL_AUTH = os.getenv('URL_AUTH', "http://openstack.test.mqsolutions.vn/identity/v3/auth/tokens")
URL_ACCESS = os.getenv('URL_ACCESS', "http://s3.openstack.test.mqsolutions.vn/v1")
FOLDER_STORAGE = os.getenv('FOLDER_STORAGE', "videos_storage")
FOLDER_SUMMARY = os.getenv('FOLDER_SUMMARY', "video_summary")

app = Flask(__name__)

# app.config.from_object('configuration.Config')
print(app.config)
app.config['file_allowed'] = ['image/png', 'image/jpeg', 'application/octet-stream']
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=365)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_POOL_SIZE'] = 100
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 100

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
	'pool_size': 100,
}

q = Queue(connection=conn)
api_bp = Blueprint("api", __name__, url_prefix="/api")

api = Api(api_bp, version='1.0', title='Brief Cam API',
	description='Brief Cam API for everyone', base_url='/api'
)
app.register_blueprint(api_bp)
CORS(app, supports_credentials=True, allow_headers=['Content-Type', 'X-ACCESS_TOKEN', 'Authorization'], origins=[f"http://{s.getsockname()[0]}:3456"])
