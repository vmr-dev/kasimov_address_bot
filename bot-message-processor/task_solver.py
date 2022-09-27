import os

from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")

def solve_echo(chat_id, text):
    bot = Bot(BOT_TOKEN)
    bot.send_message(chat_id, text)

# TODO: Add command handlers