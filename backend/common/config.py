"""Настройки из переменных окружения.
Секреты можно передать файлом: для NAME читается NAME_FILE (так работают docker secrets)."""
import os
from dataclasses import dataclass

from sqlalchemy.engine import URL


def env(name: str, default: str | None = None) -> str | None:
    path = os.getenv(f"{name}_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return str(env(name, str(default))).lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int
    admin_username: str
    admin_password: str
    redis_enabled: bool
    redis_url: str
    worker_interval: int
    expiry_warn_days: int


def load_settings() -> Settings:
    db_url = env("DATABASE_URL")
    if not db_url:
        db_url = URL.create(
            "postgresql+psycopg2",
            username=env("DB_USER", "licenses"),
            password=env("DB_PASSWORD", ""),
            host=env("DB_HOST", "postgres"),
            port=int(env("DB_PORT", "5432")),
            database=env("DB_NAME", "licenses"),
        ).render_as_string(hide_password=False)
    return Settings(
        database_url=db_url,
        jwt_secret=env("JWT_SECRET", "dev-secret-change-me"),
        jwt_expire_minutes=int(env("JWT_EXPIRE_MINUTES", "60")),
        admin_username=env("ADMIN_USERNAME", "admin"),
        admin_password=env("ADMIN_PASSWORD", "admin"),
        redis_enabled=env_bool("REDIS_ENABLED", False),
        redis_url=env("REDIS_URL", "redis://redis:6379/0"),
        worker_interval=int(env("WORKER_INTERVAL_SECONDS", "60")),
        expiry_warn_days=int(env("EXPIRY_WARN_DAYS", "30")),
    )


settings = load_settings()
