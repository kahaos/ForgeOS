from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from governance import GovernanceStore

def test_initial_state(tmp_path):
    assert GovernanceStore(tmp_path).state()["state"] == "REQUESTED"

def test_valid_transition_and_audit(tmp_path):
    s = GovernanceStore(tmp_path)
    result = s.transition("EXPERIMENTING", "test")
    assert result["state"]["state"] == "EXPERIMENTING"
    assert len(s.audit()) == 1
    assert s.audit()[0]["event_digest"]

def test_illegal_transition_is_blocked(tmp_path):
    s = GovernanceStore(tmp_path)
    try:
        s.transition("DEPLOYED")
    except ValueError:
        pass
    else:
        raise AssertionError("illegal transition accepted")

def test_release_path(tmp_path):
    s = GovernanceStore(tmp_path)
    for state in ["EXPERIMENTING","EVIDENCE_READY","VERDICTED","APPROVAL_PENDING","RELEASED"]:
        s.transition(state)
    assert s.state()["state"] == "RELEASED"

def test_production_disabled(tmp_path):
    assert GovernanceStore(tmp_path).health()["production_enabled"] is False
