import json
import boto3
import datetime

s3 = boto3.resource('s3')
bucket = ""
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):

    table = dynamodb.Table('beyondcovid_mask_alerts')
    response = table.scan()
    all_responses = response.get('Items', [])
    sorted_responses = sorted(
        all_responses, key=lambda k: k['timestamp'], reverse=True)
    dates = []
    toReturn = {}
    dates = [datetime.datetime.strptime(
        response['timestamp'][:-7], '%Y-%m-%d %H:%M:%S').date() for response in sorted_responses]
    dates = list(set(dates))
    dates = sorted(dates, reverse=True)
    for date in dates:
        toReturn[date.strftime('%d %b %Y')] = [response for response in sorted_responses if datetime.datetime.strptime(
            response['timestamp'][:-7], '%Y-%m-%d %H:%M:%S').date().strftime('%d %b %Y') == date.strftime('%d %b %Y')]

    for key in toReturn:
        for image in toReturn[key]:
            url = boto3.client('s3').generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': 'dashboard-no-mask',
                        'Key': image['image_name']},
                ExpiresIn=3600)
            image['image_url'] = url

    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json',
            'Access-Control-Allow-Credentials': True,
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        'body': json.dumps(toReturn)
    }


def getDate(toReturn):
    return
