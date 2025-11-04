import os
import json
import time
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import ResumableUploadError
from concurrent.futures import ThreadPoolExecutor
from config import settings
from logger_setup import logger
from notify_handler import TelegramLogHandler  # добавлено

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


class YouTubeUploader:
    SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")

    def __init__(self, client_secrets_file=None, token_file=None):
        self.client_secrets_file = client_secrets_file or settings.YOUTUBE_CLIENT_SECRETS
        self.token_file = token_file or settings.YOUTUBE_TOKEN
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        self.creds = None
        self.service = None
        self._init_creds()
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Telegram уведомления
        self.tg_handler = TelegramLogHandler(
            token=settings.TG_NOTIFY_BOT_TOKEN,
            chat_id=settings.TG_NOTIFY_CHAT_ID,
        )

    def _init_creds(self):
        if os.path.exists(self.token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception:
                logger.exception("Failed to load credentials from token file")
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    logger.exception("Failed to refresh credentials")
                    self.creds = None
            else:
                logger.info("Starting OAuth flow for YouTube credentials (follow instructions).")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(self.creds.to_json())

        self.service = build("youtube", "v3", credentials=self.creds)

    def _build_request_body(self, title: str, description: str, privacy: str):
        return {
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy}
        }

    def _notify(self, message: str):
        """Отправка уведомления в Telegram через handler."""
        record = logging.LogRecord(
            name="YouTubeUploader",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=message,
            args=None,
            exc_info=None
        )
        self.tg_handler.emit(record)

    def upload(self, file_path: str, title: str, description: str, privacy: str = None, chunk_size: int = 256 * 1024):
        """Blocking upload call (runs in thread). Returns uploaded video id on success."""
        if not file_path.lower().endswith(self.SUPPORTED_EXTENSIONS):
            logger.warning(f"⛔ Unsupported media type, skipping: {file_path}")
            return None

        if privacy is None:
            privacy = settings.YOUTUBE_UPLOAD_PRIVACY

        title = (title or "")[:settings.MAX_TITLE_LENGTH]
        body = self._build_request_body(title, description or "", privacy)
        media = MediaFileUpload(file_path, chunksize=chunk_size, resumable=True)
        request = self.service.videos().insert(part="snippet,status", body=body, media_body=media)
        retry = 0
        max_retries = 5

        # msg = f"🎬 Начата загрузка видео: {title}"
        # logger.info(msg)
        # self._notify(msg)

        while True:
            try:
                status, response = request.next_chunk()
                if response:
                    video_id = response.get("id")
                    # msg = f"✅ Видео успешно загружено: {title}\nYouTube ID: {video_id}"
                    # logger.info(msg)
                    # self._notify(msg)
                    return video_id
            except ResumableUploadError as e:
                if "Media type" in str(e):
                    msg = f"⚠️ Пропущен неподдерживаемый файл: {file_path}"
                    logger.warning(msg)
                    self._notify(msg)
                    return None
                raise
            except Exception as e:
                retry += 1
                msg = f"❌ Ошибка при загрузке видео '{title}': {e}"
                logger.exception(msg)
                self._notify(msg)

                if retry > max_retries:
                    final_msg = f"🚨 Превышено число попыток загрузки видео '{title}' — прекращено."
                    logger.error(final_msg)
                    self._notify(final_msg)
                    raise
                sleep_time = 2 ** retry
                logger.info(f"Повторная попытка через {sleep_time}s (попытка {retry}/{max_retries})")
                time.sleep(sleep_time)

    async def upload_async(self, file_path: str, title: str, description: str, privacy: str = None):
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.upload, file_path, title, description, privacy)
