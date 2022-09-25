from queue_settings import *


def handler(event, context):
    # Create client
    client = create_client()

    # Create queue and get its url
    # queue_url = create_queue(client, name_queue="msg_queue")

    # Get url queue
    queue_url = get_queue_url(client, name_queue="msg_queue")

    # Send message
    # Add this text in turn
    msg_text = "world"
    send_message(client, queue_url, msg_text)

    return {
        'statusCode': 200,
        'send_message_text': msg_text,
        'event': event,
        'context': context,
    }


def send_message(client, queue_url, send_word):
    # Send message to queue
    client.send_message(
        QueueUrl=queue_url,
        MessageBody=send_word
    )
    print("Sent successfully!")
