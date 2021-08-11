from datetime import datetime
import json
import boto3
import urllib
import urllib3
http = urllib3.PoolManager()


def lambda_handler(event, context):
    """
    The Ground truth labeling job is created when number of images in the bucket reaches n

    ALTERNATIVELY, we can check to see if the confidence and accuracy of the model is going down based on what is returned by the IOT.
    If they reach below a certain level, we can create the GT labelling job

    """

    IMAGE_NUM_TO_TRIGGER = 4

    # Get the bucket name
    bucket_name = event['Records'][0]['s3']['bucket']['name']

    # Get the file/key name
    key = urllib.parse.unquote_plus(
        event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    retrain_images_bucket_name = <<FILL THIS IN>>
    retrain_images_uri = "s3://" + retrain_images_bucket_name
    print("Event triggered from S3:", bucket_name)

    s3 = boto3.resource('s3')
    bucket_objects = s3.Bucket(bucket_name)
    num_images = 0
    input_manifest_string = ''

    # Count number of images to see if it meets condition
    for key in bucket_objects.objects.all():
        num_images += 1
    print("Number of images:", num_images)

    if num_images >= IMAGE_NUM_TO_TRIGGER:
        for key in bucket_objects.objects.all():
            # copy labelled images to retraining images bucket
            copy_source = {
                'Bucket': bucket_name,
                'Key': key.key
            }
            s3.meta.client.copy(
                copy_source, retrain_images_bucket_name, key.key)

            object_uri = retrain_images_uri + '/' + key.key
            input_manifest_string += '{"source-ref":"' + object_uri + '"}\n'

        # Remove all the images from original bucket
        bucket_objects.objects.all().delete()

        # Create manifest file
        encoded_string = input_manifest_string.encode("utf-8")
        manifest_bucket = <<FILL THIS IN>>
        manifest_filename = <<FILL THIS IN>>
        s3.Bucket(manifest_bucket).put_object(
            Key=manifest_filename, Body=encoded_string)

        manifest_uri = "s3://" + manifest_bucket + '/' + manifest_filename

        sagemaker_client = boto3.client('sagemaker')
        labelling_job_name = 'facemask-detection' + \
            str(datetime.now()).replace(
                " ", "T").replace(":", "").split(".")[0]

        # DOC: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker.html#SageMaker.Client.create_labeling_job
        labelling_job_arn = sagemaker_client.create_labeling_job(
            LabelingJobName=labelling_job_name,
            LabelAttributeName='facemask-detection',
            InputConfig={
                'DataSource': {
                    'S3DataSource': {
                        'ManifestS3Uri': manifest_uri
                    }
                }
            },
            OutputConfig={
                'S3OutputPath': << FILL THIS IN >>
            },
            RoleArn= << FILL THIS IN >>,
            LabelCategoryConfigS3Uri='s3://custom-files-groundtruth/labels.json',
            LabelingJobAlgorithmsConfig={
                'LabelingJobAlgorithmSpecificationArn': << FILL THIS IN >>
            },
            HumanTaskConfig={
                'WorkteamArn': << FILL THIS IN >> ,
                'UiConfig': {
                    'UiTemplateS3Uri': 's3://custom-files-groundtruth/bounding-box.liquid.html'
                },
                'PreHumanTaskLambdaArn': << FILL THIS IN >> ,
                'TaskTitle': 'Face Mask Detection',
                'TaskDescription': 'Please select the corresponding label and draw a boudning box around the person face',
                'NumberOfHumanWorkersPerDataObject': 1,
                'TaskTimeLimitInSeconds': 28000,
                'AnnotationConsolidationConfig': {
                    'AnnotationConsolidationLambdaArn': << FILL THIS IN >>
                }
            },
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'facemask-Detection-GeneratedJob'
                },
            ]
        )

        print("JOB ARN:", labelling_job_arn)

    else:
        print("No trigger, images below {}".format(IMAGE_NUM_TO_TRIGGER))
        return {
            'statusCode': 200,
            'body': json.dumps("No GT Labelling job trigger as number of images is below trigger ")
        }

    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps(labelling_job_arn)
    }
