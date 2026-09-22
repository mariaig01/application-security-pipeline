from uuid import UUID

from flask import Blueprint, jsonify, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select

from appsec_pipeline.db import get_db
from appsec_pipeline.errors import ApiError, error_response
from appsec_pipeline.extensions import login_manager
from appsec_pipeline.models import User
from appsec_pipeline.passwords import dummy_hash, verify_password
from appsec_pipeline.validation import json_object, string_field, username_value

auth = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    try:
        identifier = UUID(user_id)
    except (ValueError, TypeError):
        return None
    return get_db().get(User, identifier)


@login_manager.unauthorized_handler
def unauthorized():
    return error_response("authentication_required", "Authentication is required.", 401)


@auth.get("/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@auth.post("/login")
def login():
    data = json_object({"username", "password"}, {"username", "password"})
    username = username_value(data["username"])
    password = string_field(data["password"], "password", 1, 128)
    user = get_db().scalar(select(User).where(User.username == username))
    valid = verify_password(user.password_hash if user else dummy_hash(), password)
    if not valid or user is None:
        raise ApiError("invalid_credentials", "Invalid username or password.", 401)
    session.clear()
    login_user(user, remember=False, fresh=True)
    session.permanent = True
    return jsonify(user=user.to_dict())


@auth.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return "", 204


@auth.get("/me")
@login_required
def me():
    return jsonify(user=current_user.to_dict())
