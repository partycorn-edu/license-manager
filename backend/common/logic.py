"""Бизнес-логика: срок действия, статусы, дашборд, проверки для воркера.
Лежит в common, чтобы её использовали и api, и worker."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.models import Assignment, License, Notification


def days_left(expiry: date | None, today: date) -> int | None:
    """Сколько дней до окончания. None для бессрочной."""
    return None if expiry is None else (expiry - today).days


def license_flags(expiry: date | None, seats: int, used: int, today: date, warn_days: int) -> dict:
    left = days_left(expiry, today)
    return {
        "expired": left is not None and left < 0,
        "expiring": left is not None and 0 <= left <= warn_days,
        "overused": used > seats,
        "full": used == seats,
    }


def license_status(expiry: date | None, seats: int, used: int, today: date, warn_days: int) -> str:
    f = license_flags(expiry, seats, used, today, warn_days)
    if f["expired"]:
        return "expired"
    if f["overused"]:
        return "overused"
    if f["expiring"]:
        return "expiring"
    return "ok"


def usage_map(db: Session) -> dict[int, int]:
    """license_id -> сколько мест занято."""
    rows = db.execute(select(Assignment.license_id, func.count()).group_by(Assignment.license_id))
    return {license_id: cnt for license_id, cnt in rows}


def build_dashboard(db: Session, today: date, warn_days: int) -> dict:
    used_by = usage_map(db)
    licenses = db.scalars(select(License)).all()
    total = used = 0
    expiring, expired, overused = [], [], []
    for lic in licenses:
        u = used_by.get(lic.id, 0)
        f = license_flags(lic.expiry_date, lic.seats, u, today, warn_days)
        item = {
            "license_id": lic.id,
            "software_name": lic.software.name,
            "expiry_date": lic.expiry_date.isoformat() if lic.expiry_date else None,
            "days_left": days_left(lic.expiry_date, today),
            "seats": lic.seats,
            "used": u,
        }
        if f["expired"]:
            expired.append(item)
            continue  # просроченные не входят в общий подсчёт мест
        total += lic.seats
        used += min(u, lic.seats)
        if f["expiring"]:
            expiring.append(item)
        if f["overused"]:
            overused.append(item)
    expiring.sort(key=lambda x: x["days_left"])
    return {
        "licenses_total": len(licenses),
        "seats_total": total,
        "seats_used": used,
        "seats_free": total - used,
        "utilization_percent": round(used * 100 / total, 1) if total else 0.0,
        "expiring": expiring,
        "expired": expired,
        "overused": overused,
    }


def run_checks(db: Session, today: date, warn_days: int) -> int:
    """Создаёт уведомления. Повторно не создаёт, пока старое не прочитано.
    Возвращает число новых уведомлений."""
    used_by = usage_map(db)
    open_keys = {
        (n.kind, n.license_id)
        for n in db.scalars(select(Notification).where(Notification.is_read.is_(False)))
    }
    created = 0
    for lic in db.scalars(select(License)):
        u = used_by.get(lic.id, 0)
        f = license_flags(lic.expiry_date, lic.seats, u, today, warn_days)
        name = lic.software.name
        left = days_left(lic.expiry_date, today)
        candidates = []
        if f["expired"]:
            candidates.append(("expired", f"Лицензия «{name}» просрочена ({lic.expiry_date})."))
        else:
            if f["expiring"]:
                candidates.append(("expiring", f"Лицензия «{name}» истекает через {left} дн. ({lic.expiry_date})."))
            if f["overused"]:
                candidates.append(("overuse", f"Перерасход по «{name}»: занято {u} из {lic.seats} мест."))
            elif f["full"] and lic.seats > 0:
                candidates.append(("seats_full", f"Свободных мест по «{name}» не осталось ({u} из {lic.seats})."))
        for kind, message in candidates:
            if (kind, lic.id) not in open_keys:
                db.add(Notification(kind=kind, license_id=lic.id, message=message))
                created += 1
    db.commit()
    return created
