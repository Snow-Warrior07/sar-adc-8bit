"""Run only on the online Linux runner: no local native circuit measurements."""
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
from tools.common import ROOT,save
from tools.generate_circuits import run as generate

MODEL_REV='75594eec516be3087e64eeb5347a958de70f410c'
MODEL_URL='https://raw.githubusercontent.com/eelab-dev/EEcircuit-engine/'+MODEL_REV+'/src/models/skywater/'


def models(folder):
    parts=[];hashes={}
    for name in ['params','nfet18','pfet18','pfet18_hvt']:
        with urllib.request.urlopen(MODEL_URL+name+'.ts',timeout=60) as r:raw=r.read()
        s=raw.decode();body=s[s.index('`')+1:s.rindex('`')]
        if '${' in body:raise RuntimeError('Unexpected template interpolation in model source')
        parts.append(body);hashes[name]=hashlib.sha256(raw).hexdigest()
    (folder/'modelcard.skywater').write_text('\n'.join(parts),encoding='utf-8')
    return {'repository':'https://github.com/eelab-dev/EEcircuit-engine','revision':MODEL_REV,'source_sha256':hashes,
            'coverage':'EEcircuit SKY130 port; nominal model; no foundry process-corner or mismatch qualification',
            'license':'SkyWater model portions Apache-2.0; upstream conversion/engine attribution retained'}


def measurements(text):
    return {m.group(1):float(m.group(2)) for m in re.finditer(r'^\s*([a-zA-Z][\w]*)\s*=\s*([-+\d.]+(?:e[-+]?\d+)?)',text,re.M|re.I)}


def run():
    generate();folder=ROOT/'analog'/'spice';dest=ROOT/'results'/'online-cloud';dest.mkdir(parents=True,exist_ok=True)
    provenance=models(folder);reports={}
    version=subprocess.run(['ngspice','--version'],capture_output=True,text=True,check=True).stdout
    for path in sorted(folder.glob('*.cir')):
        r=subprocess.run(['ngspice','-b',path.name],cwd=folder,capture_output=True,text=True,timeout=120)
        log=r.stdout+'\n'+r.stderr
        (dest/(path.stem+'.txt')).write_text(log,encoding='utf-8')
        vals=measurements(log)
        reports[path.name]={'returncode':r.returncode,'measurements':vals,'netlist_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        print(path.name,'exit',r.returncode,'measurements',len(vals),flush=True)
        if r.returncode or not vals:raise RuntimeError('Online circuit bench failed: '+path.name+'\n'+log[-2000:])
    save('results/online-cloud/summary.json',{'execution':'GitHub-hosted Ubuntu online runner','engine':version,
                                           'models':provenance,'benches':reports})


if __name__=='__main__':run()
