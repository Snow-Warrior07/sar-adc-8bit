import csv,hashlib,json,re
from pathlib import Path
from analysis.metrics import spectral_metrics,static_metrics
from model.ideal_adc import reconstruct
from tools.common import ROOT,save,phase
from tools.report import run as report


def run():
    gates=[json.loads((ROOT/f'results/phases/phase-{i:02d}.json').read_text()) for i in range(9)]
    if any(g['status']!='passed' for g in gates):raise RuntimeError('Required engineering phase remains failed or pending')
    reproduction=json.loads((ROOT/'results/reproduction.json').read_text())
    assert reproduction['status']=='passed'
    char=json.loads((ROOT/'results/characterization.json').read_text())
    config=json.loads((ROOT/'config/spice-characterized.json').read_text())
    assert char['configuration']==config,'Characterization is stale relative to the calibrated model'
    for suffix,k,key in [('low',41,'dynamic_low'),('high',821,'dynamic_high')]:
        with (ROOT/f'results/dynamic-{suffix}.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==4096
        assert [int(r['sample']) for r in rows]==list(range(4096))
        codes=[int(r['code']) for r in rows]
        assert all(0<=q<=255 for q in codes)
        metric=spectral_metrics(reconstruct(codes),100000,k)
        assert abs(metric['enob']-char[key]['enob'])<1e-9
    sm=static_metrics(char['static']['transition_v'])
    assert abs(sm['max_abs_inl_lsb']-char['static']['max_abs_inl_lsb'])<1e-9
    spice=json.loads((ROOT/'results/online-cloud/summary.json').read_text())
    for name,data in spice['benches'].items():
        raw=(ROOT/'analog/spice'/name).read_bytes().replace(b'\r\n',b'\n')
        assert hashlib.sha256(raw).hexdigest()==data['netlist_sha256'],f'Circuit source changed after online run: {name}'
    save('results/phases/phase-09.json',{'phase':9,'name':'Clean reproduction and release audit','status':'pending','checks':[]})
    report()
    count=0
    for p in [ROOT/'README.md',ROOT/'report/engineering-report.md',ROOT/'docs/PHASE_RESULTS.md']:
        text=p.read_text(encoding='utf-8')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            if re.match(r'^[a-z]+:',target) or target.startswith('#'):continue
            path=(p.parent/target.split('#')[0]).resolve()
            assert path.is_relative_to(ROOT.resolve()) and path.exists(),(p.name,target)
            count+=1
    result=phase(9,'Clean reproduction and release audit',[
        {'name':'all prior engineering gates passed','passed':True,'phases':list(range(9))},
        {'name':'clean-source, clean-Python unit and actual-RTL reproduction','passed':True,'source_commit':reproduction['source_commit']},
        {'name':'published CSVs reproduce the saved FFT metrics','passed':True,'records':2,'samples_each':4096},
        {'name':'online executed netlist hashes match release circuits','passed':True,'circuits':len(spice['benches'])},
        {'name':'README/report/phase-index local links resolve','passed':True,'links_checked':count}],
        {'scope':'Engineering release audit; profile/portfolio integration and final GitHub publication follow this gate.'})
    report()
    return result


if __name__=='__main__':run()
