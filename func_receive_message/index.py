def handler(event, context):
    # EVENT - this is the information that the queue sends
    print(event)

    return {
        'statusCode': 200,
        'event': event,
        'context': context
    }
