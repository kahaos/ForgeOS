import hashlib
from pathlib import Path

from local_test_handler import HANDLER_ID, execute, verify


def test_local_test_handler(tmp_path):
    result = execute(tmp_path)

    assert result["handler_id"] == HANDLER_ID
    assert result["target"] == "local-test"

    artifact = tmp_path / result["artifact"]
    assert artifact.is_file()

    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert result["sha256"] == expected

    verified = verify(tmp_path, result)
    assert verified["ok"] is True
    assert verified["sha256"] == expected


def test_handler_is_bounded():
    from local_test_handler import HANDLERS

    assert list(HANDLERS) == ["local-test.artifact.v1"]
    assert HANDLERS[HANDLER_ID]["target"] == "local-test"
