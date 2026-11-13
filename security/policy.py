"""Evaluate scanner reports. Missing, malformed and incomplete reports fail closed."""

import argparse
import json
from datetime import date
from pathlib import Path


def evaluate(scanner, report, exceptions, today=None):
    today = today or date.today()
    if not isinstance(exceptions, list):
        raise ValueError("Exceptions must be a list")
    accepted = set()
    for exception in exceptions:
        fields = {"scanner", "finding", "target", "reason", "owner", "review_date"}
        if set(exception) != fields or not all(
            isinstance(v, str) and v.strip() for v in exception.values()
        ):
            raise ValueError(
                "Invalid exception: exact scope, reason, owner and review_date required"
            )
        if exception["scanner"] not in {"semgrep", "trivy", "zap"}:
            raise ValueError("Unknown exception scanner")
        if date.fromisoformat(exception["review_date"]) < today:
            raise ValueError("Expired exception")
        accepted.add((exception["scanner"], exception["finding"], exception["target"]))
    findings = []
    if scanner == "semgrep":
        if report["errors"] or not report["paths"]["scanned"]:
            raise ValueError("Semgrep errors or no scanned files")
        for row in report["results"]:
            if row["extra"]["severity"] in {"ERROR", "HIGH", "CRITICAL"}:
                findings.append((row["check_id"], row["path"]))
    elif scanner == "trivy":
        if report["SchemaVersion"] != 2 or not report["ArtifactName"]:
            raise ValueError("Invalid Trivy report")
        for result in report["Results"]:
            for row in result.get("Vulnerabilities") or []:
                if row["Severity"] in {"HIGH", "CRITICAL"}:
                    findings.append(
                        (row["VulnerabilityID"], result["Target"] + ":" + row["PkgName"])
                    )
    elif scanner == "zap":
        evidence = report["authentication"]
        if not (
            evidence["anonymous_status"] == 401
            and evidence["identity_status"] == 200
            and evidence["document_status"] == 200
            and evidence["scan_status"] == 100
            and evidence["passive_remaining"] == 0
            and evidence["authenticated_messages"] > 0
        ):
            raise ValueError("ZAP authentication or coverage incomplete")
        for row in report["alerts"]:
            if row["risk"] not in {"Informational", "Low", "Medium", "High"}:
                raise ValueError("Unknown ZAP risk")
            if row["risk"] == "High":
                findings.append((row["pluginId"], row["url"]))
    else:
        raise ValueError("Unknown scanner")
    return [
        (finding, target)
        for finding, target in findings
        if (scanner, finding, target) not in accepted
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", choices=["semgrep", "trivy", "zap"])
    parser.add_argument("report", type=Path)
    parser.add_argument("--exceptions", type=Path, default=Path("security/exceptions.json"))
    args = parser.parse_args()
    try:
        blocked = evaluate(
            args.scanner,
            json.loads(args.report.read_text()),
            json.loads(args.exceptions.read_text()),
        )
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit(f"Security gate failed: {error}") from None
    for finding, target in blocked:
        print(f"BLOCK: {finding} at {target}")
    if blocked:
        raise SystemExit(1)
    print(f"PASS: {args.scanner} security policy")


if __name__ == "__main__":
    main()
