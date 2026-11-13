"""Run pinned scanners locally or in CI; never reuse development credentials."""

import argparse
import http.cookiejar
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

IMAGES = json.loads(Path("security/images.json").read_text())
REPORTS = Path("reports")


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def api(component, kind, action, **params):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"http://127.0.0.1:18082/JSON/{component}/{kind}/{action}/?{query}",
        headers={"Host": "localhost:8080"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if "code" in result:
        raise RuntimeError(f"ZAP API failure: {result}")
    return result


def wait_for(check, seconds=600):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (OSError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("Scan readiness/completion deadline exceeded")


def zap_scan():
    env = dict(os.environ, SCAN_SECRET_KEY=secrets.token_hex(32))
    compose = ["docker", "compose", "-f", "compose.security.yaml"]
    try:
        run(*compose, "up", "--build", "-d", env=env)
        wait_for(lambda: api("core", "view", "version"))
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": "http://127.0.0.1:18082"}),
            urllib.request.HTTPCookieProcessor(jar),
        )

        def request(path, body=None, token=None):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["X-CSRFToken"] = token
            req = urllib.request.Request(
                "http://app:8000" + path,
                data=json.dumps(body).encode() if body else None,
                headers=headers,
            )
            try:
                response = opener.open(req, timeout=20)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read())

        wait_for(lambda: request("/health")[0] == 200)
        anonymous = request("/documents")[0]
        output = run(
            *compose,
            "exec",
            "-T",
            "app",
            "flask",
            "--app",
            "appsec_pipeline",
            "create-user",
            "--username",
            "scanner",
            "--generate-password",
            env=env,
            capture_output=True,
            text=True,
        ).stdout
        password = output.split("Password (shown once): ")[1].strip()
        token = request("/auth/csrf")[1]["csrf_token"]
        assert (
            request("/auth/login", {"username": "scanner", "password": password}, token)[0] == 200
        )
        token = request("/auth/csrf")[1]["csrf_token"]
        status, body = request(
            "/documents", {"title": "Scanner fixture", "content": "Fictional"}, token
        )
        assert status == 201
        path = "/documents/" + body["document"]["id"]
        identity = request("/auth/me")[0]
        document = request(path)[0]
        cookie = "; ".join(f"{item.name}={item.value}" for item in jar)
        for name, value in (("Cookie", cookie), ("X-CSRFToken", token)):
            api(
                "replacer",
                "action",
                "addRule",
                description=name,
                enabled="true",
                matchType="REQ_HEADER",
                matchRegex="false",
                matchString=name,
                replacement=value,
                url="http://app:8000/.*",
            )
        api("context", "action", "newContext", contextName="private-api")
        api(
            "context",
            "action",
            "includeInContext",
            contextName="private-api",
            regex="http://app:8000/.*",
        )
        api("ascan", "action", "excludeFromScan", regex="http://app:8000/auth/(login|logout).*")
        api("ascan", "action", "setOptionMaxScanDurationInMins", Integer=5)
        scan = api("ascan", "action", "scan", url="http://app:8000", recurse="true")["scan"]
        wait_for(lambda: int(api("ascan", "view", "status", scanId=scan)["status"]) == 100, 480)
        wait_for(lambda: int(api("pscan", "view", "recordsToScan")["recordsToScan"]) == 0)
        messages = api(
            "core", "view", "messages", baseurl="http://app:8000/documents", count=10000
        )["messages"]
        scan_messages = {
            str(identifier)
            for identifier in api("ascan", "view", "messagesIds", scanId=scan)["messagesIds"]
        }
        authenticated = sum(
            " 200 " in row["responseHeader"].split("\r\n")[0] and str(row["id"]) in scan_messages
            for row in messages
        )
        assert request("/auth/me")[0] == 200
        report = {
            "alerts": api("core", "view", "alerts", baseurl="http://app:8000", count=10000)[
                "alerts"
            ],
            "authentication": {
                "anonymous_status": anonymous,
                "identity_status": identity,
                "document_status": document,
                "scan_status": 100,
                "passive_remaining": 0,
                "authenticated_messages": authenticated,
            },
        }
        # Session headers/passwords and raw message history are never exported.
        encoded = json.dumps(report, indent=2)
        for secret in (password, token, cookie, *(item.value for item in jar)):
            encoded = encoded.replace(secret, "[REDACTED]")
        (REPORTS / "zap.json").write_text(encoded)
    finally:
        run(*compose, "down", "--volumes", "--remove-orphans", env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", choices=["semgrep", "trivy", "zap"])
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    # Stale success reports must never mask a failed scanner.
    report = REPORTS / f"{args.scanner}.json"
    report.unlink(missing_ok=True)
    if args.scanner == "semgrep":
        run(
            "docker",
            "run",
            "--rm",
            "-v",
            f"{Path.cwd()}:/src",
            "-w",
            "/src",
            IMAGES["semgrep"],
            "semgrep",
            "scan",
            "--config",
            "security/semgrep.json",
            "--strict",
            "--metrics=off",
            "--json",
            "--output",
            "/src/reports/semgrep.json",
            "appsec_pipeline",
            "migrations",
            "scripts",
            "security",
        )
        run(
            "docker",
            "run",
            "--rm",
            "-v",
            f"{Path.cwd()}:/src",
            "-w",
            "/src",
            IMAGES["semgrep"],
            "semgrep",
            "scan",
            "--config",
            "security/semgrep.json",
            "--metrics=off",
            "--strict",
            "--json",
            "--output",
            "/src/reports/semgrep-demo.json",
            "demos/unsafe.py",
        )
        demonstration = subprocess.run(
            ["python3", "security/policy.py", "semgrep", "reports/semgrep-demo.json"],
            capture_output=True,
            text=True,
        )
        if demonstration.returncode != 1 or "BLOCK:" not in demonstration.stdout:
            raise RuntimeError("Semgrep failed to block the isolated vulnerable fixture")
        print("PASS: Semgrep detected and blocked the isolated eval fixture")
    elif args.scanner == "trivy":
        run("docker", "build", "--target", "runtime", "-t", "appsec-scan:local", ".")
        run("docker", "save", "-o", "reports/image.tar", "appsec-scan:local")
        try:
            run(
                "docker",
                "run",
                "--rm",
                "-v",
                f"{Path.cwd() / REPORTS}:/reports",
                IMAGES["trivy"],
                "image",
                "--input",
                "/reports/image.tar",
                "--scanners",
                "vuln",
                "--format",
                "json",
                "--output",
                "/reports/trivy.json",
                "--no-progress",
            )
        finally:
            (REPORTS / "image.tar").unlink(missing_ok=True)
    else:
        zap_scan()
    run("python3", "security/policy.py", args.scanner, str(report))


if __name__ == "__main__":
    main()
