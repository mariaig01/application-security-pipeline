import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from appsec_pipeline import create_app
from appsec_pipeline.db import get_db
from appsec_pipeline.models import Document, User
from appsec_pipeline.passwords import hash_password

TEST_PASSWORD = "Only-in-tests-password-2026!"


@pytest.fixture(scope="session")
def database_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set TEST_DATABASE_URL or use docker compose -f compose.test.yaml up --build")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg" or not (parsed.database or "").endswith("_test"):
        pytest.fail("Tests require PostgreSQL and a database name ending in _test")
    # Only this unpredictable test-owned schema is created/dropped; no shared data is truncated.
    schema = f"test_{uuid4().hex}"
    control = create_engine(url, hide_parameters=True)
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, hide_parameters=True, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        with engine.begin() as connection:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def app(database_engine, password_hash):
    connection = database_engine.connect()
    transaction = connection.begin()
    application = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SECRET_KEY": "test-only-session-secret-at-least-32-characters",
            "DATABASE_URL": database_engine.url,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    application.extensions["db_session_factory"] = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        with application.app_context():
            db = get_db()
            users = {
                name: User(username=name, password_hash=password_hash, role=role)
                for name, role in (("alice", "user"), ("bob", "user"), ("admin", "admin"))
            }
            db.add_all(users.values())
            db.flush()
            documents = {
                name: Document(
                    owner_id=user.id, title=f"Private {name}", content=f"Secret belonging to {name}"
                )
                for name, user in users.items()
            }
            db.add_all(documents.values())
            db.commit()
            application.config["TEST_USERS"] = {name: str(u.id) for name, u in users.items()}
            application.config["TEST_DOCUMENTS"] = {
                name: str(d.id) for name, d in documents.items()
            }
        yield application
    finally:
        transaction.rollback()
        connection.close()
        application.extensions["db_engine"].dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_headers(client):
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRFToken": response.json["csrf_token"]}


@pytest.fixture
def login(app):
    def login_as(username):
        client = app.test_client()
        response = client.post(
            "/auth/login",
            headers=csrf_headers(client),
            json={"username": username, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        return client

    return login_as
