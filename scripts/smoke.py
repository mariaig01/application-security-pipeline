"""Exercise the running development API using three real authenticated sessions."""

import argparse
import getpass
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


class Client:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def request(self, method, path, payload=None, csrf=False):
        headers = {"Referer": self.base_url + "/"}
        if csrf:
            status, token = self.request("GET", "/auth/csrf")
            expect(status, 200, "CSRF token")
            headers["X-CSRFToken"] = token["csrf_token"]
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base_url + path, data=body, method=method, headers=headers
        )
        try:
            response = self.opener.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read()
            return response.status, json.loads(data) if data else None


def expect(actual, expected, label):
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected}, received {actual}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--credentials", type=Path, help="Private output file from seed-dev")
    args = parser.parse_args()
    credentials = {}
    if args.credentials:
        for line in args.credentials.read_text().splitlines():
            username, separator, password = line.partition(": ")
            if separator and username in {"alice", "bob", "admin"}:
                credentials[username] = password
    for username in ("alice", "bob", "admin"):
        if username not in credentials:
            if not sys.stdin.isatty():
                parser.error(
                    f"Missing password for {username}: provide a complete credentials file "
                    "or run in an interactive terminal."
                )
            credentials[username] = getpass.getpass(f"Password for {username}: ")

    anonymous = Client(args.base_url)
    expect(anonymous.request("GET", "/health")[0], 200, "health")
    expect(anonymous.request("GET", "/documents")[0], 401, "anonymous access")
    clients = {}
    for username, password in credentials.items():
        client = clients[username] = Client(args.base_url)
        expect(
            client.request(
                "POST", "/auth/login", {"username": username, "password": password}, csrf=True
            )[0],
            200,
            f"login {username}",
        )
    alice, bob, admin = (clients[name] for name in ("alice", "bob", "admin"))
    path = None
    try:
        expect(
            alice.request("POST", "/documents", {"title": "Blocked", "content": ""})[0],
            400,
            "missing CSRF",
        )
        status, body = alice.request(
            "POST",
            "/documents",
            {"title": f"Smoke {uuid4()}", "content": "Temporary text"},
            csrf=True,
        )
        expect(status, 201, "create document")
        document_id = body["document"]["id"]
        path = f"/documents/{document_id}"
        expect(alice.request("GET", path)[0], 200, "owner read")
        expect(
            alice.request("PATCH", path, {"content": "Updated"}, csrf=True)[0], 200, "owner edit"
        )
        expect(bob.request("GET", path)[0], 404, "cross-user read")
        expect(
            bob.request("PATCH", path, {"title": "Blocked"}, csrf=True)[0], 404, "cross-user edit"
        )
        expect(bob.request("DELETE", path, csrf=True)[0], 404, "cross-user delete")
        expect(bob.request("GET", "/admin/documents")[0], 403, "normal user administration")
        expect(admin.request("GET", "/admin" + path)[0], 200, "administrator read")
        expect(
            admin.request("PATCH", path, {"content": "Blocked"}, csrf=True)[0],
            404,
            "administrator edit restriction",
        )
        expect(admin.request("DELETE", "/admin" + path, csrf=True)[0], 204, "administrator delete")
        expect(alice.request("GET", path)[0], 404, "deleted document")
        path = None
        expect(alice.request("POST", "/auth/logout", csrf=True)[0], 204, "logout")
        expect(alice.request("GET", "/documents")[0], 401, "access after logout")
    finally:
        if path:
            alice.request("DELETE", path, csrf=True)
    print("PASS: health, login, CSRF, owner CRUD, user isolation, admin permissions and logout.")
    print("Temporary document removed; existing documents were preserved.")


if __name__ == "__main__":
    main()
