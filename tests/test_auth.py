from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from appsec_pipeline.db import get_db
from appsec_pipeline.models import User
from appsec_pipeline.passwords import HASH_METHOD, hash_password, verify_password
from tests.conftest import TEST_PASSWORD, csrf_headers


def test_login_identity_logout(client):
    old_token = csrf_headers(client)
    response = client.post(
        "/auth/login", headers=old_token, json={"username": "alice", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json["user"]["role"] == "user"
    assert "password" not in response.get_data(as_text=True)
    assert client.get("/auth/me").json["user"]["username"] == "alice"
    # Successful login cleared the pre-authentication session/CSRF token.
    assert client.post("/auth/logout", headers=old_token).status_code == 400
    assert client.post("/auth/logout", headers=csrf_headers(client)).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.get("/documents").status_code == 401


def test_invalid_credentials_are_generic(client):
    bodies = []
    for username, password in (("alice", "wrong"), ("nobody", TEST_PASSWORD)):
        response = client.post(
            "/auth/login",
            headers=csrf_headers(client),
            json={"username": username, "password": password},
        )
        assert response.status_code == 401
        bodies.append(response.json)
    assert bodies[0] == bodies[1]
    assert client.get("/documents").status_code == 401


@pytest.mark.parametrize("headers", [{}, {"X-CSRFToken": "invalid"}])
def test_login_requires_csrf(client, headers):
    assert (
        client.post(
            "/auth/login", headers=headers, json={"username": "alice", "password": TEST_PASSWORD}
        ).status_code
        == 400
    )
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/documents"),
        ("post", "/documents"),
        ("get", f"/documents/{uuid4()}"),
        ("patch", f"/documents/{uuid4()}"),
        ("delete", f"/documents/{uuid4()}"),
        ("get", "/auth/me"),
        ("post", "/auth/logout"),
        ("get", "/admin/documents"),
        ("get", f"/admin/documents/{uuid4()}"),
        ("delete", f"/admin/documents/{uuid4()}"),
    ],
)
def test_anonymous_rejected_with_valid_csrf(client, method, path):
    response = getattr(client, method)(path, headers=csrf_headers(client))
    assert response.status_code == 401
    assert response.is_json
    assert "Location" not in response.headers


def test_secure_password_storage(app):
    with app.app_context():
        user = get_db().scalar(select(User).where(User.username == "alice"))
        assert user.password_hash.startswith(HASH_METHOD + "$")
        assert TEST_PASSWORD not in user.password_hash
        assert verify_password(user.password_hash, TEST_PASSWORD)
        assert hash_password(TEST_PASSWORD) != user.password_hash  # independent salt


def test_cookie_flags_and_expiry(client, app):
    response = client.post(
        "/auth/login",
        headers=csrf_headers(client),
        json={"username": "alice", "password": TEST_PASSWORD},
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Expires=" in cookie
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False
    app.config["SESSION_COOKIE_SECURE"] = True
    secure = app.test_client().get("/auth/csrf", base_url="https://localhost")
    assert "Secure" in secure.headers["Set-Cookie"]


def test_tampered_cookie_rejected(login, app):
    client = login("alice")
    name = app.config["SESSION_COOKIE_NAME"]
    value = client.get_cookie(name).value
    # Modify the signature, not JSON, so client-controlled role data is never trusted.
    prefix, signature = value.rsplit(".", 1)
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    client.set_cookie(name, prefix + "." + signature)
    assert client.get("/documents").status_code == 401


def test_session_expiration(login, app, monkeypatch):
    client = login("alice")
    import itsdangerous.timed

    now = itsdangerous.timed.time.time()
    monkeypatch.setattr(itsdangerous.timed.time, "time", lambda: now + 1801)
    assert client.get("/auth/me").status_code == 401


def test_api_cannot_grant_admin(client):
    response = client.post(
        "/auth/login",
        headers=csrf_headers(client),
        json={"username": "alice", "password": TEST_PASSWORD, "role": "admin"},
    )
    assert response.status_code == 400
    assert client.get("/auth/me").status_code == 401
    assert (
        client.post(
            "/auth/register",
            headers=csrf_headers(client),
            json={"username": "evil", "role": "admin"},
        ).status_code
        == 404
    )
