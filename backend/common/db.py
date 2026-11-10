"""Подключение к БД и одноразовая инициализация схемы."""
import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common.config import settings

log = logging.getLogger("db")

if settings.database_url.startswith("sqlite"):
    # SQLite нужен только для тестов
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Маленький пул, чтобы не есть память на слабом VPS
    engine = create_engine(settings.database_url, pool_size=3, max_overflow=2, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

LOCK_ID = 727001  # произвольный номер advisory lock


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Ждёт БД и создаёт таблицы. Advisory lock не даёт нескольким репликам
    создавать таблицы одновременно: остальные ждут и видят уже готовую схему."""
    from common import models

    is_pg = engine.dialect.name == "postgresql"
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                if is_pg:
                    conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": LOCK_ID})
                try:
                    models.Base.metadata.create_all(bind=conn)
                    conn.commit()
                finally:
                    if is_pg:
                        conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                        conn.commit()
            log.info("БД готова")
            return
        except Exception as exc:  # БД ещё стартует
            log.warning("БД недоступна (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Не удалось подключиться к БД")
