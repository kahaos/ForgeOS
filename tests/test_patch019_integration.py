import tempfile
from pathlib import Path
from forgeos_github.api import GitHubIntegration

class FakeProvider:
    def get_repository(self,o,r):
        return {"id":123,"default_branch":"main","html_url":f"https://github.com/{o}/{r}","full_name":f"{o}/{r}"}
    def list_branches(self,o,r): return [{"name":"main"}]
    def list_commits(self,o,r): return [{"sha":"abc123"}]
    def list_pull_requests(self,o,r): return []
    def list_checks(self,o,r,ref): return []
    def create_pull_request(self,o,r,title,head,base,body): return {"number":1,"title":title,"head":head,"base":base}

def test_project_create_and_list():
    with tempfile.TemporaryDirectory() as td:
        a=GitHubIntegration(Path(td), provider=FakeProvider())
        s,b=a.post("/api/projects",{"name":"Calculator"})
        assert s==201
        pid=b["project"]["project_id"]
        s,b=a.get("/api/projects")
        assert s==200 and b["projects"][0]["project_id"]==pid

def test_bind_and_repository():
    with tempfile.TemporaryDirectory() as td:
        a=GitHubIntegration(Path(td), provider=FakeProvider())
        _,b=a.post("/api/projects",{"name":"Calculator"}); pid=b["project"]["project_id"]
        s,_=a.post(f"/api/projects/{pid}/github/bind",{"owner":"forgeos","repo":"calculator"})
        assert s==200
        s,b=a.get(f"/api/projects/{pid}/github/repository")
        assert s==200 and b["repository"]["full_name"]=="forgeos/calculator"

def test_run_contract_requires_github():
    with tempfile.TemporaryDirectory() as td:
        a=GitHubIntegration(Path(td), provider=FakeProvider())
        _,b=a.post("/api/projects",{"name":"Calculator"}); pid=b["project"]["project_id"]
        s,_=a.post(f"/api/projects/{pid}/runs",{"run_id":"RUN-001","task":"change calculator"})
        assert s in (409,500)

def test_provider_backed_reads():
    with tempfile.TemporaryDirectory() as td:
        a=GitHubIntegration(Path(td), provider=FakeProvider())
        _,b=a.post("/api/projects",{"name":"Calculator"}); pid=b["project"]["project_id"]
        a.post(f"/api/projects/{pid}/github/bind",{"owner":"forgeos","repo":"calculator"})
        s,b=a.get(f"/api/projects/{pid}/github/branches")
        assert s==200 and b["branches"][0]["name"]=="main"
