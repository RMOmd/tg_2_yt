import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

Base = declarative_base()
engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False  # можно включить True для отладки SQL
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class UploadedVideo(Base):
    __tablename__ = "uploaded_videos"

    id = Column(Integer, primary_key=True, index=True)
    tg_message_id = Column(Integer, nullable=False)  # используем INTEGER, чтобы совпадал с Telegram ID
    tg_chat = Column(Integer, nullable=False)        # используем INTEGER для chat_id
    tg_post_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    yt_video_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tg_message_id', 'tg_chat', name='uix_message_chat'),
    )


def init_db():
    """Создание таблиц, если их нет"""
    Base.metadata.create_all(bind=engine)


def record_upload(tg_message_id: int, tg_chat: int, post_text: str, path: str, yt_video_id: str | None = None):
    s = SessionLocal()
    try:
        # Проверяем, есть ли запись
        existing = s.query(UploadedVideo).filter_by(tg_message_id=int(tg_message_id),
                                                    tg_chat=int(tg_chat)).first()
        if existing:
            # Обновляем yt_video_id и путь, если уже есть
            existing.yt_video_id = yt_video_id
            existing.file_path = path
            existing.tg_post_text = post_text or ""
            s.commit()
            return existing

        # Если нет — создаём новую запись
        item = UploadedVideo(
            tg_message_id=int(tg_message_id),
            tg_chat=int(tg_chat),
            tg_post_text=post_text or "",
            file_path=path,
            yt_video_id=yt_video_id
        )
        s.add(item)
        s.commit()
        return item
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def already_uploaded(tg_message_id: int, tg_chat: int) -> bool:
    """
    Проверяет, было ли сообщение уже загружено.
    Работает только по базе данных, без файлов и кеша.
    """
    s = SessionLocal()
    try:
        # Явное сравнение как INTEGER
        exists = s.query(UploadedVideo).filter_by(
            tg_message_id=int(tg_message_id),
            tg_chat=int(tg_chat)
        ).first() is not None
        return exists
    finally:
        s.close()
