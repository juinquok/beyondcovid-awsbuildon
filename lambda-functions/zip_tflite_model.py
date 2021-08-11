# This code will zip a tflite model together with the labels.txt file for deployment to the edge device
# This is part of the model component package on greengrass

import json
import boto3
import io
import zipfile
import urllib3
http = urllib3.PoolManager()


def lambda_handler(event, context):
    SOURCE_BUCKET = <<INPUT BUCKET WHERE THE TFLITE MODEL WAS OUTPUT>>

    OUTPUT_BUCKET = <<OUPUT BUCKET HERE WHERE GREENGRASS WILL READ IT FROM>>
    files = [['labels.txt', 'new_models/labels.txt'],
             ['model.tflite', 'new_models/model.tflite']]

    resp = http.request("GET", url)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
        for file_details in files:
            print("Downloading file: {}".format(file_details[1]))
            infile_object = s3.get_object(
                Bucket=SOURCE_BUCKET, Key=file_details[1])
            infile_content = infile_object['Body'].read()
            zipper.writestr(file_details[0], infile_content)

    response = s3.put_object(
        Bucket=OUTPUT_BUCKET, Key="beyondcovid-ssdlitemobilenet.zip", Body=zip_buffer.getvalue())
    print(response)
    print('File successfully uploaded')
