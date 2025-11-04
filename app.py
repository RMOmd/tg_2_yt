import asyncio
import os
from config import settings
from logger_setup import logger
from db import init_db, already_uploaded, record_upload
from telegram_client import TGClient
from youtube_client import YouTubeUploader

app_state = {}


async def handle_new_video(message, file_path: str, post_text: str, media_type: str):
    """
    Обработчик нового сообщения: загружает видео на YouTube,
    добавляет запись в базу и удаляет локальный файл после успешного аплоада.
    """
    chat_id = getattr(message.peer_id, 'channel_id', str(settings.TG_CHANNELS[0]))

    title_candidate = (post_text.splitlines()[0] if post_text else f"Telegram post {message.id}")[:settings.MAX_TITLE_LENGTH]
    description = post_text

    try:
        yt_id = await app_state["yt"].upload_async(file_path, title_candidate, description, settings.YOUTUBE_UPLOAD_PRIVACY)
        logger.info(f"Uploaded to YouTube: {yt_id}")

        # Записываем в DB только после успешного upload
        record_upload(str(message.id), str(chat_id), post_text, file_path, yt_video_id=yt_id)

        # Удаляем локальный файл после успешного аплоада
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted local file {file_path}")

    except Exception as e:
        logger.exception("Failed to upload video for message %s: %s", message.id, e)
        return

    if already_uploaded(message.id, chat_id):
        logger.info(f"Message {message.id} successfully uploaded and recorded in DB.")


async def main():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
    init_db()
    logger.info("Database initialized")

    tg = TGClient()
    yt = YouTubeUploader()
    app_state["tg"] = tg
    app_state["yt"] = yt

    # tg.add_new_message_handler(handle_new_video)

    await tg.run_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down.")
