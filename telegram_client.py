import os
from telethon import TelegramClient, events, types
from telethon.tl.types import DocumentAttributeVideo
from config import settings
from logger_setup import logger
from db import already_uploaded, record_upload, SessionLocal, UploadedVideo
from youtube_client import YouTubeUploader
from telegram_notify import TelegramNotifier


def ensure_dirs():
    os.makedirs(os.path.dirname(settings.TELEGRAM_SESSION), exist_ok=True)
    os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)


ensure_dirs()


class TGClient:
    def __init__(self):
        self.client = TelegramClient(
            settings.TELEGRAM_SESSION,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        self.channel_entities = []
        self.yt = YouTubeUploader()
        self.notifier = TelegramNotifier()

    async def start(self):
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Telethon started as {me.username or me.first_name}")
        await self.notifier.send_message(f"Telethon started as {me.username or me.first_name}")

        if not settings.TG_CHANNELS:
            raise ValueError("TG_CHANNELS not set in config")

        for channel in settings.TG_CHANNELS:
            try:
                entity = await self.client.get_entity(channel)
                self.channel_entities.append(entity)
                logger.info(f"✅ Listening to channel: {getattr(entity, 'title', channel)}")
                await self.notifier.send_message(f"✅ Listening to channel: {getattr(entity, 'title', channel)}")
            except Exception as e:
                logger.error(f"❌ Failed to load channel {channel}: {e}")

        @self.client.on(events.NewMessage(chats=self.channel_entities))
        async def handler(event: events.NewMessage.Event):
            try:
                await self._on_message(event.message)
            except Exception as e:
                logger.exception("Error handling message: %s", e)
                await self.notifier.send_message(f"❌ Ошибка обработки сообщения: {e}")

    async def _on_message(self, message: types.Message):
        """Обрабатывает ТОЛЬКО видео из Telegram."""
        if not message.media:
            return

        chat_id = getattr(message.peer_id, "channel_id", str(settings.TG_CHANNELS[0]))
        if already_uploaded(message.id, chat_id):
            logger.info(f"Message {message.id} in {chat_id} already processed — skipping")
            return

        # --- Определяем, видео ли это ---
        is_video = False
        filename = None

        # 1️⃣ Обычное видео
        if getattr(message, "video", None):
            is_video = True
            filename = f"tg_{message.id}.mp4"

        # 2️⃣ Документ с атрибутом видео
        elif getattr(message.media, "document", None):
            doc = message.media.document
            for attr in getattr(doc, "attributes", []):
                if isinstance(attr, DocumentAttributeVideo):
                    is_video = True
                    filename = f"tg_{message.id}.mp4"
                    break

        # Если не видео — выходим
        if not is_video:
            logger.info(f"Message {message.id} ignored (not a video)")
            return

        post_text = message.message or message.text or ""
        out_path = os.path.join(settings.DOWNLOAD_DIR, filename)

        steps = [f"✉️ Найдено новое видео: {filename}"]

        # --- Скачиваем ---
        try:
            await self.client.download_media(message.media, file=out_path)
            steps.append(f"⬇️ Скачано: {out_path}")
        except Exception as e:
            steps.append(f"❌ Ошибка при скачивании: {e}")
            logger.exception("Download failed: %s", e)
            await self.notifier.send_message("\n".join(steps))
            return

        # --- Загружаем на YouTube ---
        yt_id = None
        hashtags = "#paintedclothes #bodypaint #bikini #blonde"
        base_title = (post_text.split("\n")[0] if post_text else filename)[:70]
        title = f"{base_title} {hashtags}"
        description = f"{post_text}\n\n{hashtags}" if post_text else hashtags

        try:
            steps.append(f"🔼 Начинаю загрузку на YouTube: {filename} {hashtags}")
            vid = await self.yt.upload_async(out_path, title, description)
            if vid:
                yt_id = vid
                steps.append(f"✅ Загружено на YouTube\n📺 ID: {yt_id}\n🔗 https://youtu.be/{yt_id}")
            else:
                steps.append("⚠️ Загрузка пропущена (YouTube вернул None)")
        except Exception as e:
            steps.append(f"❌ Ошибка загрузки на YouTube: {e}")
            logger.exception("Upload error: %s", e)

        # --- Удаляем после загрузки ---
        if yt_id:
            try:
                os.remove(out_path)
                steps.append(f"🗑️ Удалено локально: {filename}")
            except Exception as e:
                steps.append(f"⚠️ Не удалось удалить файл: {e}")

        await self.notifier.send_message("\n".join(steps))

    async def run_forever(self):
        await self.start()
        logger.info("TG client connected and running.")
        await self.client.run_until_disconnected()
