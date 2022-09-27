################################################################
#                      About this module                       #
################################################################
# Usage:
# 1. Set up YDB and service account with (ydb.editor, ydb.viewer) rights
# 2. Create specific tables in the YDB
# 3. Set up Yandex function and assign created service account to it

import json

from ydb_session import YDBSession
from task_solver import *


def handler(event, context):
    ydb_session = YDBSession()

    task = event["messages"][0]["details"]["message"]["body"]
    task = json.loads(task)

    chat_id = task["chat_id"]
    text = task["text"]

    solve_echo(chat_id, text)

    return {
        'statusCode': 200,
        'event': event,
        'context': context
    }
