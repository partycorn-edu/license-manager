from datetime import date, timedelta

import jwt

TODAY = date.today()


def mk_software(api, h, name="Office"):
    r = api.post("/api/software", json={"name": name, "vendor": "MS", "category": "Офис"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def mk_license(api, h, sw_id, seats=2, **extra):
    body = {
        "software_id": sw_id, "license_type": "subscription", "seats": seats,
        "purchase_date": str(TODAY), "expiry_date": str(TODAY + timedelta(days=100)),
        "cost": "1000", "license_key": "ABCD-1234-WXYZ",
    }
    body.update(extra)
    r = api.post("/api/licenses", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def mk_employee(api, h, n):
    r = api.post("/api/employees", json={"full_name": f"Сотрудник {n}", "email": f"e{n}@x.ru"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_requires_auth(api):
    assert api.get("/api/software").status_code == 401
    assert api.get("/api/dashboard", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_expired_token_rejected(api):
    token = jwt.encode({"sub": "x", "role": "admin", "exp": 1}, "test-secret", algorithm="HS256")
    assert api.get("/api/software", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(api):
    token = jwt.encode({"sub": "x", "role": "admin"}, "other-secret", algorithm="HS256")
    assert api.get("/api/software", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_viewer_can_read_but_not_write(api, admin_h, viewer_h):
    mk_software(api, admin_h)
    assert api.get("/api/software", headers=viewer_h).status_code == 200
    r = api.post("/api/software", json={"name": "X"}, headers=viewer_h)
    assert r.status_code == 403


def test_key_is_masked(api, admin_h):
    lic_id = mk_license(api, admin_h, mk_software(api, admin_h))
    lic = next(x for x in api.get("/api/licenses", headers=admin_h).json() if x["id"] == lic_id)
    assert lic["license_key_masked"] == "****-WXYZ"
    assert "ABCD" not in str(lic)


def test_seat_limit(api, admin_h):
    lic_id = mk_license(api, admin_h, mk_software(api, admin_h), seats=2)
    emps = [mk_employee(api, admin_h, i) for i in range(3)]
    for e in emps[:2]:
        assert api.post("/api/assignments", json={"license_id": lic_id, "employee_id": e}, headers=admin_h).status_code == 201
    r = api.post("/api/assignments", json={"license_id": lic_id, "employee_id": emps[2]}, headers=admin_h)
    assert r.status_code == 409
    assert "мест нет" in r.json()["detail"]
    # после удаления одного назначения место освобождается
    first = api.get("/api/assignments", headers=admin_h).json()[0]["id"]
    assert api.delete(f"/api/assignments/{first}", headers=admin_h).status_code == 204
    r = api.post("/api/assignments", json={"license_id": lic_id, "employee_id": emps[2]}, headers=admin_h)
    assert r.status_code == 201


def test_duplicate_assignment_rejected(api, admin_h):
    lic_id = mk_license(api, admin_h, mk_software(api, admin_h), seats=5)
    emp = mk_employee(api, admin_h, 1)
    body = {"license_id": lic_id, "employee_id": emp}
    assert api.post("/api/assignments", json=body, headers=admin_h).status_code == 201
    assert api.post("/api/assignments", json=body, headers=admin_h).status_code == 409


def test_cannot_assign_expired_license(api, admin_h):
    sw = mk_software(api, admin_h)
    lic_id = mk_license(api, admin_h, sw, purchase_date=str(TODAY - timedelta(days=60)),
                        expiry_date=str(TODAY - timedelta(days=1)))
    emp = mk_employee(api, admin_h, 1)
    r = api.post("/api/assignments", json={"license_id": lic_id, "employee_id": emp}, headers=admin_h)
    assert r.status_code == 409


def test_cannot_reduce_seats_below_used(api, admin_h):
    sw = mk_software(api, admin_h)
    lic_id = mk_license(api, admin_h, sw, seats=3)
    for i in range(2):
        e = mk_employee(api, admin_h, i)
        api.post("/api/assignments", json={"license_id": lic_id, "employee_id": e}, headers=admin_h)
    body = {"software_id": sw, "license_type": "subscription", "seats": 1,
            "purchase_date": str(TODAY), "expiry_date": str(TODAY + timedelta(days=10))}
    assert api.put(f"/api/licenses/{lic_id}", json=body, headers=admin_h).status_code == 409


def test_license_validation(api, admin_h):
    sw = mk_software(api, admin_h)
    base = {"software_id": sw, "license_type": "subscription", "seats": 1, "purchase_date": str(TODAY)}
    assert api.post("/api/licenses", json=base, headers=admin_h).status_code == 422  # нет даты окончания
    bad = {**base, "expiry_date": str(TODAY - timedelta(days=1))}
    assert api.post("/api/licenses", json=bad, headers=admin_h).status_code == 422
    ok = {**base, "license_type": "perpetual"}  # бессрочной дата окончания не нужна
    assert api.post("/api/licenses", json=ok, headers=admin_h).status_code == 201


def test_license_filters(api, admin_h):
    a, b = mk_software(api, admin_h, "A"), mk_software(api, admin_h, "B")
    mk_license(api, admin_h, a)
    mk_license(api, admin_h, b, expiry_date=str(TODAY + timedelta(days=5)))
    assert len(api.get(f"/api/licenses?software_id={a}", headers=admin_h).json()) == 1
    exp = api.get("/api/licenses?status=expiring", headers=admin_h).json()
    assert [x["software_name"] for x in exp] == ["B"]


def test_dashboard_endpoint(api, admin_h, viewer_h):
    sw = mk_software(api, admin_h)
    lic_id = mk_license(api, admin_h, sw, seats=4)
    mk_license(api, admin_h, sw, seats=2, expiry_date=str(TODAY + timedelta(days=3)))
    e = mk_employee(api, admin_h, 1)
    api.post("/api/assignments", json={"license_id": lic_id, "employee_id": e}, headers=admin_h)
    d = api.get("/api/dashboard", headers=viewer_h).json()
    assert d["seats_total"] == 6 and d["seats_used"] == 1 and d["seats_free"] == 5
    assert len(d["expiring"]) == 1


def test_delete_software_with_licenses_blocked(api, admin_h):
    sw = mk_software(api, admin_h)
    mk_license(api, admin_h, sw)
    assert api.delete(f"/api/software/{sw}", headers=admin_h).status_code == 409


def test_health_and_metrics(api):
    assert api.get("/health").json()["status"] == "ok"
    text = api.get("/metrics").text
    assert "lic_seats_total" in text and "lic_licenses_expiring_soon" in text
