import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"

class GitHubAPIError(RuntimeError):
    def __init__(self, status, message, body=None):
        super().__init__(f"GitHub API {status}: {message}")
        self.status, self.message, self.body = status, message, body

class GitHubProvider:
    """Small dependency-free GitHub REST adapter.

    The token should be a GitHub App installation token or fine-grained token.
    ForgeOS never persists the token in project state.
    """

    def __init__(self, token=None, api_base=API, timeout=20):
        self.token = token or os.getenv("FORGEOS_GITHUB_TOKEN")
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def _request(self, method, path, payload=None, accept="application/vnd.github+json"):
        if not self.token:
            raise GitHubAPIError(0, "FORGEOS_GITHUB_TOKEN is not configured")
        url = self.api_base + path
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Authorization", "Bearer " + self.token)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try: body_json = json.loads(body)
            except Exception: body_json = body
            raise GitHubAPIError(e.code, body_json.get("message", "request failed") if isinstance(body_json, dict) else "request failed", body_json)
        except urllib.error.URLError as e:
            raise GitHubAPIError(0, str(e))

    def get_repository(self, owner, repo):
        return self._request("GET", f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}")

    def list_repositories(self, owner=None, per_page=100):
        if owner:
            path = f"/users/{urllib.parse.quote(owner)}/repos?per_page={min(per_page,100)}"
        else:
            path = f"/user/repos?per_page={min(per_page,100)}"
        return self._request("GET", path)

    def create_repository(self, name, description="", private=True, organization=None):
        if organization:
            path = f"/orgs/{urllib.parse.quote(organization)}/repos"
        else:
            path = "/user/repos"
        return self._request("POST", path, {
            "name": name, "description": description, "private": private
        })

    def get_branch(self, owner, repo, branch):
        return self._request("GET", f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch)}")

    def list_branches(self, owner, repo):
        return self._request("GET", f"/repos/{owner}/{repo}/branches?per_page=100")

    def get_commit(self, owner, repo, sha):
        return self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")

    def list_commits(self, owner, repo, branch=None):
        q = "" if not branch else "?sha=" + urllib.parse.quote(branch)
        return self._request("GET", f"/repos/{owner}/{repo}/commits{q}")

    def create_branch(self, owner, repo, branch, from_sha):
        return self._request("POST", f"/repos/{owner}/{repo}/git/refs", {
            "ref": "refs/heads/" + branch, "sha": from_sha
        })

    def list_pull_requests(self, owner, repo, state="open"):
        return self._request("GET", f"/repos/{owner}/{repo}/pulls?state={state}&per_page=100")

    def get_pull_request(self, owner, repo, number):
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")

    def create_pull_request(self, owner, repo, title, head, base, body=""):
        return self._request("POST", f"/repos/{owner}/{repo}/pulls", {
            "title": title, "head": head, "base": base, "body": body
        })

    def list_checks(self, owner, repo, ref):
        return self._request("GET", f"/repos/{owner}/{repo}/commits/{urllib.parse.quote(ref)}/check-runs")

    def list_statuses(self, owner, repo, ref):
        return self._request("GET", f"/repos/{owner}/{repo}/commits/{urllib.parse.quote(ref)}/statuses")

    def list_hooks(self, owner, repo):
        return self._request("GET", f"/repos/{owner}/{repo}/hooks")

    def create_webhook(self, owner, repo, url, secret, events=None, active=True):
        return self._request("POST", f"/repos/{owner}/{repo}/hooks", {
            "name": "web", "active": active,
            "events": events or ["push", "pull_request", "check_run"],
            "config": {"url": url, "content_type": "json", "secret": secret, "insecure_ssl": "0"}
        })

    def get_webhook(self, owner, repo, hook_id):
        return self._request("GET", f"/repos/{owner}/{repo}/hooks/{hook_id}")

    def delete_webhook(self, owner, repo, hook_id):
        return self._request("DELETE", f"/repos/{owner}/{repo}/hooks/{hook_id}")
