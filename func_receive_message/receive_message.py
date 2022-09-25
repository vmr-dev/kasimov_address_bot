from queue_settings import *


def handler(event, context):
    # Create client
    client = create_client()

    # Create queue and get its url
    # queue_url = create_queue(client, name_queue="msg_queue")

    # Get url queue
    queue_url = get_queue_url(client, name_queue="msg_queue")

    # Receive sent message
    get_msg = receive_sent_message(client, queue_url)
    delete_processed_messages(client, queue_url, get_msg)

    return {
        'statusCode': 200,
        'send_message_text': get_msg,
        'event': event,
        'context': context,
    }


def receive_sent_message(client, queue_url):
    # Receive sent message
    messages = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        VisibilityTimeout=60,
        WaitTimeSeconds=20
    ).get('Messages')

    for msg in messages:
        print("debug:", msg)

    return messages


def delete_processed_messages(client, queue_url, messages):
    # Delete processed messages
    for msg in messages:
        client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=msg.get('ReceiptHandle')
        )
        print('Deleted!')
