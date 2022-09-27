# In this handler we get message from telegram
# and create message (task) in queue
# then, queue triggers our other Yandex function (processor)

import os
import json
import boto3


def create_task(task_body):
    client = boto3.client(
        service_name='sqs',  # constant name for queue service
        endpoint_url=os.getenv("QUEUE_ENDPOINT"),
        region_name='ru-central1'
    )

    queue_url = client.get_queue_url(QueueName="kasimov-houses-tasks")["QueueUrl"]

    client.send_message(
        QueueUrl=queue_url,
        MessageBody=task_body,
    )

    client.close()


def handler(event, context):
    body = json.loads(event["body"])

    if "message" in body and "text" in body["message"]:
        text = body["message"]["text"]
        chat_id = body["message"]["chat"]["id"]

        payload = {"chat_id": chat_id, "text": text}
        payload = json.dumps(payload, indent=4)
        create_task(payload)

    return {
        'statusCode': 200,
        'body': 'Everything is OK.',
    }
