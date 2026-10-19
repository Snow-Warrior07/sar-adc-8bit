import json,math,subprocess,sys
from pathlib import Path
import yaml
from model.ideal_adc import LSB,quantize
from model.sar_reference import convert,top_plates
from tools.common import ROOT,phase,save,executable,tool_env


def run():
    versions={}
    for name,flag in [('iverilog','-V'),('yosys','-V')]:
        p=subprocess.run([executable(name),flag],env=tool_env(),capture_output=True,text=True,timeout=30)
        versions[name]=(p.stdout+p.stderr).splitlines()[0]
        assert p.returncode==0
    rc=(ROOT/'results/online/rc-smoke.txt').read_text()
    assert '2.00050e-06' in rc and '9.996644e-01' in rc
    tau=2.00050e-6-1e-6
    phase(0,'Tools and online circuit smoke test',[
        {'name':'Icarus and Yosys start','passed':True,'versions':versions},
        {'name':'online ngspice RC time constant','passed':abs(tau-1e-6)<.01e-6,
         'measured_tau_s':tau,'expected_tau_s':1e-6,'relative_error_percent':100*(tau/1e-6-1),
         'source':'results/online/rc-smoke.txt','execution':'https://gen1.eecircuit.com/; ngspice-45.2 WASM'}])
    spec=yaml.safe_load((ROOT/'config/spec.yaml').read_text())
    clocks=spec['acquisition_cycles']+spec['hold_cycles']+8*spec['cycles_per_bit']+spec['done_cycles']
    assert clocks==32 and spec['clock_hz']/clocks==spec['sample_rate_hz']
    traces=[]
    for vin in [-.49,-.125,0,.183,.49]:
        q,trace=convert(vin);assert q==quantize(vin)
        for code in range(256):
            p,n=top_plates(vin,code);assert math.isclose(p-n,-.5+code/256-vin,abs_tol=1e-14)
        traces.append({'input_v':vin,'code':q,'trials':[vars(x) for x in trace]})
    save('results/reference-traces.json',traces)
    phase(1,'Specification, charge equations and timing contract',[
        {'name':'32-clock frame and 100 kS/s arithmetic','passed':True,'clocks':clocks},
        {'name':'differential charge equation and polarity','passed':True,'points':5*256},
        {'name':'five independent reference traces','passed':True}],
        {'specification':spec,'lsb_v':LSB})
    result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_reference.py','--junitxml=results/reference-tests.xml'],cwd=ROOT,capture_output=True,text=True)
    (ROOT/'results/reference-tests.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    phase(2,'Independent reference and analysis validation',[
        {'name':'reference, charge, static and FFT tests','passed':result.returncode==0,'output':result.stdout.strip()}])
    if result.returncode:raise RuntimeError('Reference tests failed')


if __name__=='__main__':run()
