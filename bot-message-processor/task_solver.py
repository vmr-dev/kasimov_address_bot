import os
import json

from telegram import Bot
from ydb_session import YDBSession

from dadata_address_suggester import unify_address


# example [1234124, 123124, 12431243]
ADMIN_ID_LIST = []


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise "You must set BOT_TOKEN environment variable before start your bot"


def pong(chat_id):
    bot = Bot(BOT_TOKEN)
    bot.send_message(chat_id, "pong!")


def show_help(chat_id):
    bot = Bot(BOT_TOKEN)
    help_msg = '''
Привет! Я жкх помощник, я могу рассказать тебе об
управляющей компании твоего дома.

Просто отправь мне адрес дома, например:
ул. 50 лет СССР д. 30А
И я постараюсь тебе помочь!
    '''
    bot.send_message(chat_id, help_msg)


def update_database(chat_id):
    if chat_id not in ADMIN_ID_LIST:
        return
    bot = Bot(BOT_TOKEN)
    response_msg = "Принято, обновляю базу"
    bot.send_message(chat_id, response_msg)

    ydb_session = YDBSession()
    try:
        ydb_session.update_database_with_parser()
    except:
        response_msg = "При обновлении что-то пошло не так.\n"
        response_msg += "Чтобы понять в чём причина, воспользуйтесь логами.\n"
        response_msg += "Возможно кончились платные запросы dadata.ru\n"
        bot.send_message(chat_id, response_msg)
        return

    response_msg = "База данных обновлена"
    bot.send_message(chat_id, response_msg)


# address_row - string we get after YDB SELECT request
# There are all fields of SELECT element
def get_filtered_house_info_answer(ydb_row):
    wanted_fields = [
        "адрес",
        "год",
        "этажей"
    ]
    result = "🏠 Информация о доме:\n\n"

    additional_info = json.loads(ydb_row["additional_info"])

    # Ищем по ключевым словам нужные нам ключи
    # если нашли - добавляем
    for wanted in wanted_fields:
        for info_key in additional_info.keys():
            if wanted in info_key.lower():
                result += '*' + info_key + '*: ' + additional_info[info_key] + '\n'

    return result


def get_filtered_company_info_str(ydb_row):
    wanted_fields = [
        "наименование",
        "адрес",
        "год",
        "фио",
        "руководитель",
        "код",
        "номер",
        "телефон"
    ]
    result = "🏢 Информация об управляющей компании:\n\n"

    additional_info = json.loads(ydb_row["additional_info"])

    for wanted in wanted_fields:
        for info_key in additional_info.keys():
            if wanted in info_key.lower():
                result += '*' + info_key + '*: ' + additional_info[info_key] + '\n'

    return result


def provide_address_info_to_user(chat_id, text):
    ydb_session = YDBSession()
    bot = Bot(BOT_TOKEN)
    is_requests_paid = ydb_session.has_user_paid_requests(chat_id)

    unified_address = unify_address("Касимов " + text, is_requests_paid)

    if not text:
        answer = "Ваш запрос не совсем понятен.\n"
        answer += "Попробуйте уточнить свой запрос\n"
        answer += "Если вам кажется, что это ошибка, то "
        answer += "пожалуйста сообщите об этом @Админ\n"
        bot.send_message(chat_id, answer)
        return

    # address was recognized, so we can start searching in ydb
    house_answer = ydb_session.search_in_database("houses", unified_address)

    if house_answer[0].rows:
        answer = get_filtered_house_info_answer(house_answer[0].rows[0])
        if house_answer[0].rows[0]["company_name"]:
            company_name = house_answer[0].rows[0]["company_name"]
            company_answer = ydb_session.search_in_database("companies", company_name)
            if company_answer[0].rows:
                answer += '\n' + get_filtered_company_info_str(company_answer[0].rows[0])
        else:
            answer += "\n\n🏢 Управляющая компания не найдена"
    else:
        answer = "Я не смог найти ваш адрес в своей базе.\n"
        answer += "Попробуйте уточнить свой запрос\n"
        answer += "Если вам кажется, что это ошибка, то "
        answer += "пожалуйста сообщите об этом @Админ\n"

    bot = Bot(BOT_TOKEN)
    bot.send_message(chat_id, answer, parse_mode="Markdown")


def reply_id(chat_id):
    bot = Bot(BOT_TOKEN)
    bot.send_message(chat_id, f"Ваш ID: `{chat_id}`", parse_mode="Markdown")

# Main command handler for tasks above
def solve_task(chat_id, text):
    if "/ping" in text:
        pong(chat_id)
    elif "/help" in text:
        show_help(chat_id)
    elif "/update" in text:
        update_database(chat_id)
    elif "/id" in text:
        reply_id(chat_id)
    else:
        provide_address_info_to_user(chat_id, text)
