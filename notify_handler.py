import logging
import aiohttp
import asyncio
import os


class TelegramLogHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    async def _send_message(self, text: str):
        """Отправка логов в Telegram."""
        if not self.token or not self.chat_id:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text[:4000]}  # ограничение Telegram
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
        except Exception:
            pass  # не мешаем основному процессу при ошибках

    def emit(self, record: logging.LogRecord):
        """Асинхронно шлёт логи в Telegram."""
        message = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_message(message))
        except RuntimeError:
            # если логгер вызван вне event loop
            asyncio.run(self._send_message(message))
