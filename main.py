################################################################
#                      About this module                       #
################################################################
# Usage:
# 1. Set up YDB and service account with (ydb.editor, ydb.viewer) rights
# 2. Create specific tables in the YDB
# 3. Set up Yandex function and assign created service account to it

# TODO:
# 1. Change additional_info value type in the YDB from String to JSON
#
# 2. Add a message queue integration for tasks
#   (after telegram request-response test)

from ydb_session import YDBSession


def handler(event, context):
    ydb_session = YDBSession()

    return {
        'statusCode': 200,
        'body': 'Hello World!',
    }
