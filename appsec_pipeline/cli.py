import secrets
from uuid import NAMESPACE_URL, uuid5

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from appsec_pipeline.db import get_db
from appsec_pipeline.errors import ApiError
from appsec_pipeline.models import Document, User
from appsec_pipeline.passwords import hash_password
from appsec_pipeline.validation import string_field, username_value


@click.command("create-user")
@click.option("--username", required=True)
@click.option("--admin", is_flag=True, help="Grant the explicit administrator role.")
@click.option("--generate-password", is_flag=True, help="Print a random password once.")
@with_appcontext
def create_user(username, admin, generate_password):
    try:
        username = username_value(username)
        password = (
            secrets.token_urlsafe(24)
            if generate_password
            else click.prompt("Password", hide_input=True, confirmation_prompt=True)
        )
        password = string_field(password, "password", 15, 128)
    except ApiError as error:
        raise click.ClickException(error.message) from None
    db = get_db()
    if db.scalar(select(User).where(User.username == username)):
        raise click.ClickException("Username already exists.")
    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role="admin" if admin else "user",
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise click.ClickException("Username already exists.") from None
    click.echo(f"Created {username} ({'admin' if admin else 'user'}).")
    if generate_password:
        click.echo(f"Password (shown once): {password}")


@click.command("seed-dev")
@with_appcontext
def seed_dev():
    if current_app.config["APP_ENV"] != "development":
        raise click.ClickException("seed-dev is available only in development.")
    db = get_db()
    credentials = []
    for username, role in (("alice", "user"), ("bob", "user"), ("admin", "admin")):
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            password = secrets.token_urlsafe(24)
            user = User(username=username, role=role, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            credentials.append((username, password))
        elif user.role != role:
            db.rollback()
            raise click.ClickException("Existing seed user has a different role; no changes made.")
        document_id = uuid5(NAMESPACE_URL, f"appsec-pipeline/seed/{username}")
        if db.get(Document, document_id) is None:
            db.add(
                Document(
                    id=document_id,
                    owner_id=user.id,
                    title=f"Notes for {username}",
                    content="Fictional development document. No real personal data.",
                )
            )
    db.commit()
    click.echo("Development seed complete; existing passwords and documents were preserved.")
    for username, password in credentials:
        click.echo(f"{username}: {password}")
    if credentials:
        click.echo("Passwords are shown only on creation. Store them outside the repository.")


def register_commands(app):
    app.cli.add_command(create_user)
    app.cli.add_command(seed_dev)
