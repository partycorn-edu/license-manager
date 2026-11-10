from tests.conftest import login


def test_login_ok(auth):
    r = auth.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin" and body["access_token"]


def test_login_wrong_password(auth):
    r = auth.post("/auth/login", json={"username": "admin", "password": "bad"})
    assert r.status_code == 401


def test_me_requires_token(auth, admin_h):
    assert auth.get("/auth/me").status_code == 401
    assert auth.get("/auth/me", headers=admin_h).json() == {"username": "admin", "role": "admin"}


def test_admin_manages_users(auth, admin_h):
    r = auth.post("/auth/users", json={"username": "newuser", "password": "secret1", "role": "viewer"}, headers=admin_h)
    assert r.status_code == 201
    uid = r.json()["id"]
    assert auth.post("/auth/users", json={"username": "newuser", "password": "secret1"}, headers=admin_h).status_code == 409
    login(auth, "newuser", "secret1")
    # отключённый пользователь войти не может
    auth.put(f"/auth/users/{uid}", json={"is_active": False}, headers=admin_h)
    r = auth.post("/auth/login", json={"username": "newuser", "password": "secret1"})
    assert r.status_code == 401


def test_viewer_cannot_manage_users(auth, viewer_h):
    assert auth.get("/auth/users", headers=viewer_h).status_code == 403
    r = auth.post("/auth/users", json={"username": "x" * 5, "password": "secret1"}, headers=viewer_h)
    assert r.status_code == 403


def test_admin_cannot_delete_self(auth, admin_h):
    me_id = next(u["id"] for u in auth.get("/auth/users", headers=admin_h).json() if u["username"] == "admin")
    assert auth.delete(f"/auth/users/{me_id}", headers=admin_h).status_code == 409
