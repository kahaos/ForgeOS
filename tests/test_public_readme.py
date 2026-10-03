from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_is_product_facing_and_discoverable():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "ai agent control plane",
        "ai agent security",
        "agent authorization",
        "task-scoped",
        "multi-agent security",
        "real ai agent trial",
        "security evidence",
        "current limitations",
        "roadmap",
    ]:
        assert phrase in text


def test_readme_links_to_the_main_discovery_pages():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in [
        "docs/WHY_FORGEOS.md",
        "docs/AI_AGENT_AUTHORIZATION.md",
        "docs/MULTI_AGENT_SECURITY.md",
        "docs/SECURITY_MODEL.md",
        "docs/REAL_AGENT_QUICKSTART.md",
        "docs/EVIDENCE.md",
        "docs/ROADMAP.md",
    ]:
        assert f"({path})" in text
