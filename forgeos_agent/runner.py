import json, os, shlex, subprocess
from pathlib import Path
from .models import AgentRun
from .isolation import run_root, assert_within
from .policy import check_path, check_command
from .evidence import record
from .github_workspace import GitHubWorkspace
from .sandbox import build_execution, SandboxError

class RunManager:
    def __init__(self, root, github_integration):
        self.root=Path(root); self.github=github_integration
        self.path=self.root/'data'/'agent_runs.json'; self.path.parent.mkdir(parents=True,exist_ok=True)
    def _load(self): return json.loads(self.path.read_text()) if self.path.exists() else {}
    def _save(self,d):
        tmp=self.path.with_suffix('.tmp'); tmp.write_text(json.dumps(d,indent=2,sort_keys=True)); os.replace(tmp,self.path)
    def get(self,rid): return self._load().get(rid)
    def create(self, project, run_id, task):
        if self.get(run_id): raise ValueError('RUN_EXISTS')
        contract=self.github.orchestrator.create_contract(project,run_id,task)
        dest=run_root(self.root/'agent_workspaces',project.project_id,run_id)
        ws=GitHubWorkspace(self.root/'agent_workspaces',self.github.provider)
        ws.clone_exact(contract.github_owner,contract.github_repo,contract.base_branch,contract.base_commit,dest)
        data=AgentRun(run_id,project.project_id,task,contract.base_commit,str(dest),contract.github_owner,contract.github_repo,contract.base_branch,contract.allowed_paths,contract.forbidden_paths,contract.required_stages).__dict__.copy()
        data['allowed_commands']=['pytest','python','python3','npm','node']
        data['state']='READY'
        db=self._load(); db[run_id]=data; self._save(db); return data
    def tool(self, run, tool, args):
        source=Path(run['workspace'])
        if tool=='read_file':
            ok,why=check_path(args.get('path'),run['allowed_paths'],run['forbidden_paths'])
            if not ok: raise PermissionError(why)
            p=assert_within(source/args['path'],source); return {'content':p.read_text(encoding='utf-8')}
        if tool=='write_file':
            ok,why=check_path(args.get('path'),run['allowed_paths'],run['forbidden_paths'])
            if not ok: raise PermissionError(why)
            p=assert_within(source/args['path'],source); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(args.get('content',''),encoding='utf-8')
            if args['path'] not in run['changed_files']: run['changed_files'].append(args['path'])
            self._persist(run); return {'ok':True}
        if tool=='run_command':
            ok,why=check_command(args.get('command'),run.get('allowed_commands',[]))
            if not ok: raise PermissionError(why)
            try:
                argv, env = build_execution(args['command'], source, self.root)
            except SandboxError as e:
                raise PermissionError(str(e))
            p=subprocess.run(argv,cwd=source,shell=False,text=True,capture_output=True,timeout=300,env=env)
            ev=record(self.root,run['run_id'],'COMMAND',{'command':args['command'],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},'command execution')
            run['evidence_ids'].append(ev['evidence_id']); self._persist(run)
            return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'evidence':ev}
        if tool in ('approve_release','deploy_production'): raise PermissionError('HUMAN_ONLY_OPERATION')
        raise KeyError('UNKNOWN_TOOL')
    def finalize(self,run):
        verdict='PASS'
        for eid in run.get('evidence_ids',[]):
            if not (self.root/'evidence'/run['run_id']/f'{eid}.meta.json').exists(): verdict='FAIL'
        run['verdict']=verdict; run['state']='VERDICT'; self._persist(run); return run
    def approve(self,run,approved_by):
        if run.get('verdict')!='PASS': raise ValueError('VERDICT_REQUIRED')
        if not approved_by or str(approved_by).lower() in {'agent','gemini','codex','claude','copilot'}: raise ValueError('HUMAN_ACTOR_REQUIRED')
        run['approval']='APPROVED'; run['approval_actor']=approved_by; run['state']='APPROVED'; self._persist(run); return run
    def return_to_github(self,run,title,body=''):
        if run.get('verdict')!='PASS': raise ValueError('VERDICT_REQUIRED')
        if run.get('approval')!='APPROVED': raise ValueError('HUMAN_APPROVAL_REQUIRED')
        branch=f'forgeos/{run["run_id"]}'
        model_fields = {
            'run_id','project_id','task','base_commit','workspace',
            'owner','repo','branch','allowed_paths','forbidden_paths',
            'required_stages','state','verdict','approval',
            'changed_files','evidence_ids'
        }
        github_run = AgentRun(**{
            k: run[k]
            for k in model_fields
            if k in run
        })
        sha=GitHubWorkspace(self.root/'agent_workspaces',self.github.provider).create_branch_commit_push(github_run,branch,title)
        pr=self.github.provider.create_pull_request(run['owner'],run['repo'],title,branch,run['branch'],body)
        run['return_branch']=branch; run['commit_sha']=sha; run['pull_request']=pr; run['state']='PR_CREATED'; self._persist(run); return run
    def _persist(self,run):
        d=self._load(); d[run['run_id']]=run; self._save(d)
