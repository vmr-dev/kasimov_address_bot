import os
import json

from datetime import date

from telegram import Bot
from ydb_session import YDBSession

from dadata_address_suggester import unify_address

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
    # DEBUG BOT
    bot = Bot(BOT_TOKEN)

    user_query = unify_address("Касимов " + text, False)
    house_answer = ydb_session.search_in_database("houses", user_query)
    user_info = ydb_session.search_in_database("users", chat_id)

    if user_info[0].rows:
        bot.send_message(chat_id, "DEBUG: Пользователь найден")
        paid_requests_count = user_info[0].rows[0]['paid_requests_count']
        user_date = user_info[0].rows[0]['date']

        if user_date == str(date.today()):
            if paid_requests_count > 0:
                paid_requests_count -= 1
                user_info = {'chat_id': chat_id, 'date': str(date.today()), 'paid_requests_count': paid_requests_count}
                ydb_session._write_db_user(user_info)
                bot.send_message(chat_id, "DEBUG: Запрос выполнен. Оталось попыток " + str(paid_requests_count))
                # От сюда идёт не мой код.
                # If address exists (search result (rows) is not empty):
                #   get filtered and formatted info about the house
                # If address has company (first_row["company_name"] is not None)
                #   get filtered and formatted info about the company also
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
            else:
                bot.send_message(chat_id, "DEBUG: Ваши попытки кончились")
        else:
            user_info = {'chat_id': chat_id, 'date': str(date.today()), 'paid_requests_count': 10}
            ydb_session._write_db_user(user_info)
            bot.send_message(chat_id, "DEBUG: Ты устарел, обновляем тебя, теперь у тебя 10 попыток")
    else:
        user_info = {'chat_id': chat_id, 'date': str(date.today()), 'paid_requests_count': 10}
        ydb_session._write_db_user(user_info)
        bot.send_message(chat_id, "DEBUG: Нет пользователя, но мы его запишем. Твой ID " + str(chat_id))
        provide_address_info_to_user(chat_id, text)

# Main command handler for tasks above
def solve_task(chat_id, text):
    if "/ping" in text:
        pong(chat_id)
    elif "/help" in text:
        show_help(chat_id)
    elif "/update" in text:
        update_database(chat_id)
    else:
        provide_address_info_to_user(chat_id, text)
