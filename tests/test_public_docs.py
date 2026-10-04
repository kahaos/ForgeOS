from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_guides_exist_and_have_search_intent():
    required = {
        "WHY_FORGEOS.md": ["AI agent control plane", "task-scoped"],
        "AI_AGENT_AUTHORIZATION.md": ["AI agent authorization", "ALLOW", "ASK", "DENY"],
        "MULTI_AGENT_SECURITY.md": ["Multi-agent security", "delegation"],
        "SECURITY_MODEL.md": ["security model", "fail closed"],
        "REAL_AGENT_QUICKSTART.md": ["Real AI agent quickstart", "real-agent-trial.py"],
    }
    for name, phrases in required.items():
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").lower()
        for phrase in phrases:
            assert phrase.lower() in text, (name, phrase)


def test_discovery_guides_state_prototype_limits_and_cross_link():
    for name in [
        "WHY_FORGEOS.md",
        "AI_AGENT_AUTHORIZATION.md",
        "MULTI_AGENT_SECURITY.md",
        "SECURITY_MODEL.md",
        "REAL_AGENT_QUICKSTART.md",
    ]:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").lower()
        assert "prototype" in text
        assert "real-agent-quickstart.md" in text or name == "REAL_AGENT_QUICKSTART.md"
