import pytest

from tests.conftest import csrf_headers


@pytest.mark.parametrize("method,collection", [("get", True), ("get", False), ("delete", False)])
def test_normal_user_cannot_administer(login, app, method, collection):
    client = login("alice")
    path = "/admin/documents"
    if not collection:
        path += f"/{app.config['TEST_DOCUMENTS']['alice']}"
    assert getattr(client, method)(path, headers=csrf_headers(client)).status_code == 403


def test_admin_can_read_and_delete_but_cannot_edit_other_documents(login, app, caplog):
    client = login("admin")
    document_id = app.config["TEST_DOCUMENTS"]["alice"]
    admin_path, normal_path = f"/admin/documents/{document_id}", f"/documents/{document_id}"
    assert len(client.get("/admin/documents").json["items"]) == 3
    assert client.get(admin_path).json["document"]["title"] == "Private alice"
    assert client.get(normal_path).status_code == 404
    assert (
        client.patch(normal_path, headers=csrf_headers(client), json={"title": "No"}).status_code
        == 404
    )
    assert client.delete(normal_path, headers=csrf_headers(client)).status_code == 404
    assert (
        client.patch(admin_path, headers=csrf_headers(client), json={"title": "No"}).status_code
        == 405
    )
    assert client.delete(admin_path, headers=csrf_headers(client)).status_code == 204
    assert login("alice").get(normal_path).status_code == 404
    assert "admin_document_deleted" in caplog.text
    assert document_id in caplog.text
    assert "Secret belonging" not in caplog.text


def test_admin_delete_requires_csrf(login, app):
    client = login("admin")
    path = f"/admin/documents/{app.config['TEST_DOCUMENTS']['alice']}"
    assert client.delete(path).status_code == 400
    assert client.get(path).status_code == 200


def test_admin_role_is_read_from_database_on_each_request(login, app):
    from uuid import UUID

    from appsec_pipeline.db import get_db
    from appsec_pipeline.models import User

    client = login("admin")
    assert client.get("/admin/documents").status_code == 200
    with app.app_context():
        user = get_db().get(User, UUID(app.config["TEST_USERS"]["admin"]))
        user.role = "user"
        get_db().commit()
    assert client.get("/admin/documents").status_code == 403
