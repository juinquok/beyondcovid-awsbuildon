import logging
import os
import sys

from awsiot.greengrasscoreipc.model import QOS

# Set all the constants
SCORE_THRESHOLD = 0.3
MAX_NO_OF_RESULTS = 5
SHAPE = (416, 416)
QOS_TYPE = QOS.AT_LEAST_ONCE
TIMEOUT = 10
SCORE_CONVERTER = 255

# retraining params
RETRAINING_BUCKET = "images-for-facemask-detection-labelling"
LOWER_SCORE_THRESHOLD = 0.1
NO_MASK_BUCKET = "dashboard-no-mask"

# Intialize all the variables with default values
CAMERA = None
DEFAULT_IMAGE_NAME = "no_mask.png"
DEFAULT_BOUNDED_OUTPUT_IMAGE_NAME = "bounded_output.jpeg"
DEFAULT_PREDICTION_INTERVAL_SECS = 60
DEFAULT_USE_CAMERA = "true"
UPDATED_CONFIG = False
SCHEDULED_THREAD = None
TOPIC = "ml/tflite/object-detection"

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Get the model directory and images directory from the env variables.
MODEL_DIR = os.path.expandvars(os.environ.get("TFLITE_OD_MODEL_DIR"))
IMAGE_DIR = os.path.expandvars(os.environ.get("DEFAULT_TFLITE_OD_IMAGE_DIR"))
WORK_DIR = os.path.expandvars(os.environ.get("PWD"))
BOUNDED_OUTPUT_DIR_NAME = "bounded_output"
BOUNDED_OUTPUT_DIR = os.path.join(WORK_DIR, BOUNDED_OUTPUT_DIR_NAME)
