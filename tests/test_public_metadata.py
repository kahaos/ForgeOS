from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_project_metadata_exists():
    assert (ROOT / "CONTRIBUTING.md").exists()
    assert (ROOT / "SECURITY.md").exists()
    assert (ROOT / "CITATION.cff").exists()
    assert (ROOT / ".github/ISSUE_TEMPLATE/feature_request.md").exists()
    assert (ROOT / ".github/ISSUE_TEMPLATE/security_report.md").exists()


def test_security_and_contribution_docs_are_specific_to_forgeos():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    assert "ai agent" in security
    assert "authorization" in security
    assert "security-sensitive" in contributing
    assert "pytest -q" in contributing
