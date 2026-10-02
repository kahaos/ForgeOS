import json
import tempfile
import unittest
from pathlib import Path

from forgeos_github.project_registry import ProjectRegistry
from forgeos_github.models import Project, GitHubRepository
from forgeos_github.contract import build_execution_contract, validate_path
from forgeos_github.webhook import verify_signature
import hashlib, hmac

class TestPatch019(unittest.TestCase):
    def test_project_creation_and_github_binding(self):
        with tempfile.TemporaryDirectory() as d:
            r = ProjectRegistry(d)
            p = r.create("Calculator", github_owner="octo", github_repo="calculator")
            self.assertTrue(p["project_id"].startswith("proj-calculator"))
            self.assertEqual(p["github"]["full_name"], "octo/calculator")
            r.bind_github(p["project_id"], "octo", "calculator", "main", 123)
            got = r.get(p["project_id"])
            self.assertEqual(got["github"]["repo_id"], 123)

    def test_project_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            r = ProjectRegistry(d)
            a = r.create("Alpha")
            b = r.create("Beta")
            self.assertNotEqual(a["project_id"], b["project_id"])
            self.assertEqual(len(r.list()), 2)

    def test_scope_and_forbidden_paths(self):
        ok, reason = validate_path("src/calculator.py", ["src/**"], [".env", ".git/**"])
        self.assertTrue(ok)
        ok, reason = validate_path(".env", ["**"], [".env"])
        self.assertFalse(ok); self.assertEqual(reason, "FORBIDDEN_PATH")
        ok, reason = validate_path("../secret", ["**"], [])
        self.assertFalse(ok); self.assertEqual(reason, "PATH_TRAVERSAL")

    def test_contract_binds_commit_and_repo(self):
        p = Project("p1", "Calculator", github=GitHubRepository("octo","calc"))
        c = build_execution_contract(p, "run-1", "add percentage", "abc123")
        self.assertEqual(c.base_commit, "abc123")
        self.assertEqual(c.github_repo, "calc")
        self.assertIn("APPROVAL_REQUEST", c.required_stages)

    def test_webhook_signature(self):
        body = b'{"action":"opened"}'
        secret = "secret"
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(body, sig, secret))
        self.assertFalse(verify_signature(body, sig[:-1] + "0", secret))

if __name__ == "__main__":
    unittest.main()
