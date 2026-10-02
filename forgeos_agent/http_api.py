from urllib.parse import urlparse
from .runner import RunManager

class AgentHTTP:
    def __init__(self,root,github_integration): self.manager=RunManager(root,github_integration)
    def get(self,path):
        parts=[x for x in urlparse(path).path.split('/') if x]
        if parts==['api','agent','capabilities']:
            return 200,{'schema':'forgeos.agent.v2','human_only':['human_approval','deploy_production'],'tools':['read_file','write_file','run_command']}
        if len(parts)==4 and parts[:3]==['api','agent','runs']:
            r=self.manager.get(parts[3]); return (200,r) if r else (404,{'error':'run_not_found'})
        return None
    def post(self,path,body,project_resolver):
        parts=[x for x in urlparse(path).path.split('/') if x]
        try:
            if len(parts)==5 and parts[:3]==['api','agent','runs'] and parts[4]=='tool':
                run=self.manager.get(parts[3]);
                if not run: return 404,{'error':'run_not_found'}
                return 200,self.manager.tool(run,str(body.get('tool','')),body.get('args') or {})
            if len(parts)==5 and parts[:3]==['api','agent','runs'] and parts[4] in {'finalize','human-approval','return'}:
                rid=parts[3]; run=self.manager.get(rid)
                if not run: return 404,{'error':'run_not_found'}
                if parts[4]=='finalize': return 200,self.manager.finalize(run)
                if parts[4]=='human-approval': return 200,self.manager.approve(run,str(body.get('approved_by','')))
                return 200,self.manager.return_to_github(run,str(body.get('title','ForgeOS change')),str(body.get('body','')))
            if len(parts)==4 and parts[:2]==['api','projects'] and parts[2] and parts[3]=='runs':
                project=project_resolver(parts[2]);
                if project is None: return 404,{'error':'project_not_found','project_id':parts[2]}
                data=self.manager.create(project,str(body.get('run_id','')).strip(),str(body.get('task','')).strip())
                return 201,{'schema':'forgeos.agent.run.v2','run':data}
        except PermissionError as e: return 403,{'error':str(e)}
        except ValueError as e: return 409,{'error':str(e)}
        except Exception as e:
            return 502,{'error':'agent_integration_error','detail':str(e)}
        return None
