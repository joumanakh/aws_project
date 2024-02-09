mport json
import time
from pathlib import Path
from decimal import Decimal
import requests
from detect import run
import yaml
from loguru import logger
import os
import boto3
from botocore.exceptions import NoCredentialsError
images_bucket = os.environ['BUCKET_NAME']
queue_name = os.environ['SQS_QUEUE_NAME']

sqs_client = boto3.client('sqs', region_name='eu-north-1')

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']


def consume():
    while True:
        response = sqs_client.receive_message(QueueUrl=queue_name, MaxNumberOfMessages=1, WaitTimeSeconds=5)

        if 'Messages' in response:
            message = response['Messages'][0]['Body']
            receipt_handle = response['Messages'][0]['ReceiptHandle']

            # Use the ReceiptHandle as a prediction UUID
            prediction_id = response['Messages'][0]['MessageId']

            logger.info(f'prediction: {prediction_id}. start processing')

            # Receives a URL parameter representing the image to download from S3
            message_body_json = json.loads(message)

            img_name = message_body_json['image_name']  # TODO extract from `message`
            chat_id = message_body_json['chat_id']  # TODO extract from `message`
            #original_img_path = ...
            # TODO download img_name from S3, store the local image path in original_img_path
            #^^^^^^^^^^^
            # ****************
            s3 = boto3.client('s3')

            nested_directory_path = f'data/images'

            # Expand the '~' to the user's home directory
            nested_directory_path = os.path.expanduser(nested_directory_path)

            # Create the nested directory if it doesn't exist
            if not os.path.exists(nested_directory_path):
                os.makedirs(nested_directory_path)
            local_img_path = f'{nested_directory_path}/{img_name}'
            print("****************" + local_img_path + "***************")
            try:
                s3.download_file(images_bucket, img_name, local_img_path)
                logger.info(f'prediction: {prediction_id}/{local_img_path}. Download img completed')
            except NoCredentialsError:
                logger.error("AWS credentials not available.")
                return "Error: AWS credentials not available.", 500
            except Exception as e:
                logger.error(f"Error downloading image: {e}")
                return f"Error downloading image: {e}", 500
            # ****************
            #  The bucket name should be provided as an env var BUCKET_NAME.
            # original_img_path = ...
            original_img_path = local_img_path
            #^^^^^^^^^^^

            logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')

            # Predicts the objects in the image
            run(
                weights='yolov5s.pt',
                data='data/coco128.yaml',
                source=original_img_path,
                project='static/data',
                name=prediction_id,
                save_txt=True
            )

            logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

            # This is the path for the predicted image with labels
            # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
            # ^^^^^^^^^^^^^^^^^^^^
            nested_directory_path = f'static/data/{prediction_id}'

            # Expand the '~' to the user's home directory
            nested_directory_path = os.path.expanduser(nested_directory_path)

            # Create the nested directory if it doesn't exist
            if not os.path.exists(nested_directory_path):
                os.makedirs(nested_directory_path)
            predicted_img_path = f'{nested_directory_path}/{img_name}'
            # ^^^^^^^^^^^^^^^^^^^^
            # predicted_img_path = Path(f'static/data/{prediction_id}/{img_name}')
            # TODO Uploads the predicted image (predicted_img_path) to S3 (be careful not to override the original image).
            #*************
            try:
                s3.upload_file(predicted_img_path, images_bucket, f'predictions/{img_name}')
                logger.info(f'prediction: {local_img_path}. Predicted img uploaded to S3.')
            except Exception as e:
                logger.error(f"Error uploading predicted image to S3: {e}")
            #the_image = original_img_path[:-4] + "_predictedImage.jpg"
            #s3.upload_file(str(predicted_img_path), images_bucket, the_image)
            # *************
            # Parse prediction labels and create a summary
            pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
            if pred_summary_path.exists():
                with open(pred_summary_path) as f:
                    labels = f.read().splitlines()
                    labels = [line.split(' ') for line in labels]
                    labels = [{
                        'class': names[int(l[0])],
                        'cx': float(l[1]),
                        'cy': float(l[2]),
                        'width': float(l[3]),
                        'height': float(l[4]),
                    } for l in labels]

                logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

                prediction_summary = {
                    'prediction_id': {'S': str(prediction_id)},
                    'original_img_path': {'S': str(original_img_path)},
                    'predicted_img_path': {'S': str(predicted_img_path)},
                    'labels': {'S': json.dumps(labels)},
                    'time': {'N': str(Decimal(str(time.time())))}
                }
                # TODO store the prediction_summary in a DynamoDB table
                dynamodb_client = boto3.client('dynamodb', region_name='eu-north-1')
                dynamodb_table_name = 'joumanakh_table'
                dynamodb_client.put_item(TableName=dynamodb_table_name, Item=prediction_summary)

                # TODO perform a GET request to Polybot to `/results` endpoint
                url = f'http://joumanakh-loadbalancer-1797806028.eu-north-1.elb.amazonaws.com:80/results?chat_id={chat_id}&prediction_id={prediction_id}'
                print(url)
                print("woooooooooooooooooowwwwuuuuuuuurlllll")
                requests.get(url)
            # Delete the message from the queue as the job is considered as DONE
            else:

             print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")             
             logger.info('hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh')
             sqs_client.delete_message(QueueUrl=queue_name, ReceiptHandle=receipt_handle)


if __name__ == "__main__":
    consume()

 
