"""Воркер: раз в N секунд проверяет сроки и места, создаёт уведомления (и пишет их в лог)."""
import logging
import pathlib
import time
from datetime import date

from common.config import settings
from common.db import SessionLocal, init_db
from common.logic import run_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")
HEARTBEAT = pathlib.Path("/tmp/worker.alive")  # по этому файлу работает healthcheck


def once() -> int:
    with SessionLocal() as db:
        created = run_checks(db, date.today(), settings.expiry_warn_days)
    log.info("Проверка завершена, новых уведомлений: %s", created)
    return created


def main() -> None:
    init_db()
    log.info("Воркер запущен, интервал %s сек", settings.worker_interval)
    while True:
        try:
            once()
        except Exception:
            log.exception("Ошибка проверки, попробуем в следующий раз")
        HEARTBEAT.touch()
        time.sleep(settings.worker_interval)


if __name__ == "__main__":
    main()
