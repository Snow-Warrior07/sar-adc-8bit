"""Test a clean tracked-source export with a separately installed Python environment."""
import hashlib,io,json,os,subprocess,sys,zipfile
from pathlib import Path
from tools.common import ROOT,TOOLCHAIN,save


def run():
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    export=ROOT/'.tools'/'reproduce'/commit[:12]
    if export.exists():raise RuntimeError('This source export already exists; use its saved reproduction report or a new commit')
    raw=subprocess.run(['git','archive','--format=zip','HEAD'],cwd=ROOT,capture_output=True,check=True).stdout
    export.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for item in archive.infolist():
            if not (export/item.filename).resolve().is_relative_to(export.resolve()):raise RuntimeError('Source archive path escapes export')
        archive.extractall(export)
    py=ROOT/'.tools'/'repro-venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not py.exists():raise RuntimeError('Create the clean reproduction venv and install requirements first')
    env=dict(os.environ,SAR_ADC_TOOLCHAIN=str(TOOLCHAIN.resolve()))
    checks=[]
    for name,args in [('unit',['-m','pytest','-q']),('rtl',['-m','tools.verify_rtl','--quick'])]:
        r=subprocess.run([str(py)]+args,cwd=export,env=env,capture_output=True,text=True,timeout=180)
        (ROOT/f'results/reproduction-{name}.txt').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        checks.append({'name':name,'passed':r.returncode==0,'output':r.stdout[-1500:]})
        if r.returncode:raise RuntimeError('Clean-source '+name+' test failed: '+(r.stdout+r.stderr)[-2000:])
    freeze=subprocess.run([str(py),'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout
    (ROOT/'requirements-tested.txt').write_text(freeze,encoding='utf-8')
    result={'status':'passed','source_commit':commit,'source_archive_sha256':hashlib.sha256(raw).hexdigest(),
            'environment':'New Python virtual environment installed from requirements.txt; shared portable Icarus toolchain',
            'checks':checks,'packages':freeze.splitlines()}
    save('results/reproduction.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
