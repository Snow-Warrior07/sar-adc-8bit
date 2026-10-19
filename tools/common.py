import json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def save(path,data):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def phase(number,name,checks,extra=None):
    result=dict(phase=number,name=name,status='passed' if all(x['passed'] for x in checks) else 'failed',
                checks=checks,environment=dict(python=sys.version.split()[0],platform=platform.platform()),
                executed_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    if extra:result.update(extra)
    save(Path('results/phases')/f'phase-{number:02d}.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return result


def executable(name):
    import shutil
    local=ROOT/'.tools'/'oss-cad-suite'/'bin'/(name+'.exe' if os.name=='nt' else name)
    return str(local) if local.exists() else shutil.which(name)


def tool_env():
    env=dict(os.environ)
    env['PATH']=str(ROOT/'.tools'/'oss-cad-suite'/'bin')+os.pathsep+str(ROOT/'.tools'/'oss-cad-suite'/'lib')+os.pathsep+env.get('PATH','')
    return env
