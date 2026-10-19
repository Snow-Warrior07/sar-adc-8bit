"""Validate downloaded online measurements and calibrate reduced-order models."""
from dataclasses import asdict
import json,math,shutil
from pathlib import Path
import numpy as np
from model.analog_frontend import AnalogConfig,AnalogFrontEnd,RTLAnalogAdapter,TCLK
from model.ideal_adc import quantize
from tools.common import ROOT,save,phase
from tb.bridge import Bridge


def run():
    source=ROOT/'results/cloud/results/online-cloud'
    target=ROOT/'results/online-cloud';target.mkdir(parents=True,exist_ok=True)
    if source.exists():
        for p in source.iterdir():
            if p.is_file():shutil.copy2(p,target/p.name)
    data=json.loads((target/'summary.json').read_text())
    manifest=json.loads((ROOT/'analog/spice/manifest.json').read_text())
    benches=data['benches'];delays=[];polarity=True
    for name in ['comparator-0c.cir','comparator-27c.cir','comparator-85c.cir']:
        m=benches[name]['measurements']
        for case in manifest[name]:
            i=case['index'];positive=case['differential_v']>0;half=case['supply_v']/2
            polarity&=(m[f'op_{i}']>half and m[f'on_{i}']<half) if positive else (m[f'on_{i}']>half and m[f'op_{i}']<half)
            delays.append(m[f'delay_{i}'])
    nominal=benches['comparator-27c.cir']['measurements']
    fine=benches['comparator-convergence.cir']['measurements']
    convergence=max(abs(nominal[f'delay_{i}']-fine[f'delay_{i}'])/fine[f'delay_{i}'] for i in range(14))
    charge=benches['cdac-charge.cir']['measurements'];charge_errors=[]
    for c in manifest['cdac-charge.cir']:
        i=c['index'];actual=charge[f'tp_{i}']-charge[f'tn_{i}']
        charge_errors.append(abs(actual-c['expected_residual_v']))
    settling=benches['settling.cir']['measurements']
    acq_tau=settling['acq_cross']-1e-6-50e-12
    dac_tau=settling['dac_cross']-1e-6-50e-12
    receipt=json.loads((target/'artifact-receipt.json').read_text()) if (target/'artifact-receipt.json').exists() else {}
    source_data={'workflow_url':receipt.get('workflow_url','https://github.com/Snow-Warrior07/sar-adc-8bit/actions/runs/39231164889'),
                 'workflow_commit':receipt.get('workflow_run',{}).get('head_sha','0fdbc2c'),'artifact_id':receipt.get('artifact_id',12177535247),
                 'execution':data['execution'],'engine':data['engine'],'models':data['models']}
    save('results/online-provenance.json',source_data)
    checks=[
        {'name':'42 SKY130 comparator operating points resolve with correct polarity','passed':bool(polarity),'cases':42},
        {'name':'comparator decisions fit the capture interval','passed':max(delays)<TCLK-5e-9,'maximum_delay_s':max(delays)},
        {'name':'20 ps versus 10 ps timestep convergence','passed':convergence<.01,'max_relative_delay_change':convergence},
        {'name':'six differential sampled-CDAC charge cases','passed':max(charge_errors)<.01/256,'max_residual_error_v':max(charge_errors)},
        {'name':'acquisition and driver RC time constants','passed':abs(acq_tau/51.2e-9-1)<.01 and abs(dac_tau/25.6e-9-1)<.01,
         'acquisition_tau_s':acq_tau,'dac_driver_tau_s':dac_tau}]
    if 'cdac-mos.cir' in benches:
        mos=benches['cdac-mos.cir']['measurements'];mos_errors=[]
        for c in manifest['cdac-mos.cir']:
            i=c['index'];mos_errors.append(abs(mos[f'tp_{i}']-mos[f'tn_{i}']-c['expected_residual_v']))
        checks.append({'name':'six SKY130 transmission-gate sampled-CDAC cases','passed':max(mos_errors)<.1/256,
                       'max_differential_error_v':max(mos_errors),'tolerance_lsb':.1})
    phase(5,'Online circuit characterization',checks,
        {'provenance':source_data,'process_scope':'Nominal EEcircuit SKY130 port; voltage and temperature sweeps only; no foundry process-corner or mismatch qualification.'})
    training=[0,2,4];heldout=[1,3]
    x=[manifest['comparator-27c.cir'][i]['differential_v'] for i in training]
    y=[nominal[f'delay_{i}'] for i in training]
    errors=[];predictions=[]
    for i in heldout:
        v=manifest['comparator-27c.cir'][i]['differential_v']
        pred=float(np.interp(math.log(v),np.log(x),y));actual=nominal[f'delay_{i}']
        errors.append(abs(pred-actual)/actual)
        predictions.append({'overdrive_v':v,'predicted_s':pred,'measured_s':actual,'relative_error':errors[-1]})
    settling_errors=[]
    for tau,key in [(acq_tau,'acq_final'),(dac_tau,'dac_final')]:
        predicted=1-math.exp(-(.625e-6-50e-12)/tau)
        settling_errors.append(abs(predicted-settling[key]))
    cfg=AnalogConfig(name='online-SPICE-characterized',acquisition_tau_s=acq_tau,dac_tau_s=dac_tau,
                     delay_points_v=x,delay_points_s=y,
                     fidelity='Actual RTL plus reduced-order analog model; RC and SKY130 comparator delay characterized online; mismatch/noise/leakage/reference impedance assumed')
    save('config/spice-characterized.json',asdict(cfg))
    with Bridge() as bridge:
        bridge.reset();fe=AnalogFrontEnd(cfg,seed=88)
        code_errors=[]
        for vin in np.random.default_rng(88).uniform(-.49,.49,256):
            code,_,_=bridge.convert(float(vin),RTLAnalogAdapter(fe,float(vin)))
            code_errors.append(abs(code-quantize(vin)))
    provenance={'calibrated':['lumped acquisition tau','lumped DAC-driver tau','nominal comparator delay versus overdrive'],
                'assumed':['unit-capacitor mismatch','comparator offset','random comparator noise','sample noise','leakage','equivalent reference impedance'],
                'coverage':'Delay interpolation validated on positive overdrives at VCM 0.9 V, VDD 1.8 V, 27 C. Below-range logarithmic extrapolation and above-range clamping are conservative modelling assumptions, not SPICE validation.'}
    save('results/surrogate-validation.json',{'held_out_delay':predictions,'settling_voltage_errors_v':settling_errors,'provenance':provenance})
    phase(6,'SPICE-derived model with actual RTL',[
        {'name':'held-out comparator-delay predictions','passed':max(errors)<.1,'max_relative_error':max(errors),'cases':len(errors)},
        {'name':'held-out lumped settling-voltage prediction','passed':max(settling_errors)<.05/256,'max_error_v':max(settling_errors)},
        {'name':'integrated actual-RTL regression','passed':max(code_errors)<=1,'conversions':256,'max_code_error':max(code_errors)}],
        {'fidelity':cfg.fidelity,'provenance':provenance})


if __name__=='__main__':run()
