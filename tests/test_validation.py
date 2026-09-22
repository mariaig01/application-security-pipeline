import pytest

from tests.conftest import csrf_headers


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "text",
        {},
        {"title": "Missing content"},
        {"title": "   ", "content": ""},
        {"title": "x" * 201, "content": ""},
        {"title": "OK", "content": "x" * 50001},
        {"title": 1, "content": ""},
        {"title": "OK", "content": False},
        {"title": "OK", "content": None},
        {"title": "OK", "content": "\x00"},
        {"title": "OK", "content": {}},
        {"title": "OK", "content": "", "owner_id": "someone-else"},
        {"title": "OK", "content": "", "role": "admin"},
        {"title": "OK", "content": "", "id": "chosen-id"},
    ],
)
def test_reject_invalid_create(login, payload):
    import json

    client = login("alice")
    response = client.post(
        "/documents",
        headers=csrf_headers(client),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.is_json
    assert len(client.get("/documents").json["items"]) == 1


@pytest.mark.parametrize(
    "payload",
    [{}, {"owner_id": "other"}, {"title": ""}, {"content": []}, {"title": "New", "role": "admin"}],
)
def test_invalid_patch_preserves_original(login, app, payload):
    client = login("alice")
    path = f"/documents/{app.config['TEST_DOCUMENTS']['alice']}"
    original = client.get(path).json
    assert client.patch(path, headers=csrf_headers(client), json=payload).status_code == 400
    assert client.get(path).json == original


def test_malformed_json_content_type_and_body_size(login):
    client = login("alice")
    headers = csrf_headers(client)
    assert (
        client.post(
            "/documents", headers=headers, data="{broken", content_type="application/json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/documents", headers=headers, data="plain", content_type="text/plain"
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/documents", headers=headers, json={"title": "Huge", "content": "x" * (256 * 1024)}
        ).status_code
        == 413
    )


def test_document_boundary_lengths(login):
    client = login("alice")
    response = client.post(
        "/documents",
        headers=csrf_headers(client),
        json={"title": "é" * 200, "content": "x" * 50000},
    )
    assert response.status_code == 201
    assert (
        client.patch(
            response.headers["Location"], headers=csrf_headers(client), json={"content": ""}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "query",
    [
        "per_page=0",
        "per_page=101",
        "page=-1",
        "page=no",
        "page=1000001",
        "page=1&page=2",
        "owner_id=other",
    ],
)
def test_reject_invalid_pagination(login, query):
    assert login("alice").get(f"/documents?{query}").status_code == 400


def test_invalid_uuid_returns_json_404(login):
    response = login("alice").get("/documents/not-a-uuid")
    assert response.status_code == 404 and response.is_json


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"username": "alice"},
        {"username": "alice", "password": 123},
        {"username": "alice", "password": "x" * 129},
        {"username": "' OR 1=1 --", "password": "x"},
    ],
)
def test_login_validation(client, payload):
    response = client.post("/auth/login", headers=csrf_headers(client), json=payload)
    assert response.status_code == 400
    assert client.get("/auth/me").status_code == 401
