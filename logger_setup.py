import logging
from logging.handlers import RotatingFileHandler
import requests
from config import settings


class TelegramLogHandler(logging.Handler):
    """Отправляет логи в Telegram через Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                data={"chat_id": self.chat_id, "text": f"⚠️ {log_entry}"},
                timeout=5,
            )
        except Exception:
            # Не ломаем основной процесс логирования при ошибке сети
            pass


def setup_logger():
    logger = logging.getLogger("tg2yt")
    logger.setLevel(logging.ERROR)

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    # Консоль
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # Файл
    fh = RotatingFileHandler(settings.LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Telegram — только для ошибок и критических логов
    if settings.TG_NOTIFY_BOT_TOKEN and settings.TG_NOTIFY_CHAT_ID:
        th = TelegramLogHandler(settings.TG_NOTIFY_BOT_TOKEN, settings.TG_NOTIFY_CHAT_ID)
        th.setLevel(logging.ERROR)
        th.setFormatter(fmt)
        logger.addHandler(th)

    return logger


logger = setup_logger()
