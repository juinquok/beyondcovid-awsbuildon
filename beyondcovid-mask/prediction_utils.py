import ast
import datetime
import io
import json
import os
import platform
import sys
import time
from time import sleep
from math import floor
from io import BytesIO

import config_utils
import IPCUtils as ipc_utils
import numpy as np
from numpy import uint8, fromstring
import tflite_runtime.interpreter as tflite

from cv2 import (
    COLOR_BGR2RGB,
    COLOR_BGRA2RGB,
    COLOR_GRAY2RGB,
    FONT_HERSHEY_SIMPLEX,
    IMWRITE_JPEG_QUALITY,
    CV_8UC3,
    CAP_PROP_FOURCC,
    FONT_HERSHEY_DUPLEX,
    LINE_AA,
    VideoWriter_fourcc,
    VideoCapture,
    cvtColor,
    imdecode,
    imread,
    imwrite,
    putText,
    rectangle,
    resize,
    getTextSize,
)


config_utils.logger.info("Using tflite from '{}'.".format(
    sys.modules[tflite.__package__].__file__))
config_utils.logger.info("Using np from '{}'.".format(np.__file__))

# Read labels file
# Use to following format:
# {0 : "mask_on", 1 : "mask_off", 2: "mask_incorrectly_worn"}
try:
    labels_path = os.path.join(config_utils.MODEL_DIR, "labels.txt")
    with open(labels_path, "r") as f:
        labels = ast.literal_eval(f.read())
except Exception as e:
    config_utils.logger.error(
        "Exception occured when loading labels file: {}".format(e))

# this must run on startup to load the model
# model file should be named model.tflite and be in the model's model eg: {archive}/MobileNet/model.tflite
try:
    interpreter = tflite.Interpreter(
        model_path=os.path.join(config_utils.MODEL_DIR, "model.tflite")
    )
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
except Exception as e:
    config_utils.logger.info(
        "Exception occured during the model loading in prediction_utils.py: {}".format(e))
    exit(1)

# Called by the inference.py init function for the camera code


def enable_camera():
    r"""
    Checks of the supported device types and access the camera accordingly.
    """
    if platform.machine() == "armv7l":  # RaspBerry Pi

        try:
            # Below for RPI Camera v2.0
            import picamera

            camera = picamera.PiCamera()

            config_utils.CAMERA = camera

        except Exception as e:
            config_utils.logger.error(
                "Error in initializing onboard camera: {}".format(e))
            config_utils.CAMERA = None


def predict_from_cam():
    r"""
    Captures an image using camera and sends it for prediction
    """
    cvimage = None

    if config_utils.CAMERA is None:
        config_utils.logger.error("Unable to use the camera.")
        exit(1)
    if platform.machine() == "armv7l":  # RaspBerry Pi
        # Below for RPI Camera v2
        stream = BytesIO()
        config_utils.CAMERA.start_preview()
        sleep(2)

        config_utils.CAMERA.capture(stream, format="jpeg")

        data = fromstring(stream.getvalue(), dtype=uint8)

        cvimage = imdecode(data, 1)

        # Below for webcam use
        # ret, cvimage = config_utils.CAMERA.read()

    if cvimage is not None:
        return predict_from_image(cvimage)
    else:
        config_utils.logger.error("Unable to capture an image using camera")
        exit(1)

# this loads any valid opencv image file type


def load_image(image_path):
    try:
        image_data = imread(image_path)
    except Exception as e:
        config_utils.logger.error(
            "Unable to read the image at: {}. Error: {}".format(
                image_path, e)
        )
        exit(1)
    return image_data


def predict_from_image(source_image):
    config_utils.logger.info("Beginning image resizing for prediction")

    try:

        image = cvtColor(source_image, COLOR_BGR2RGB)
        image = resize(
            (image*2/255)-1, (input_details[0]['shape'][1], input_details[0]['shape'][1]))
        img = image[np.newaxis, :, :, :].astype('float32')
        inference_results = predict(img, source_image)

    except Exception as e:
        config_utils.logger.error(
            "Error in resizing / prediction: {}".format(e))


def send_for_retraining(source_image):
    import boto3
    from botocore.exceptions import ClientError

    try:
        config_utils.logger.info(
            "Image confidence below minimum, uploading image for labelling")

        imwrite('retrain.jpg', source_image)

        s3 = boto3.client('s3')
        new_object_name = datetime.datetime.now().isoformat().replace(
            ":", "M").replace(".", "S") + "_retrain" + ".jpg"

        with open("retrain.jpg", "rb") as f:
            s3.upload_fileobj(
                f, config_utils.RETRAINING_BUCKET, new_object_name)

    except Exception as e:
        config_utils.logger.error(
            "Unable to upload image to s3 bucket: {}".format(e))


def send_no_mask_photo(source_image, boxes, classes, num, scores):
    import boto3
    from botocore.exceptions import ClientError

    try:
        config_utils.logger.info("No mask detected, trigering alert")
        WIDTH = 1034
        HEIGHT = 768

        def draw_and_show(box, frame):
            # print(scores[0][int(i)-1])
            y, x, bottom, right = box
            x, right = int(x*WIDTH), int(right*WIDTH)
            y, bottom = int(y*HEIGHT), int(bottom*HEIGHT)
            class_type = "No Mask"
            label_size = getTextSize(class_type, FONT_HERSHEY_DUPLEX, 0.5, 1)
            rectangle(frame, (x, y), (right, bottom), (255, 0, 0), thickness=2)
            rectangle(frame, (x, y-18),
                      (x+label_size[0][0], y), (255, 0, 0), thickness=-1)
            putText(frame, class_type, (x, y-5),
                    FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 0), 1, LINE_AA)
            return frame

        # image = cvtColor(source_image, COLOR_BGR2RGB)
        image = source_image

        for i in range(int(num[0])):
            if scores[0][i] > config_utils.SCORE_THRESHOLD and int(classes[0][i]) != 0:
                image = draw_and_show(boxes[0][i], image)

        imwrite('no_mask.jpg', image)

        s3 = boto3.client('s3')

        new_object_name = datetime.datetime.now().isoformat().replace(
            ":", "M").replace(".", "S") + "_no_mask" + ".jpg"

        with open("no_mask.jpg", "rb") as f:
            s3.upload_fileobj(
                f, config_utils.NO_MASK_BUCKET, new_object_name)

        return new_object_name

    except Exception as e:
        config_utils.logger.error(
            "Unable to upload image to s3 bucket: {}".format(e))


def predict(image_data, source_image):
    r"""
    Performs object detection and predicts using the model.

    :param image_data: numpy array of the resized image passed in for inference.
    :return: JSON object of inference results
    """
    PAYLOAD = {}
    PAYLOAD["timestamp"] = str(datetime.datetime.now())
    PAYLOAD["inference_type"] = "object-detection"
    PAYLOAD["inference_description"] = "Top {} predictions with score {} or above ".format(
        config_utils.MAX_NO_OF_RESULTS, config_utils.SCORE_THRESHOLD
    )
    PAYLOAD["inference_results"] = []
    try:

        interpreter.set_tensor(input_details[0]["index"], image_data)
        interpreter.invoke()

        try:

            boxes = interpreter.get_tensor(output_details[0]['index'])
            classes = interpreter.get_tensor(output_details[1]['index'])
            scores = interpreter.get_tensor(output_details[2]['index'])
            num = interpreter.get_tensor(output_details[3]['index'])

        except Exception as e:
            config_utils.logger.error(
                "Exception in extracting results from interpreter array; {}".format(e))

        s3_flag = False
        no_mask_trigger = False

        for i in range(int(num[0])):
            if scores[0][i] > config_utils.SCORE_THRESHOLD:
                if int(classes[0][i]) != 0:
                    no_mask_trigger = True
                result = {
                    "Label": str(labels[int(classes[0][i])]),
                    "Score": str(scores[0][i]),
                    "BoundingBox": str(np.array2string(boxes[0][i]))
                }
                PAYLOAD["inference_results"].append(result)
            if scores[0][i] < config_utils.SCORE_THRESHOLD and scores[0][i] > config_utils.LOWER_SCORE_THRESHOLD:
                s3_flag = True

        config_utils.logger.info("Processing output...")
        config_utils.logger.info(json.dumps(PAYLOAD['inference_results']))

        if s3_flag:
            send_for_retraining(source_image)
            s3_flag = False

        if no_mask_trigger:
            image_name = send_no_mask_photo(
                source_image, boxes, classes, num, scores)
            no_mask_trigger = False
            PAYLOAD['image_name'] = image_name
            if config_utils.TOPIC.strip() != "":
                ipc_utils.IPCUtils().publish_results_to_cloud(PAYLOAD)
            else:
                config_utils.logger.info(
                    "No topic set to publish the inference results to the cloud")

    except Exception as e:
        config_utils.logger.error(
            "Exception occured during prediction/processing: {}".format(e))
        exit(1)
