import os, shutil, subprocess, tempfile
from pathlib import Path
from .isolation import run_root, assert_within

class GitHubWorkspaceError(Exception): pass

class GitHubWorkspace:
    def __init__(self, root, provider): self.root=Path(root); self.provider=provider
    def _git_env(self):
        token=getattr(self.provider,'token',None) or os.getenv('FORGEOS_GITHUB_TOKEN')
        if not token: raise GitHubWorkspaceError('FORGEOS_GITHUB_TOKEN is not configured')
        fd, ask_path = tempfile.mkstemp(prefix='.forgeos-askpass-',dir=str(self.root))
        os.close(fd)
        ask=Path(ask_path)
        ask.write_text('#!/bin/sh\ncase "$1" in *Username*) echo x-access-token;; *Password*) echo "$FORGEOS_GITHUB_TOKEN";; esac\n',encoding='utf-8'); ask.chmod(0o700)
        env=os.environ.copy(); env['GIT_ASKPASS']=str(ask); env['GIT_TERMINAL_PROMPT']='0'
        return env,ask
    def clone_exact(self, owner, repo, branch, base_commit, destination):
        dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists(): raise GitHubWorkspaceError('workspace already exists')
        env,ask=self._git_env()
        try:
            url=f'https://github.com/{owner}/{repo}.git'
            subprocess.run(['git','clone','--no-checkout',url,str(dest)],check=True,capture_output=True,text=True,env=env,timeout=180)
            subprocess.run(['git','-C',str(dest),'fetch','--depth','1','origin',base_commit],check=True,capture_output=True,text=True,env=env,timeout=180)
            subprocess.run(['git','-C',str(dest),'checkout','--detach',base_commit],check=True,capture_output=True,text=True,timeout=60)
            return dest
        finally:
            ask.unlink(missing_ok=True)
    def create_branch_commit_push(self, run, branch, message):
        env, ask = self._git_env()
        dest = Path(run.workspace)
        try:
            branches = subprocess.run(
                ['git', '-C', str(dest), 'branch', '--list', branch],
                check=True, capture_output=True, text=True, timeout=30
            ).stdout.strip()

            if branches:
                subprocess.run(
                    ['git', '-C', str(dest), 'switch', branch],
                    check=True, capture_output=True, text=True, timeout=60
                )
            else:
                subprocess.run(
                    ['git', '-C', str(dest), 'switch', '-c', branch],
                    check=True, capture_output=True, text=True, timeout=60
                )

            subprocess.run(
                ['git', '-C', str(dest), 'config', 'user.name', 'ForgeOS Agent'],
                check=True, capture_output=True, text=True, timeout=30
            )
            subprocess.run(
                ['git', '-C', str(dest), 'config', 'user.email',
                 'forgeos-agent@users.noreply.github.com'],
                check=True, capture_output=True, text=True, timeout=30
            )

            subprocess.run(
                ['git', '-C', str(dest), 'add', '--', *run.changed_files],
                check=True, capture_output=True, text=True, timeout=60
            )

            staged = subprocess.run(
                ['git', '-C', str(dest), 'diff', '--cached', '--quiet'],
                capture_output=True, text=True, timeout=30
            )

            if staged.returncode == 1:
                subprocess.run(
                    ['git', '-C', str(dest), 'commit', '-m', message],
                    check=True, capture_output=True, text=True, timeout=60
                )

            subprocess.run(
                ['git', '-C', str(dest), 'push', '-u', 'origin', branch],
                check=True, capture_output=True, text=True,
                env=env, timeout=180
            )

            sha = subprocess.run(
                ['git', '-C', str(dest), 'rev-parse', 'HEAD'],
                check=True, capture_output=True, text=True, timeout=30
            ).stdout.strip()

            return sha
        finally:
            ask.unlink(missing_ok=True)
