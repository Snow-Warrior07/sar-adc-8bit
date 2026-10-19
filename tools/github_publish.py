"""Use the existing Git Credential Manager session; never print or save its token."""
import argparse,io,json,os,subprocess,urllib.error,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OWNER='Snow-Warrior07'
REPO='sar-adc-8bit'


def token():
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',
                     text=True,capture_output=True,env=dict(os.environ,GCM_INTERACTIVE='never',GIT_TERMINAL_PROMPT='0'),timeout=30)
    fields=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
    if not fields.get('password'):raise RuntimeError('GitHub credential unavailable')
    return fields['password']


def api(route,method='GET',data=None,binary=False):
    req=urllib.request.Request('https://api.github.com'+route,
         data=json.dumps(data).encode() if data is not None else None,
         headers={'Accept':'application/vnd.github+json',
                  'User-Agent':'sar-adc-engineering','X-GitHub-Api-Version':'2022-11-28'},method=method)
    req.add_unredirected_header('Authorization','Bearer '+token())
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            raw=r.read()
            return raw if binary else json.loads(raw) if raw else {'status':r.status}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'GitHub HTTP {e.code}: {e.read().decode()[:500]}') from None


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create','dispatch','runs','jobs','logs','artifacts','download','pages','enable-pages','verify']);p.add_argument('--id',type=int,default=0);p.add_argument('--mode',choices=['all','timing'],default='all')
    a=p.parse_args();base=f'/repos/{OWNER}/{REPO}'
    user=api('/user')
    if user['login']!=OWNER:raise RuntimeError('Authenticated account does not match project owner')
    if a.action=='create':
        try:r=api(base)
        except RuntimeError as e:
            if 'HTTP 404' not in str(e):raise
            r=api('/user/repos','POST',{'name':REPO,'private':False,'description':'8-bit differential SAR ADC: verified RTL, analog models, online SPICE characterization and reproducible results.'})
        print(json.dumps({'url':r['html_url'],'private':r['private'],'default_branch':r['default_branch']}))
    elif a.action=='dispatch':print(json.dumps(api(base+'/actions/workflows/cloud-lab.yml/dispatches','POST',{'ref':'main','inputs':{'mode':a.mode}})))
    elif a.action=='runs':
        r=api(base+'/actions/runs?per_page=5')
        print(json.dumps([{k:x.get(k) for k in ['id','status','conclusion','html_url','head_sha']} for x in r['workflow_runs']],indent=2))
    elif a.action in ('jobs','artifacts'):
        r=api(base+f'/actions/runs/{a.id}/{a.action}')
        print(json.dumps([{k:x.get(k) for k in ['id','name','status','conclusion','html_url','size_in_bytes','steps']} for x in r[a.action]],indent=2))
    elif a.action=='download':
        raw=api(base+f'/actions/artifacts/{a.id}/zip',binary=True)
        dest=(ROOT/'results'/'cloud').resolve();dest.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for m in z.infolist():
                if not (dest/m.filename).resolve().is_relative_to(dest):raise RuntimeError('Unsafe artifact path')
            z.extractall(dest)
        print(json.dumps({'destination':str(dest),'bytes':len(raw)}))
    elif a.action=='logs':
        raw=api(base+f'/actions/jobs/{a.id}/logs',binary=True).decode(errors='replace')
        folder=ROOT/'results'/'ci';folder.mkdir(parents=True,exist_ok=True)
        (folder/f'job-{a.id}.txt').write_text(raw,encoding='utf-8')
        print(raw[-6500:])
    elif a.action=='pages':print(json.dumps(api(base+'/pages')))
    elif a.action=='enable-pages':
        try:r=api(base+'/pages')
        except RuntimeError as e:
            if 'HTTP 404' not in str(e):raise
            r=api(base+'/pages','POST',{'build_type':'legacy','source':{'branch':'main','path':'/docs'}})
        print(json.dumps({'url':r.get('html_url'),'status':r.get('status')}))
    else:
        r=api(base+'/commits/main');print(json.dumps({'url':r['html_url'],'sha':r['sha']}))


if __name__=='__main__':main()
