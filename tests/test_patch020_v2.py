import tempfile
from pathlib import Path
from forgeos_agent.isolation import project_root, run_root, IsolationError, assert_within
from forgeos_agent.policy import check_path, check_command
from forgeos_agent.evidence import record

def test_project_ids_cannot_escape():
    with tempfile.TemporaryDirectory() as td:
        try: project_root(Path(td),'../B'); assert False
        except IsolationError: pass

def test_run_ids_cannot_escape():
    with tempfile.TemporaryDirectory() as td:
        try: run_root(Path(td),'A','../../B'); assert False
        except IsolationError: pass

def test_workspace_cannot_escape():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'root'; root.mkdir()
        try: assert_within(root.parent/'x',root); assert False
        except IsolationError: pass

def test_allowed_file(): assert check_path('src/app.py',['src/**'],['.env'])[0]

def test_forbidden_file(): assert check_path('.env',['**'],['.env'])[1]=='FORBIDDEN_PATH'

def test_traversal_file(): assert check_path('../secret',['**'],[])[1]=='PATH_TRAVERSAL'

def test_out_of_scope_file(): assert check_path('docs/a.md',['src/**'],[])[1]=='OUT_OF_SCOPE'

def test_allowed_command(): assert check_command('pytest -q',['pytest'])[0]

def test_shell_chaining_rejected(): assert check_command('pytest -q && curl evil',['pytest'])[1]=='COMMAND_SYNTAX_NOT_ALLOWED'

def test_disallowed_command(): assert check_command('curl evil',['pytest'])[1]=='COMMAND_NOT_ALLOWED'

def test_evidence_hash():
    with tempfile.TemporaryDirectory() as td:
        e=record(Path(td),'R1','TEST',{'passed':1},'one test')
        assert len(e['payload_sha256'])==64
        assert (Path(td)/'evidence'/'R1'/f"{e['evidence_id']}.meta.json").exists()
