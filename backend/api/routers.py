"""Все эндпоинты сервиса лицензий. Чтение доступно любому вошедшему, изменение только admin."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api import cache
from api.deps import current_user, require_admin
from api.schemas import (
    AssignmentIn, AssignmentOut, EmployeeIn, EmployeeOut, LicenseIn, LicenseOut,
    NotificationOut, SoftwareIn, SoftwareOut,
)
from common.config import settings
from common.db import get_db
from common.logic import build_dashboard, days_left, license_status, usage_map
from common.models import Assignment, Employee, License, Notification, Software

router = APIRouter(prefix="/api")


def mask_key(key: str) -> str:
    if not key:
        return ""
    return "****-" + key[-4:] if len(key) > 4 else "****"


def license_out(lic: License, used: int) -> LicenseOut:
    today = date.today()
    return LicenseOut(
        id=lic.id, software_id=lic.software_id, software_name=lic.software.name,
        license_type=lic.license_type, seats=lic.seats, used=used, free=max(lic.seats - used, 0),
        purchase_date=lic.purchase_date, expiry_date=lic.expiry_date,
        days_left=days_left(lic.expiry_date, today), cost=lic.cost, contract=lic.contract,
        license_key_masked=mask_key(lic.license_key),
        status=license_status(lic.expiry_date, lic.seats, used, today, settings.expiry_warn_days),
    )


def get_or_404(db: Session, model, obj_id: int, what: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, f"{what} не найден(а)")
    return obj


def save(db: Session) -> None:
    """commit с понятной ошибкой при нарушении уникальности."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Такая запись уже существует")
    cache.invalidate()


# ---------- ПО ----------
@router.get("/software", response_model=list[SoftwareOut])
def list_software(db: Session = Depends(get_db), _=Depends(current_user)):
    return db.scalars(select(Software).order_by(Software.name)).all()


@router.post("/software", response_model=SoftwareOut, status_code=201)
def create_software(data: SoftwareIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Software(**data.model_dump())
    db.add(obj)
    save(db)
    return obj


@router.put("/software/{obj_id}", response_model=SoftwareOut)
def update_software(obj_id: int, data: SoftwareIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = get_or_404(db, Software, obj_id, "ПО")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    save(db)
    return obj


@router.delete("/software/{obj_id}", status_code=204)
def delete_software(obj_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = get_or_404(db, Software, obj_id, "ПО")
    if obj.licenses:
        raise HTTPException(409, "У этого ПО есть лицензии, сначала удалите их")
    db.delete(obj)
    save(db)


# ---------- Лицензии ----------
@router.get("/licenses", response_model=list[LicenseOut])
def list_licenses(
    software_id: int | None = None,
    license_type: str | None = None,
    status: str | None = Query(default=None, pattern="^(ok|expiring|expired|overused)$"),
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    query = select(License).order_by(License.id)
    if software_id:
        query = query.where(License.software_id == software_id)
    if license_type:
        query = query.where(License.license_type == license_type)
    used_by = usage_map(db)
    result = [license_out(lic, used_by.get(lic.id, 0)) for lic in db.scalars(query)]
    if status:  # статус считается в Python, он зависит от текущей даты
        result = [x for x in result if x.status == status]
    return result


@router.post("/licenses", response_model=LicenseOut, status_code=201)
def create_license(data: LicenseIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    get_or_404(db, Software, data.software_id, "ПО")
    lic = License(**data.model_dump())
    db.add(lic)
    save(db)
    return license_out(lic, 0)


@router.put("/licenses/{obj_id}", response_model=LicenseOut)
def update_license(obj_id: int, data: LicenseIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    lic = get_or_404(db, License, obj_id, "Лицензия")
    get_or_404(db, Software, data.software_id, "ПО")
    used = usage_map(db).get(lic.id, 0)
    if data.seats < used:
        raise HTTPException(409, f"Нельзя поставить мест меньше, чем уже выдано ({used})")
    for k, v in data.model_dump().items():
        # пустое поле ключа в форме не стирает уже сохранённый ключ
        if k == "license_key" and not v:
            continue
        setattr(lic, k, v)
    save(db)
    return license_out(lic, used)


@router.delete("/licenses/{obj_id}", status_code=204)
def delete_license(obj_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    lic = get_or_404(db, License, obj_id, "Лицензия")
    for n in db.scalars(select(Notification).where(Notification.license_id == lic.id)):
        db.delete(n)
    db.delete(lic)  # назначения удалятся каскадом
    save(db)


# ---------- Сотрудники ----------
@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _=Depends(current_user)):
    return db.scalars(select(Employee).order_by(Employee.full_name)).all()


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(data: EmployeeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Employee(**data.model_dump())
    db.add(obj)
    save(db)
    return obj


@router.put("/employees/{obj_id}", response_model=EmployeeOut)
def update_employee(obj_id: int, data: EmployeeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = get_or_404(db, Employee, obj_id, "Сотрудник")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    save(db)
    return obj


@router.delete("/employees/{obj_id}", status_code=204)
def delete_employee(obj_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    db.delete(get_or_404(db, Employee, obj_id, "Сотрудник"))
    save(db)


# ---------- Назначения ----------
def assignment_out(a: Assignment) -> AssignmentOut:
    return AssignmentOut(
        id=a.id, license_id=a.license_id, software_name=a.license.software.name,
        employee_id=a.employee_id, employee_name=a.employee.full_name, assigned_at=a.assigned_at,
    )


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(
    license_id: int | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    query = select(Assignment).order_by(Assignment.id.desc())
    if license_id:
        query = query.where(Assignment.license_id == license_id)
    if employee_id:
        query = query.where(Assignment.employee_id == employee_id)
    return [assignment_out(a) for a in db.scalars(query)]


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(data: AssignmentIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    # with_for_update блокирует строку лицензии, чтобы два запроса не заняли последнее место одновременно
    lic = db.execute(
        select(License).where(License.id == data.license_id).with_for_update()
    ).scalar_one_or_none()
    if lic is None:
        raise HTTPException(404, "Лицензия не найдена")
    get_or_404(db, Employee, data.employee_id, "Сотрудник")
    if lic.expiry_date and lic.expiry_date < date.today():
        raise HTTPException(409, "Лицензия просрочена")
    used = usage_map(db).get(lic.id, 0)
    if used >= lic.seats:
        raise HTTPException(409, f"Свободных мест нет ({used} из {lic.seats})")
    a = Assignment(license_id=lic.id, employee_id=data.employee_id)
    db.add(a)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Эта лицензия уже выдана сотруднику")
    save(db)
    db.refresh(a)
    return assignment_out(a)


@router.delete("/assignments/{obj_id}", status_code=204)
def delete_assignment(obj_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    db.delete(get_or_404(db, Assignment, obj_id, "Назначение"))
    save(db)


# ---------- Уведомления ----------
@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(unread: bool = False, db: Session = Depends(get_db), _=Depends(current_user)):
    query = select(Notification).order_by(Notification.id.desc()).limit(200)
    if unread:
        query = query.where(Notification.is_read.is_(False))
    return db.scalars(query).all()


@router.post("/notifications/read-all", status_code=204)
def read_all(db: Session = Depends(get_db), _=Depends(require_admin)):
    for n in db.scalars(select(Notification).where(Notification.is_read.is_(False))):
        n.is_read = True
    db.commit()


@router.post("/notifications/{obj_id}/read", status_code=204)
def read_one(obj_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    get_or_404(db, Notification, obj_id, "Уведомление").is_read = True
    db.commit()


# ---------- Дашборд ----------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(current_user)):
    data = cache.get_dashboard()
    if data is None:
        data = build_dashboard(db, date.today(), settings.expiry_warn_days)
        cache.set_dashboard(data)
    return data
