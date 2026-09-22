from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from appsec_pipeline import create_app
from appsec_pipeline.db import get_db
from appsec_pipeline.models import Document, User


def test_health_and_security_headers(client):
    response = client.get("/health")
    assert response.status_code == 200 and response.json == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in response.headers


def test_health_database_failure_has_no_details(client, monkeypatch):
    def fail(*args, **kwargs):
        raise OperationalError("secret SQL", {}, Exception("secret database password"))

    monkeypatch.setattr("sqlalchemy.orm.Session.execute", fail)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json == {"status": "unavailable"}


def test_unexpected_error_is_generic(client, app, caplog):
    def fail():
        raise RuntimeError("secret document content and credentials")

    app.add_url_rule("/test-error", view_func=fail)
    response = client.get("/test-error")
    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    assert "secret" not in response.get_data(as_text=True)
    assert "secret" not in caplog.text


def test_database_error_is_generic(client, app, caplog):
    def fail():
        raise OperationalError("INSERT secret SQL", {}, Exception("private content"))

    app.add_url_rule("/test-db-error", view_func=fail)
    response = client.get("/test-db-error")
    assert response.status_code == 503
    assert response.json["error"]["code"] == "service_unavailable"
    assert "private" not in response.get_data(as_text=True) + caplog.text


def test_untrusted_host_rejected(client):
    assert client.get("/health", headers={"Host": "attacker.example"}).status_code == 400


def test_missing_secret_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_cookie_configuration(database_engine, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    app = create_app(
        {
            "SECRET_KEY": "test-only-secret-for-production-config",
            "DATABASE_URL": database_engine.url,
        }
    )
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["DEBUG"] is False
    response = app.test_client().get("/auth/csrf", base_url="https://localhost")
    assert "Secure" in response.headers["Set-Cookie"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    app.extensions["db_engine"].dispose()


def test_migration_matches_models_and_upgrade_is_repeatable(database_engine):
    with database_engine.begin() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.check(config)


def test_cli_creates_normal_user_and_admin_explicitly(app):
    runner = app.test_cli_runner()
    for name, options in (("new_user", []), ("new_admin", ["--admin"])):
        result = runner.invoke(
            args=["create-user", "--username", name, "--generate-password", *options]
        )
        assert result.exit_code == 0
        assert "Password (shown once):" in result.output
    with app.app_context():
        db = get_db()
        assert db.scalar(select(User).where(User.username == "new_user")).role == "user"
        assert db.scalar(select(User).where(User.username == "new_admin")).role == "admin"
    duplicate = runner.invoke(args=["create-user", "--username", "alice", "--generate-password"])
    assert duplicate.exit_code != 0
    assert "Password (shown once):" not in duplicate.output


def test_cli_rejects_short_password(app):
    result = app.test_cli_runner().invoke(
        args=["create-user", "--username", "new_user"], input="short\nshort\n"
    )
    assert result.exit_code != 0
    with app.app_context():
        assert get_db().scalar(select(User).where(User.username == "new_user")) is None


def test_seed_is_development_only_and_preserves_existing_data(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-dev"]).exit_code != 0
    app.config["APP_ENV"] = "development"
    with app.app_context():
        original_hash = get_db().get(User, UUID(app.config["TEST_USERS"]["alice"])).password_hash
    first = runner.invoke(args=["seed-dev"])
    assert first.exit_code == 0
    second = runner.invoke(args=["seed-dev"])
    assert second.exit_code == 0
    assert "Passwords are shown" not in second.output
    with app.app_context():
        db = get_db()
        assert db.scalar(select(func.count()).select_from(User)) == 3
        assert db.scalar(select(func.count()).select_from(Document)) == 6
        assert db.get(User, UUID(app.config["TEST_USERS"]["alice"])).password_hash == original_hash


def test_seed_creates_random_passwords_and_expected_roles(app):
    app.config["APP_ENV"] = "development"
    with app.app_context():
        db = get_db()
        for user in db.scalars(select(User)).all():
            user.username = "existing_" + user.username
        db.commit()
    result = app.test_cli_runner().invoke(args=["seed-dev"])
    assert result.exit_code == 0
    passwords = [
        line.split(": ", 1)[1]
        for line in result.output.splitlines()
        if line.startswith(("alice: ", "bob: ", "admin: "))
    ]
    assert len(set(passwords)) == 3 and all(len(p) >= 15 for p in passwords)
    with app.app_context():
        assert get_db().scalar(select(User).where(User.username == "admin")).role == "admin"


def test_seed_does_not_elevate_existing_user(app):
    app.config["APP_ENV"] = "development"
    with app.app_context():
        db = get_db()
        db.get(User, UUID(app.config["TEST_USERS"]["admin"])).role = "user"
        db.commit()
    result = app.test_cli_runner().invoke(args=["seed-dev"])
    assert result.exit_code != 0
    with app.app_context():
        assert get_db().get(User, UUID(app.config["TEST_USERS"]["admin"])).role == "user"
        assert get_db().scalar(select(func.count()).select_from(Document)) == 3
