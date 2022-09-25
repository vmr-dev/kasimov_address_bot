import boto3


def create_client():
    client = boto3.client(
        service_name='sqs',
        endpoint_url='https://message-queue.api.cloud.yandex.net',
        region_name='ru-central1'
    )
    
    return client


def create_queue(sqs_client, name_queue):
    response = sqs_client.create_queue(
        QueueName=name_queue,
        Attributes={
            "DelaySeconds": "0",
            "VisibilityTimeout": "60",
        }
    )
    
    return response


def get_queue_url(sqs_client, name_queue):
    response = sqs_client.get_queue_url(
        QueueName=name_queue,
    )

    return response["QueueUrl"]
