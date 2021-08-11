# This function send images via telegram after retrieveing the filename form a dynamodb
# DynamoDB receives this information from the IOT Core via MQTT

import json
import boto3
import urllib
import urllib3
import http.client
import mimetypes
from codecs import encode


def lambda_handler(event, context):

    print(event)
    # http = urllib3.PoolManager()

    def send_to_subscribers(image_name, timestamp):

        s3 = boto3.client('s3')
        db = boto3.resource('dynamodb')
        s3_resource = boto3.resource('s3')
        settings = db.Table( << FILL THIS IN>>)

        timestamp = timestamp.split(".")[0]
        caption = timestamp + ": Mask alert triggered at Main Entrance A, Test Mall"
        url = <<FILL THIS IN>>

        data = settings.get_item(Key={'setting': 'subscribers'})
        all_active_subscribers = data['Item']['data_value']

        temp_file_path = "/tmp/" + image_name

        s3_resource.meta.client.download_file(
            'dashboard-no-mask', image_name, temp_file_path)

        with open(temp_file_path, 'rb') as fp:
            file_data = fp.read()

        for user in all_active_subscribers:

            conn = http.client.HTTPSConnection("api.telegram.org")
            dataList = []
            boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
            dataList.append(encode('--' + boundary))
            dataList.append(
                encode('Content-Disposition: form-data; name=chat_id;'))

            dataList.append(encode('Content-Type: {}'.format('text/plain')))
            dataList.append(encode(''))

            dataList.append(encode(user))
            dataList.append(encode('--' + boundary))
            dataList.append(
                encode('Content-Disposition: form-data; name=caption;'))

            dataList.append(encode('Content-Type: {}'.format('text/plain')))
            dataList.append(encode(''))

            dataList.append(encode(caption))
            dataList.append(encode('--' + boundary))
            dataList.append(encode(
                'Content-Disposition: form-data; name=photo; filename={0}'.format(temp_file_path)))

            dataList.append(encode('Content-Type: {}'.format('image/jpeg')))
            dataList.append(encode(''))

            with open(temp_file_path, 'rb') as f:
                dataList.append(f.read())
            dataList.append(encode('--'+boundary+'--'))
            dataList.append(encode(''))
            body = b'\r\n'.join(dataList)
            payload = body
            headers = {
                'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
            }
            conn.request("GET", "/<<YOUR BOT ID HERE>>/sendPhoto",
                         payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(data.decode("utf-8"))

    send_to_subscribers(event['image_name'], event['timestamp'])
