"""Демо-данные: python -m api.seed  (можно запускать повторно, дубликаты не создаются)."""
from datetime import date, timedelta

from sqlalchemy import select

from common.db import SessionLocal, init_db
from common.config import env
from common.models import Assignment, Employee, License, Software, User
from common.security import hash_password

SOFTWARE = [
    ("Microsoft Office 365", "Microsoft", "Офис"),
    ("JetBrains All Products", "JetBrains", "Разработка"),
    ("MATLAB", "MathWorks", "Инженерия"),
    ("Adobe Photoshop", "Adobe", "Дизайн"),
    ("Kaspersky Endpoint Security", "Лаборатория Касперского", "Безопасность"),
    ("1С:Предприятие", "1С", "Учёт"),
]
EMPLOYEES = [
    ("Иванов Иван Иванович", "Разработка", "ivanov@example.com"),
    ("Петрова Мария Сергеевна", "Дизайн", "petrova@example.com"),
    ("Сидоров Алексей Павлович", "Разработка", "sidorov@example.com"),
    ("Кузнецова Елена Андреевна", "Бухгалтерия", "kuznetsova@example.com"),
    ("Смирнов Дмитрий Олегович", "Инженерия", "smirnov@example.com"),
    ("Попова Ольга Викторовна", "Бухгалтерия", "popova@example.com"),
    ("Волков Сергей Николаевич", "ИТ-отдел", "volkov@example.com"),
]


def main() -> None:
    init_db()
    today = date.today()
    with SessionLocal() as db:
        if db.scalar(select(Software).limit(1)):
            print("Демо-данные уже есть, пропускаю")
            return
        sw = {n: Software(name=n, vendor=v, category=c) for n, v, c in SOFTWARE}
        db.add_all(sw.values())
        emp = [Employee(full_name=n, department=d, email=e) for n, d, e in EMPLOYEES]
        db.add_all(emp)
        db.flush()
        # (ПО, тип, мест, покупка, дней до конца, стоимость, договор, ключ)
        rows = [
            ("Microsoft Office 365", "subscription", 10, -200, 165, 85000, "Д-2026/14", "OFF3-6SUB-X9Q2-AB12"),
            ("JetBrains All Products", "per_user", 3, -350, 15, 54000, "Д-2025/77", "JB-PER-USR-7781-CD34"),
            ("MATLAB", "floating", 2, -400, -10, 190000, "Д-2025/31", "ML-FLOAT-4412-EF56"),
            ("Adobe Photoshop", "subscription", 2, -100, 20, 42000, "Д-2026/05", "PS-SUB-9921-GH78"),
            ("Kaspersky Endpoint Security", "subscription", 50, -30, 335, 120000, "Д-2026/22", "KES-5050-1234-IJ90"),
            ("1С:Предприятие", "perpetual", 5, -900, None, 150000, "Д-2023/09", "1C-PERP-0005-KL12"),
        ]
        lics = []
        for name, typ, seats, buy, left, cost, contract, key in rows:
            lic = License(
                software_id=sw[name].id, license_type=typ, seats=seats,
                purchase_date=today + timedelta(days=buy),
                expiry_date=None if left is None else today + timedelta(days=left),
                cost=cost, contract=contract, license_key=key,
            )
            db.add(lic)
            lics.append(lic)
        db.flush()
        # Выдаём: Office на 6 человек, JetBrains на все 3 места, Photoshop 2 из 2, 1С двоим
        plan = {0: [0, 1, 2, 3, 4, 5], 1: [0, 2, 4], 3: [1, 4], 5: [3, 5]}
        for li, emp_ids in plan.items():
            for ei in emp_ids:
                db.add(Assignment(license_id=lics[li].id, employee_id=emp[ei].id))
        # Демо-пользователь с правом чтения
        if not db.scalar(select(User).where(User.username == "viewer")):
            db.add(User(username="viewer", role="viewer", password_hash=hash_password(env("VIEWER_PASSWORD", "viewer123"))))
        db.commit()
    print("Демо-данные созданы (пользователь viewer, пароль из VIEWER_PASSWORD или viewer123)")


if __name__ == "__main__":
    main()
