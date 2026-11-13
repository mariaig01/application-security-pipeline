import copy
import unittest
from datetime import date

from security.policy import evaluate


class PolicyTests(unittest.TestCase):
    """Synthetic reports exercise gates; these are not scanner findings."""

    def reports(self):
        return {
            "semgrep": {"errors": [], "paths": {"scanned": ["app.py"]}, "results": []},
            "trivy": {"SchemaVersion": 2, "ArtifactName": "image", "Results": []},
            "zap": {
                "alerts": [],
                "authentication": {
                    "anonymous_status": 401,
                    "identity_status": 200,
                    "document_status": 200,
                    "scan_status": 100,
                    "passive_remaining": 0,
                    "authenticated_messages": 1,
                },
            },
        }

    def test_clean_reports_pass(self):
        for scanner, report in self.reports().items():
            self.assertEqual(evaluate(scanner, report, []), [])

    def test_all_blocking_thresholds(self):
        reports = self.reports()
        reports["semgrep"]["results"] = [
            {"check_id": "eval", "path": "app.py", "extra": {"severity": "ERROR"}}
        ]
        reports["trivy"]["Results"] = [
            {
                "Target": "os",
                "Vulnerabilities": [
                    {"Severity": "HIGH", "VulnerabilityID": "SYNTHETIC", "PkgName": "example"}
                ],
            }
        ]
        reports["zap"]["alerts"] = [{"risk": "High", "pluginId": "synthetic", "url": "/private"}]
        for scanner, report in reports.items():
            self.assertEqual(len(evaluate(scanner, report, [])), 1)

    def test_missing_malformed_or_incomplete_report_fails(self):
        for scanner in self.reports():
            with self.assertRaises((KeyError, TypeError, ValueError)):
                evaluate(scanner, {}, [])
        report = self.reports()["semgrep"]
        report["errors"] = ["scanner failure"]
        with self.assertRaises(ValueError):
            evaluate("semgrep", report, [])
        for field in (
            "identity_status",
            "document_status",
            "scan_status",
            "authenticated_messages",
            "anonymous_status",
        ):
            report = copy.deepcopy(self.reports()["zap"])
            report["authentication"][field] = -1
            with self.assertRaises(ValueError):
                evaluate("zap", report, [])

    def test_exception_exact_scope_expiration_and_metadata(self):
        report = self.reports()["semgrep"]
        report["results"] = [{"check_id": "eval", "path": "app.py", "extra": {"severity": "ERROR"}}]
        exception = {
            "scanner": "semgrep",
            "finding": "eval",
            "target": "app.py",
            "reason": "Synthetic policy test",
            "owner": "test",
            "review_date": "2030-01-02",
        }
        today = date(2030, 1, 1)
        self.assertEqual(evaluate("semgrep", report, [exception], today), [])
        exception["target"] = "different.py"
        self.assertEqual(len(evaluate("semgrep", report, [exception], today)), 1)
        exception["review_date"] = "2029-12-31"
        with self.assertRaises(ValueError):
            evaluate("semgrep", report, [exception], today)
        del exception["reason"]
        with self.assertRaises(ValueError):
            evaluate("semgrep", report, [exception], today)
