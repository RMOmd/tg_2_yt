import aiohttp
from config import settings
import logging


class TelegramNotifier:
    def __init__(self):
        self.token = settings.TG_NOTIFY_BOT_TOKEN
        self.chat_id = settings.TG_NOTIFY_CHAT_ID

    async def send_message(self, text: str):
        if not self.token or not self.chat_id:
            logging.warning("TG_NOTIFY_BOT_TOKEN or TG_NOTIFY_CHAT_ID not set")
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": self.chat_id, "text": text})
