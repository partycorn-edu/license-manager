import os

# Настройки до импорта приложения: SQLite в памяти и тестовый секрет
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["REDIS_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app as api_app  # noqa: E402
from auth.main import app as auth_app  # noqa: E402
from common.db import SessionLocal, engine  # noqa: E402
from common.models import Base, User  # noqa: E402
from common.security import hash_password  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Чистая БД и два пользователя перед каждым тестом."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(username="admin", role="admin", password_hash=hash_password("adminpass")))
        db.add(User(username="viewer", role="viewer", password_hash=hash_password("viewerpass")))
        db.commit()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def api():
    return TestClient(api_app)


@pytest.fixture
def auth():
    return TestClient(auth_app)


def login(auth_client, username, password):
    r = auth_client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(auth):
    return login(auth, "admin", "adminpass")


@pytest.fixture
def viewer_h(auth):
    return login(auth, "viewer", "viewerpass")
