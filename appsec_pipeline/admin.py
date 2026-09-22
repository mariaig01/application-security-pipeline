from functools import wraps

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required
from sqlalchemy import select

from appsec_pipeline.db import get_db
from appsec_pipeline.documents import document_page
from appsec_pipeline.errors import ApiError
from appsec_pipeline.models import Document

admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            raise ApiError("forbidden", "Administrator permission is required.", 403)
        return view(*args, **kwargs)

    return wrapped


def any_document(document_id):
    document = get_db().get(Document, document_id)
    if document is None:
        raise ApiError("not_found", "Resource not found.", 404)
    return document


@admin.get("/documents")
@admin_required
def list_documents():
    return document_page(select(Document))


@admin.get("/documents/<uuid:document_id>")
@admin_required
def read_document(document_id):
    return jsonify(document=any_document(document_id).to_dict())


@admin.delete("/documents/<uuid:document_id>")
@admin_required
def delete_document(document_id):
    document = any_document(document_id)
    get_db().delete(document)
    get_db().commit()
    current_app.logger.warning(
        "admin_document_deleted actor_id=%s document_id=%s", current_user.id, document_id
    )
    return "", 204
