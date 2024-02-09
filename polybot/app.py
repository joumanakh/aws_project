import collections
import json

import flask
from flask import request
import os
from bot import ObjectDetectionBot
import boto3
app = flask.Flask(__name__)


# TODO load TELEGRAM_TOKEN value from Secret Manager
#*****************************
secret_name = "joumanakh-telegram_token"
client = boto3.client('secretsmanager', region_name='eu-north-1')
response = client.get_secret_value(SecretId=secret_name)
response_json = json.loads(response['SecretString'])


TELEGRAM_TOKEN = response_json['TELEGRAM_TOKEN']

print(TELEGRAM_TOKEN)
#*****************************
#TELEGRAM_TOKEN = ...

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']
images_bucket = os.environ['BUCKET_NAME']

@app.route('/', methods=['GET'])
def index():
    print("im here1")
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    print("im heeereee wowwwwwwwww") 
    bot.handle_message(req['message'],images_bucket)
    return 'Ok'


@app.route(f'/results/', methods=['GET'])
def results():
    print("im innnnnnnnnnnnnnnnn reeeeeeeeeeeeesuuuuuuuultttttttts")
    prediction_id = request.args.get('prediction_id')
    print(prediction_id)
    # TODO use the prediction_id to retrieve results from DynamoDB and send to the end-user

    #chat_id = ...
    #text_results = ...
    dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
    table = dynamodb.Table('joumanakh_table')

    response_item = table.get_item(
        Key={
            'prediction_id': prediction_id
        }
    )
    chat_id = request.args.get('chat_id')
    print(chat_id)
    text_results = response_item
    labels_string = response_item.get('Item', {}).get('labels', [])
    labels = json.loads(labels_string)

    class_counts = collections.Counter(item['class'] for item in labels)
    res = json.dumps(dict(class_counts))
    text_results = "\n".join([f"{key}: {value}" for key, value in class_counts.items()])
    bot.send_text(chat_id, text_results)
    return 'Ok'


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)
