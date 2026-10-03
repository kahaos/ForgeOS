import tempfile

from controlplane import ControlPlane


def test_control_plane_can_gate_a_real_executor():
    with tempfile.TemporaryDirectory() as td:
        cp = ControlPlane(td)
        cp.register("builder", "human", ["FS_WRITE"])
        seen = []

        result = cp.request(
            "builder",
            "filesystem",
            "write",
            "workspace/a.txt",
            executor=lambda req: seen.append(req.target) or {"written": True},
        )

        assert result["verdict"] == "allow"
        assert result["result"] == {"written": True}
        assert seen == ["workspace/a.txt"]


def test_control_plane_denies_missing_capability_before_executor():
    with tempfile.TemporaryDirectory() as td:
        cp = ControlPlane(td)
        cp.register("builder", "human", ["FS_READ"])
        executed = False

        def executor(_req):
            nonlocal executed
            executed = True
            return {"should": "not happen"}

        result = cp.request("builder", "filesystem", "write", "blocked.txt", executor=executor)

        assert result["verdict"] == "deny"
        assert executed is False
