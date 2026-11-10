"""Схемы запросов и ответов API."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LicenseType = Literal["perpetual", "subscription", "per_user", "floating"]
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SoftwareIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    vendor: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=80)


class SoftwareOut(SoftwareIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LicenseIn(BaseModel):
    software_id: int
    license_type: LicenseType
    seats: int = Field(ge=1, le=100000)
    purchase_date: date
    expiry_date: date | None = None
    cost: Decimal = Field(default=Decimal(0), ge=0)
    contract: str = Field(default="", max_length=255)
    license_key: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def check_dates(self):
        if self.license_type != "perpetual" and self.expiry_date is None:
            raise ValueError("Для этого типа лицензии нужна дата окончания")
        if self.expiry_date and self.expiry_date < self.purchase_date:
            raise ValueError("Дата окончания раньше даты покупки")
        return self


class LicenseOut(BaseModel):
    id: int
    software_id: int
    software_name: str
    license_type: str
    seats: int
    used: int
    free: int
    purchase_date: date
    expiry_date: date | None
    days_left: int | None
    cost: Decimal
    contract: str
    license_key_masked: str
    status: str


class EmployeeIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    department: str = Field(default="", max_length=80)
    email: str = Field(pattern=EMAIL_RE, max_length=120)


class EmployeeOut(EmployeeIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AssignmentIn(BaseModel):
    license_id: int
    employee_id: int


class AssignmentOut(BaseModel):
    id: int
    license_id: int
    software_name: str
    employee_id: int
    employee_name: str
    assigned_at: datetime | None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    license_id: int
    message: str
    is_read: bool
    created_at: datetime | None
