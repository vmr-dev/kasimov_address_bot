from threading import Thread
from task_solver import *


def handler(event, context):
    task = event["messages"][0]["details"]["message"]["body"]
    task = json.loads(task)

    chat_id = task["chat_id"]
    text = task["text"]

    try:
        solver = Thread(target=solve_task, args=(chat_id, text))
        solver.start()
        solver.join()
    finally:
        return {
            'statusCode': 200,
            'event': event,
            'context': context
        }
