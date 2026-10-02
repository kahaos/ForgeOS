from pathlib import Path
from local_test_handler import HANDLER_ID, execute, verify, HANDLERS


def test_registered_handler():
    assert HANDLER_ID in HANDLERS
    assert HANDLERS[HANDLER_ID]["target"] == "local-test"


def test_execute_and_verify(tmp_path):
    result = execute(tmp_path)
    assert result["handler_id"] == HANDLER_ID
    assert result["target"] == "local-test"

    verified = verify(tmp_path, result)
    assert verified["ok"] is True
    assert verified["sha256"] == result["sha256"]


def test_handler_is_bounded():
    assert list(HANDLERS) == ["local-test.artifact.v1"]
    assert HANDLERS[HANDLER_ID]["target"] == "local-test"
