from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import select

from appsec_pipeline.db import get_db
from appsec_pipeline.errors import ApiError
from appsec_pipeline.models import Document
from appsec_pipeline.validation import document_input, pagination

documents = Blueprint("documents", __name__, url_prefix="/documents")


def own_document(document_id):
    document = get_db().scalar(
        select(Document).where(Document.id == document_id, Document.owner_id == current_user.id)
    )
    if document is None:
        raise ApiError("not_found", "Resource not found.", 404)
    return document


def document_page(query):
    page, per_page = pagination()
    rows = (
        get_db()
        .scalars(query.order_by(Document.id).offset((page - 1) * per_page).limit(per_page + 1))
        .all()
    )
    return jsonify(
        items=[document.to_dict() for document in rows[:per_page]],
        page=page,
        per_page=per_page,
        has_next=len(rows) > per_page,
    )


@documents.get("")
@login_required
def list_documents():
    return document_page(select(Document).where(Document.owner_id == current_user.id))


@documents.post("")
@login_required
def create_document():
    document = Document(owner_id=current_user.id, **document_input())
    get_db().add(document)
    get_db().commit()
    return jsonify(document=document.to_dict()), 201, {"Location": f"/documents/{document.id}"}


@documents.get("/<uuid:document_id>")
@login_required
def read_document(document_id):
    return jsonify(document=own_document(document_id).to_dict())


@documents.patch("/<uuid:document_id>")
@login_required
def update_document(document_id):
    document = own_document(document_id)
    for field, value in document_input(partial=True).items():
        setattr(document, field, value)
    get_db().commit()
    return jsonify(document=document.to_dict())


@documents.delete("/<uuid:document_id>")
@login_required
def delete_document(document_id):
    get_db().delete(own_document(document_id))
    get_db().commit()
    return "", 204
