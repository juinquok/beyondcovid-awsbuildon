# This function performs a train test split for your images coming from the same source folder

import json
import os
import boto3
from botocore.exceptions import ClientError
import re
import math
import random

# pls define your train test split ratio
ratio = 0.2

# Define resource and client
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

source_bucket_name = <<SOURCE BUCKET HERE>>  # change input bucket name
# change destionation bucket name
destination_bucket_name = <<OUTPUT BUCKET HERE>>
rpi_upload_bucket = s3.Bucket(source_bucket_name)


def lambda_handler(event, context):
    # Get list of all the images file names
    images = [f.key for f in rpi_upload_bucket.objects.all() if re.search(
        r'([a-zA-Z0-9\s_\\.\-\(\):])+(.jpg|.jpeg|.png)$', f.key)]
    to_delete = images.copy()

    # Get total and test number of images
    num_images = len(images)
    num_test_images = math.ceil(ratio*num_images)

    # Train test folder automtically created if it doesnt exist
    # Create test set
    for i in range(num_test_images):
        idx = random.randint(0, len(images)-1)
        filename = images[idx]
        # Copy image
        copy_source_object = {'Bucket': source_bucket_name, 'Key': filename}
        s3_client.copy_object(CopySource=copy_source_object,
                              Bucket=destination_bucket_name, Key='test/'+filename)
        # Copy xml
        xml_filename = os.path.splitext(filename)[0]+'.xml'
        copy_source_object = {
            'Bucket': source_bucket_name, 'Key': xml_filename}
        s3_client.copy_object(CopySource=copy_source_object,
                              Bucket=destination_bucket_name, Key='test/'+filename)
        images.remove(images[idx])

    # Create train set
    for filename in images:
        # Copy image
        copy_source_object = {'Bucket': source_bucket_name, 'Key': filename}
        s3_client.copy_object(CopySource=copy_source_object,
                              Bucket=destination_bucket_name, Key='train/'+filename)
        # Copy xml
        xml_filename = os.path.splitext(filename)[0]+'.xml'
        copy_source_object = {
            'Bucket': source_bucket_name, 'Key': xml_filename}
        s3_client.copy_object(CopySource=copy_source_object,
                              Bucket=destination_bucket_name, Key='train/'+filename)

    # Delete all the images and xml in source bucket
    for filename in to_delete:
        s3_client.delete_object(Bucket=source_bucket_name, Key=filename)
        s3_client.delete_object(Bucket=source_bucket_name,
                                Key=os.path.splitext(filename)[0]+'.xml')
