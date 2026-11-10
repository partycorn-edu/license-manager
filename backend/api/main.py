"""Сервис лицензий (api)."""
import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException
from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text

from api.routers import router
from common.config import settings
from common.db import SessionLocal, engine, init_db
from common.logic import build_dashboard
from common.models import Notification

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Licenses API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
@app.get("/api/health")  # второй адрес нужен, чтобы проверять сервис через gateway
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "БД недоступна")
    return {"status": "ok", "service": "api"}


class LicenseCollector:
    """Свои метрики. Считаются в момент запроса /metrics (раз в 15 секунд от Prometheus)."""

    def collect(self):
        try:
            with SessionLocal() as db:
                d = build_dashboard(db, date.today(), settings.expiry_warn_days)
                unread = db.scalar(select(func.count()).select_from(Notification).where(Notification.is_read.is_(False)))
        except Exception:
            return  # если БД недоступна, просто не отдаём свои метрики
        values = [
            ("lic_licenses_expiring_soon", "Лицензий, срок которых скоро истекает", len(d["expiring"])),
            ("lic_licenses_expired", "Просроченных лицензий", len(d["expired"])),
            ("lic_licenses_overused", "Лицензий с перерасходом мест", len(d["overused"])),
            ("lic_seats_total", "Всего мест по действующим лицензиям", d["seats_total"]),
            ("lic_seats_used", "Занято мест", d["seats_used"]),
            ("lic_seats_utilization_percent", "Загрузка мест, %", d["utilization_percent"]),
            ("lic_notifications_unread", "Непрочитанных уведомлений", unread or 0),
        ]
        for name, doc, value in values:
            yield GaugeMetricFamily(name, doc, value=value)


REGISTRY.register(LicenseCollector())
Instrumentator(excluded_handlers=["/metrics", "/health", "/api/health"]).instrument(app).expose(
    app, include_in_schema=False
)
