import urllib
import json
import boto3
from datetime import datetime
import sys
import urllib3
http = urllib3.PoolManager()

# This lambda will be triggered by a new image being pushed to the ECR Repo or by the retraining lambda

S3_OUTPUT_BUCKET = <<ENTER S3 OUTPUT BUCKET HERE>>
S3_IMAGES_BUCKET = <<ENTER S3 IMAGES BUCKET HERE>>


def lambda_handler(event, context):
    print(event)
    # get sagemaker client
    sagemaker = boto3.client('sagemaker')

    s3 = boto3.resource('s3')

    BUCKET = <<ENTER SETTINGS INPUT BUCKET HERE>>
    FILE = 'training_settings.json'

    obj = s3.Object(BUCKET, FILE)
    data = obj.get()['Body'].read().decode('utf-8')
    hyperparams = json.loads(data)

    # creating unique job name based on datetime
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%YT%H-%M-%S")

    training_job_name = "maskDetection-" + dt_string

    input_data = {
        'ChannelName': "training",
        'DataSource': {
            'S3DataSource': {
                'S3DataType': "S3Prefix",
                'S3Uri': S3_IMAGES_BUCKET
            }
        }
    }

    print("Creating training job...")

    S3_OUTPUT_BUCKET_TENSORBOARD = S3_OUTPUT_BUCKET + "/tensorboard"
    S3_OUTPUT_BUCKET_CHECKPOINTS = S3_OUTPUT_BUCKET + "/checkpoints"

    try:

        response = sagemaker.create_training_job(
            TrainingJobName=training_job_name,
            HyperParameters=hyperparams,
            AlgorithmSpecification={
                'TrainingImage': << ENTER TRAINING IMAGE HERE >>,
                'TrainingInputMode': "File"
            },
            RoleArn = << ENTER ROLE HERE >> ,
            InputDataConfig=[input_data],
            OutputDataConfig={
                'S3OutputPath': S3_OUTPUT_BUCKET
            },
            ResourceConfig={
                "InstanceType": "ml.m5.xlarge",
                "InstanceCount": 1,
                "VolumeSizeInGB": 30
            },
            StoppingCondition={
                'MaxRuntimeInSeconds': 86400
            },
            CheckpointConfig={
                'S3Uri': S3_OUTPUT_BUCKET_CHECKPOINTS
            },
            TensorBoardOutputConfig={
                'S3OutputPath': S3_OUTPUT_BUCKET_TENSORBOARD
            }
        )

    except Exception as e:
        print("Error in creating training job: {}".format(e))
        sys.exit(0)

    print(response)
    print("Training Job created")
