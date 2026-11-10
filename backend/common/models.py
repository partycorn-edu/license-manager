"""Модели данных (таблицы)."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

LICENSE_TYPES = ("perpetual", "subscription", "per_user", "floating")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="viewer")  # admin или viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Software(Base):
    __tablename__ = "software"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    vendor: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    licenses: Mapped[list["License"]] = relationship(back_populates="software")


class License(Base):
    __tablename__ = "licenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    software_id: Mapped[int] = mapped_column(ForeignKey("software.id"))
    license_type: Mapped[str] = mapped_column(String(20))
    seats: Mapped[int] = mapped_column(Integer)
    purchase_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    contract: Mapped[str] = mapped_column(String(255), default="")
    license_key: Mapped[str] = mapped_column(String(255), default="")
    software: Mapped[Software] = relationship(back_populates="licenses")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="license", cascade="all, delete-orphan"
    )


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80), default="")
    email: Mapped[str] = mapped_column(String(120), unique=True)
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("license_id", "employee_id", name="uq_license_employee"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    license: Mapped[License] = relationship(back_populates="assignments")
    employee: Mapped[Employee] = relationship(back_populates="assignments")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # expiring, expired, seats_full, overuse
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
