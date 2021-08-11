import json
import boto3
import time

TELEGRAM_URL = 'https://api.telegram.org/<<YOUR BOTS CODE HERE>>/'

ADD_LOC_BUTTON = {
    'text': 'Add new location using code',
    'callback_data': '/join_alert_group'
}
REMOVE_LOC_BUTTON = {
    'text': "Unsubscribe from a location's alerts",
    'callback_data': '/leave_alert_group'
}
VIEW_LOC_BUTTON = {
    'text': 'View subscribed locations',
    'callback_data': '/my_alert_groups'
}

MAIN_MENU = {
    'inline_keyboard': [[ADD_LOC_BUTTON], [REMOVE_LOC_BUTTON], [VIEW_LOC_BUTTON]],
    'resize_keyboard': True,
    'one_time_keyboard': True
}

REMOVE_LOCATION_MENU = {
    'inline_keyboard': [[{
        'text': "Test Mall - Main Entrance",
        'callback_data': '/remove_test_mall_main_entrance'
    }]],
    'resize_keyboard': True,
    'one_time_keyboard': True
}

db = boto3.resource('dynamodb')
settings = db.Table('beyondcovid_telegram_alert')


def lambda_handler(event, context):
    tele_req = event['body']
    tele_req = json.loads(tele_req)

    print(tele_req)

    PAYLOAD = {}

    try:

        if 'message' in tele_req:

            req_msg = tele_req['message']
            chat_id = req_msg['chat']['id']

            if req_msg['text'] == '/start':
                reply = {}
                reply['chat_id'] = req_msg['chat']['id']
                reply['text'] = "Welcome to the BeyondCovid Alerts System. To use this system, you should already have an alert code provided to you. Please choose from the options below."
                reply['reply_markup'] = MAIN_MENU
                reply['method'] = 'sendMessage'

                return json.dumps(reply)

            elif req_msg['text'][0:5].lower() == 'locid':

                req_invite_id = req_msg['text']
                data = settings.get_item(Key={'setting': 'codes'})
                all_active_codes = data['Item']['data_value']

                unused_codes = []
                checkflag = False
                for code in all_active_codes:
                    if str(code.lower()) == str(req_invite_id.lower()):
                        checkflag = True
                    else:
                        unused_codes.append(code)
                if checkflag:
                    # update the subscribers list
                    data = settings.get_item(Key={'setting': 'subscribers'})
                    all_active_subscribers = data['Item']['data_value']
                    all_active_subscribers.add(str(chat_id))
                    settings.update_item(
                        Key={
                            'setting': 'subscribers'
                        },
                        UpdateExpression='SET data_value = :val1',
                        ExpressionAttributeValues={
                            ':val1': all_active_subscribers
                        }
                    )

                    # update the active codes
                    settings.update_item(
                        Key={
                            'setting': 'codes'
                        },
                        UpdateExpression='SET data_value = :val1',
                        ExpressionAttributeValues={
                            ':val1': set(unused_codes)
                        }
                    )

                    # send the reponse
                    reply = {}
                    reply['chat_id'] = chat_id
                    reply['text'] = 'The code you have provided has been verified. You will now receive notifications from that location.'
                    reply['method'] = 'sendMessage'
                    return json.dumps(reply)

                else:
                    reply = {}
                    reply['chat_id'] = chat_id
                    reply['text'] = 'The code you have provided is not valid. Please check the code you have keyed in and try again.'
                    reply['method'] = 'sendMessage'
                    return json.dumps(reply)

            elif str(req_msg['text']) == "internal-aws-test-beyondcovid-telegram-alert":
                print("Creating testing account...")
                data = settings.get_item(Key={'setting': 'subscribers'})
                all_active_subscribers = data['Item']['data_value']
                all_active_subscribers.add(str(chat_id))
                settings.update_item(
                    Key={
                        'setting': 'subscribers'
                    },
                    UpdateExpression='SET data_value = :val1',
                    ExpressionAttributeValues={
                        ':val1': all_active_subscribers
                    }
                )
                reply = {}
                reply['chat_id'] = chat_id
                reply['text'] = 'The testing code you have provided has been verified. You will now receive notifications from that location.'
                reply['method'] = 'sendMessage'
                return json.dumps(reply)

            else:
                reply = {}
                reply['chat_id'] = chat_id
                reply['text'] = 'The code you have provided is not valid. Please check the code you have keyed in and try again.'
                reply['method'] = 'sendMessage'
                return json.dumps(reply)

        if 'callback_query' in tele_req:

            data = tele_req['callback_query']['data']
            print("The following callback command was received: {}".format(data))
            chat_id = tele_req['callback_query']['message']['chat']['id']

            if data == '/join_alert_group':
                reply = {}
                reply['chat_id'] = chat_id
                reply['text'] = "Please enter the code you were provided below and press the enter key"
                reply['method'] = 'sendMessage'
                return json.dumps(reply)

            if data == '/leave_alert_group':
                data = settings.get_item(Key={'setting': 'subscribers'})
                all_active_subscribers = data['Item']['data_value']
                if str(chat_id) in all_active_subscribers:
                    reply = {}
                    reply['chat_id'] = chat_id
                    reply['text'] = "Please select the location you wish to unsubscribe from alerts below."
                    reply['reply_markup'] = REMOVE_LOCATION_MENU
                    reply['method'] = 'sendMessage'
                    return json.dumps(reply)
                else:
                    reply = {}
                    reply['chat_id'] = chat_id
                    reply['text'] = "You are not currently not subscribed to any locations."
                    reply['method'] = 'sendMessage'
                    return json.dumps(reply)

            if data == '/my_alert_groups':
                data = settings.get_item(Key={'setting': 'subscribers'})
                all_active_subscribers = data['Item']['data_value']
                if str(chat_id) in all_active_subscribers:
                    reply = {}
                    reply['text'] = "You are subscribed to alerts from the following locations: Test Mall - Main Entrance"
                    reply['method'] = 'sendMessage'
                    reply['chat_id'] = chat_id
                    return json.dumps(reply)
                else:
                    reply = {}
                    reply['text'] = "You are currently not subscribed to alerts from any location"
                    reply['method'] = 'sendMessage'
                    reply['chat_id'] = chat_id
                    return json.dumps(reply)

            if data == '/remove_test_mall_main_entrance':
                print("User {} removing location".format(str(chat_id)))
                data = settings.get_item(Key={'setting': 'subscribers'})
                all_active_subscribers = data['Item']['data_value']
                all_active_subscribers.remove(str(chat_id))
                settings.update_item(
                    Key={
                        'setting': 'subscribers'
                    },
                    UpdateExpression='SET data_value = :val1',
                    ExpressionAttributeValues={
                        ':val1': all_active_subscribers
                    })
                reply = {}
                reply['text'] = "You are unsubscribed from alerts from the following locations: Test Mall - Main Entrance"
                reply['method'] = 'sendMessage'
                reply['chat_id'] = chat_id
                return json.dumps(reply)

    except Exception as e:
        print("Error occured: {}".format(e))
        return json.dumps({'Status': 'OK'})
