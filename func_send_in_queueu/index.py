import boto3


def handler(event, context):
    # Create client
    client = boto3.client(
        service_name='sqs',
        endpoint_url='https://message-queue.api.cloud.yandex.net',
        region_name='ru-central1'
    )

    # Get url queue
    queue_url = client.get_queue_url(QueueName="msg_queue")["QueueUrl"]

    # The text of the message to be sent
    msg_text = "Hello world"

    # Add this text in turn
    client.send_message(
        QueueUrl=queue_url,
        MessageBody=msg_text,
    )

    return {
        'statusCode': 200,
        'send_message_text': msg_text,
        'event': event,
        'context': context,
    }
