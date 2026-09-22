from uuid import uuid4

import pytest

from tests.conftest import csrf_headers


def test_owner_crud(login, app):
    client = login("alice")
    response = client.post(
        "/documents",
        headers=csrf_headers(client),
        json={"title": "My notes", "content": "Private text"},
    )
    assert response.status_code == 201
    document = response.json["document"]
    assert document["owner_id"] == app.config["TEST_USERS"]["alice"]
    path = response.headers["Location"]
    assert client.get(path).json["document"] == document
    assert document in client.get("/documents").json["items"]
    updated = client.patch(path, headers=csrf_headers(client), json={"content": "Revised"})
    assert updated.status_code == 200
    assert updated.json["document"]["content"] == "Revised"
    assert updated.json["document"]["title"] == "My notes"
    assert client.delete(path, headers=csrf_headers(client)).status_code == 204
    assert client.get(path).status_code == 404


def test_cross_user_isolation_read_write_delete_and_list(login, app):
    alice = login("alice")
    bob = login("bob")
    path = f"/documents/{app.config['TEST_DOCUMENTS']['alice']}"
    original = alice.get(path).json
    assert bob.get(path).status_code == 404
    assert (
        bob.patch(path, headers=csrf_headers(bob), json={"title": "Taken over"}).status_code == 404
    )
    assert bob.delete(path, headers=csrf_headers(bob)).status_code == 404
    assert alice.get(path).json == original
    rows = bob.get("/documents").json["items"]
    assert rows and all(row["owner_id"] == app.config["TEST_USERS"]["bob"] for row in rows)
    assert bob.get(path).json == bob.get(f"/documents/{uuid4()}").json


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
@pytest.mark.parametrize("token", [None, "invalid"])
def test_document_mutations_require_csrf(login, app, method, token):
    client = login("alice")
    path = (
        "/documents" if method == "post" else f"/documents/{app.config['TEST_DOCUMENTS']['alice']}"
    )
    headers = {} if token is None else {"X-CSRFToken": token}
    response = getattr(client, method)(path, headers=headers, json={"title": "x", "content": "y"})
    assert response.status_code == 400
    rows = client.get("/documents").json["items"]
    assert len(rows) == 1 and rows[0]["title"] == "Private alice"


def test_csrf_token_is_bound_to_session(login, app):
    alice, bob = login("alice"), login("bob")
    path = f"/documents/{app.config['TEST_DOCUMENTS']['bob']}"
    assert bob.delete(path, headers=csrf_headers(alice)).status_code == 400
    assert bob.get(path).status_code == 200


def test_pagination_is_stable_and_private(login):
    client = login("alice")
    for number in range(3):
        assert (
            client.post(
                "/documents",
                headers=csrf_headers(client),
                json={"title": str(number), "content": ""},
            ).status_code
            == 201
        )
    first = client.get("/documents?per_page=2").json
    second = client.get("/documents?per_page=2&page=2").json
    assert len(first["items"]) == len(second["items"]) == 2
    assert first["has_next"] is True and second["has_next"] is False
    assert {row["id"] for row in first["items"]}.isdisjoint(row["id"] for row in second["items"])


def test_text_is_returned_as_json_without_html_interpretation(login):
    client = login("alice")
    text = "<script>alert('test')</script> '; DROP TABLE documents; --"
    created = client.post(
        "/documents", headers=csrf_headers(client), json={"title": "Text", "content": text}
    )
    assert created.status_code == 201
    response = client.get(created.headers["Location"])
    assert response.json["document"]["content"] == text
    assert response.mimetype == "application/json"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/documents").status_code == 200
