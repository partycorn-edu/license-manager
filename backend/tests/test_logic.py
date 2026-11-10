from datetime import date, timedelta

from common.logic import build_dashboard, days_left, license_status, run_checks
from common.models import Assignment, Employee, License, Notification, Software

TODAY = date(2026, 11, 1)


def test_days_left():
    assert days_left(None, TODAY) is None  # бессрочная
    assert days_left(TODAY + timedelta(days=10), TODAY) == 10
    assert days_left(TODAY - timedelta(days=1), TODAY) == -1


def test_status():
    d = timedelta(days=1)
    assert license_status(None, 5, 5, TODAY, 30) == "ok"
    assert license_status(TODAY + 29 * d, 5, 1, TODAY, 30) == "expiring"
    assert license_status(TODAY + 31 * d, 5, 1, TODAY, 30) == "ok"
    assert license_status(TODAY, 5, 1, TODAY, 30) == "expiring"  # последний день ещё действует
    assert license_status(TODAY - d, 5, 1, TODAY, 30) == "expired"
    assert license_status(None, 2, 3, TODAY, 30) == "overused"


def make(db, name, seats, expiry, used=0):
    sw = Software(name=name)
    lic = License(software=sw, license_type="subscription", seats=seats, purchase_date=TODAY, expiry_date=expiry)
    db.add(lic)
    db.flush()
    for i in range(used):
        emp = Employee(full_name=f"E{name}{i}", email=f"{name}{i}@x.ru")
        db.add(emp)
        db.flush()
        db.add(Assignment(license_id=lic.id, employee_id=emp.id))
    db.commit()
    return lic


def test_dashboard(db):
    make(db, "A", 10, TODAY + timedelta(days=100), used=4)
    make(db, "B", 3, TODAY + timedelta(days=5), used=3)
    make(db, "C", 5, TODAY - timedelta(days=2), used=1)  # просрочена, в итог не идёт
    d = build_dashboard(db, TODAY, 30)
    assert d["seats_total"] == 13
    assert d["seats_used"] == 7
    assert d["seats_free"] == 6
    assert d["utilization_percent"] == 53.8
    assert [x["software_name"] for x in d["expiring"]] == ["B"]
    assert [x["software_name"] for x in d["expired"]] == ["C"]
    assert d["overused"] == []


def test_worker_creates_notifications_once(db):
    make(db, "A", 3, TODAY + timedelta(days=5), used=3)  # скоро истекает и мест нет
    make(db, "B", 3, TODAY - timedelta(days=1))  # просрочена
    assert run_checks(db, TODAY, 30) == 3
    assert run_checks(db, TODAY, 30) == 0  # повторно не дублирует
    kinds = sorted(n.kind for n in db.query(Notification))
    assert kinds == ["expired", "expiring", "seats_full"]
    # после прочтения уведомление можно создать снова
    for n in db.query(Notification):
        n.is_read = True
    db.commit()
    assert run_checks(db, TODAY, 30) == 3
