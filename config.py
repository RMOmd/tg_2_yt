
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "./data/sessions/telethon.session")

    # теперь это список каналов, а не одна строка
    TG_CHANNELS = [c.strip() for c in os.getenv("TG_CHANNELS", "").split(",") if c.strip()]
    TG_NOTIFY_BOT_TOKEN = os.getenv("TG_NOTIFY_BOT_TOKEN", "")
    TG_NOTIFY_CHAT_ID = os.getenv("TG_NOTIFY_CHAT_ID", "")

    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./data/downloads")
    DB_PATH = os.getenv("DB_PATH", "./data/db.sqlite3")
    LOG_PATH = os.getenv("LOG_PATH", "./data/tg2yt.log")

    YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "./client_secrets.json")
    YOUTUBE_TOKEN = os.getenv("YOUTUBE_TOKEN", "./data/tokens/token.json")
    YOUTUBE_UPLOAD_PRIVACY = os.getenv("YOUTUBE_UPLOAD_PRIVACY", "private")

    MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "100"))

settings = Settings()
