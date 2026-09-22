import logging
import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_wtf.csrf import CSRFError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from appsec_pipeline.db import get_db, init_db
from appsec_pipeline.errors import ApiError, error_response
from appsec_pipeline.extensions import csrf, login_manager


def create_app(test_config=None):
    app = Flask(__name__)
    environment = os.environ.get("APP_ENV", "production")
    app.config.from_mapping(
        APP_ENV=environment,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        TRUSTED_HOSTS=[
            host.strip()
            for host in os.environ.get("TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
            if host.strip()
        ],
        SESSION_COOKIE_NAME="appsec_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=environment != "development",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_REFRESH_EACH_REQUEST=False,
        WTF_CSRF_TIME_LIMIT=30 * 60,
        MAX_CONTENT_LENGTH=256 * 1024,
        MAX_FORM_MEMORY_SIZE=256 * 1024,
        MAX_FORM_PARTS=10,
        DEBUG=False,
    )
    if test_config:
        app.config.update(test_config)
    if app.config["APP_ENV"] not in {"development", "testing", "production"}:
        raise RuntimeError("APP_ENV must be development, testing or production")
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 random characters")
    if app.config["APP_ENV"] == "production" and not app.config["SESSION_COOKIE_SECURE"]:
        raise RuntimeError("Production requires secure cookies")
    if not app.config["TRUSTED_HOSTS"]:
        raise RuntimeError("TRUSTED_HOSTS must not be empty")

    init_db(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from appsec_pipeline.admin import admin
    from appsec_pipeline.auth import auth
    from appsec_pipeline.cli import register_commands
    from appsec_pipeline.documents import documents

    app.register_blueprint(auth)
    app.register_blueprint(documents)
    app.register_blueprint(admin)
    register_commands(app)

    @app.get("/health")
    def health():
        try:
            get_db().execute(text("SELECT 1"))
        except SQLAlchemyError:
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok")

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return error_response(error.code, error.message, error.status)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return error_response("csrf_failed", "A valid CSRF token is required.", 400)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        messages = {
            400: "Invalid request.",
            404: "Resource not found.",
            405: "Method not allowed.",
            413: "Request body too large.",
            415: "Content-Type must be application/json.",
        }
        response = error.get_response()
        response.data = app.json.dumps(
            {
                "error": {
                    "code": f"http_{error.code}",
                    "message": messages.get(error.code, "Request rejected."),
                }
            }
        )
        response.content_type = "application/json"
        return response

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        app.logger.error("database_failed error_type=%s", type(error).__name__)
        return error_response("service_unavailable", "Service temporarily unavailable.", 503)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Exception text/SQL parameters may contain passwords or document content.
        app.logger.error("request_failed error_type=%s", type(error).__name__)
        return error_response("internal_error", "Internal server error.", 500)

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "no-referrer"
        if app.config["APP_ENV"] == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    # Flask-WTF INFO messages can echo token failure details; keep logs minimal.
    logging.getLogger("flask_wtf.csrf").setLevel(logging.WARNING)
    return app
