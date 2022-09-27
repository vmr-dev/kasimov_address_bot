from telegram.ext import Updater

WEBHOOK_URL = "YOUR_WEB_HOOK_HERE!!!"
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE!!!"

PORT = "8443"
updater = Updater(BOT_TOKEN)

updater.start_webhook(listen="0.0.0.0",
                      port=int(PORT),
                      url_path=BOT_TOKEN,
                      webhook_url=WEBHOOK_URL)
