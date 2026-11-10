"""Сервис авторизации (auth): вход, JWT, управление пользователями."""
import logging
from contextlib import asynccontextmanager
from typing import Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.config import settings
from common.db import SessionLocal, engine, get_db, init_db
from common.models import User
from common.security import create_token, decode_token, hash_password, verify_password

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth")


def create_default_admin() -> None:
    """Если пользователей нет, создаём админа из переменных окружения."""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)) == 0:
            db.add(User(username=settings.admin_username, role="admin",
                        password_hash=hash_password(settings.admin_password)))
            try:
                db.commit()
                log.info("Создан администратор %s", settings.admin_username)
            except IntegrityError:  # другая реплика успела раньше
                db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    create_default_admin()
    yield


app = FastAPI(title="Auth", lifespan=lifespan)
bearer = HTTPBearer(auto_error=False)


class LoginIn(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    role: Literal["admin", "viewer"] = "viewer"


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=100)
    role: Literal["admin", "viewer"] | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    is_active: bool


def token_payload(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(401, "Нужна авторизация")
    try:
        return decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Токен недействителен или просрочен")


def admin_payload(payload: dict = Depends(token_payload)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(403, "Недостаточно прав")
    return payload


@app.get("/health")
@app.get("/auth/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "БД недоступна")
    return {"status": "ok", "service": "auth"}


@app.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return {
        "access_token": create_token(user.id, user.username, user.role),
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
    }


@app.get("/auth/me")
def me(payload: dict = Depends(token_payload)):
    return {"username": payload["sub"], "role": payload["role"]}


@app.get("/auth/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(admin_payload)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.post("/auth/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _=Depends(admin_payload)):
    user = User(username=data.username, role=data.role, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Пользователь с таким именем уже есть")
    return user


@app.put("/auth/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), me=Depends(admin_payload)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == me["uid"] and (data.role == "viewer" or data.is_active is False):
        raise HTTPException(409, "Нельзя лишить прав или отключить самого себя")
    if data.password:
        user.password_hash = hash_password(data.password)
    if data.role:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    return user


@app.delete("/auth/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), me=Depends(admin_payload)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == me["uid"]:
        raise HTTPException(409, "Нельзя удалить самого себя")
    db.delete(user)
    db.commit()


Instrumentator(excluded_handlers=["/metrics", "/health", "/auth/health"]).instrument(app).expose(
    app, include_in_schema=False
)
