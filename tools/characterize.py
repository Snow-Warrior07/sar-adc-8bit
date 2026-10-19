"""Static and dynamic ADC measurements; dynamic records run actual RTL."""
from dataclasses import asdict,replace
import csv,json,math,time
from pathlib import Path
import numpy as np
from analysis.metrics import static_metrics,spectral_metrics
from model.ideal_adc import LSB,reconstruct,quantize,transitions
from model.analog_frontend import AnalogConfig,AnalogFrontEnd,RTLAnalogAdapter,TCLK
from tb.bridge import Bridge
from tools.common import ROOT,save,phase


def configuration():
    path=ROOT/'config/spice-characterized.json'
    return AnalogConfig(**json.loads(path.read_text())) if path.exists() else AnalogConfig()


def static_test(config):
    cfg=replace(config,comparator_noise_rms_v=0,sample_noise_rms_v=0)
    fe=AnalogFrontEnd(cfg,seed=20261019)
    estimates=[]
    for k in range(1,256):
        lo=-.6;hi=.6
        for _ in range(21):
            mid=(lo+hi)/2
            # Repeated identical inputs condition the reference/sampling memory.
            fe.convert(mid);fe.convert(mid);code=fe.convert(mid)
            if code>=k:hi=mid
            else:lo=mid
        estimates.append((lo+hi)/2)
    metrics=static_metrics(estimates)
    sweep=np.linspace(-.5,.5,2049)
    codes=[fe.convert(float(v)) for v in sweep]
    metrics.update(transition_v=estimates,sweep_v=sweep.tolist(),sweep_code=codes,
                   all_codes_observed=len(set(codes))==256,
                   measured_monotonic=bool(np.all(np.diff(codes)>=0)),
                   random_noise_disabled_for_transition_estimation=True)
    return metrics


def dynamic_test(config,k,n=4096):
    amplitude=.5*10**(-.5/20);fs=100000;frequency=k*fs/n
    signal=lambda t:amplitude*math.sin(2*math.pi*frequency*t)
    fe=AnalogFrontEnd(config,seed=1000+k);codes=[];inputs=[]
    with Bridge() as b:
        b.reset()
        for j in range(n+64):
            sample_time=(j*32+6)*TCLK
            vin=signal(sample_time)
            code,_,_=b.convert(vin,RTLAnalogAdapter(fe,vin,signal,sample_time))
            if j>=64:codes.append(code);inputs.append(vin)
    m=spectral_metrics(reconstruct(codes),fs,k)
    m.update(fidelity=config.fidelity,rtl_in_loop=True,late_decisions=fe.timeouts)
    path=ROOT/'results'/('dynamic-low.csv' if k==41 else 'dynamic-high.csv')
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['sample','input_differential_v','code','reconstructed_v'])
        w.writerows((i,v,c,reconstruct(c)) for i,(v,c) in enumerate(zip(inputs,codes)))
    return m


def mismatch_sensitivity():
    results=[]
    for sigma in [0,.001,.0025,.005,.01]:
        rows=[]
        for seed in range(200):
            cfg=AnalogConfig.ideal();cfg.mismatch_sigma=sigma
            fe=AnalogFrontEnd(cfg,seed=seed)
            # Isolated static capacitor mismatch: no noise, leakage, RC or offset.
            t=[fe.dac_target(k) for k in range(1,256)]
            m=static_metrics(t)
            rows.append([m['max_abs_dnl_lsb'],m['max_abs_inl_lsb']])
        a=np.asarray(rows)
        results.append(dict(unit_sigma_fraction=sigma,instances=200,
                            max_abs_dnl_lsb=float(a[:,0].max()),max_abs_inl_lsb=float(a[:,1].max()),
                            p95_abs_inl_lsb=float(np.percentile(a[:,1],95)),
                            target_passing_instances=int(np.sum((a[:,0]<=.75)&(a[:,1]<=1)))))
    return {'assumption':'Independent unit-capacitor Gaussian mismatch; fixed instance per seed. Sensitivity, not foundry yield.',
            'results':results}


def isolated_effects(config):
    values=np.linspace(-.49,.49,1001);rows=[]
    for name,field,levels in [
        ('comparator_offset','comparator_offset_v',[0,.5*LSB,2*LSB]),
        ('dac_settling','dac_tau_s',[0,25.6e-9,100e-9,500e-9]),
        ('acquisition','acquisition_tau_s',[0,51.2e-9,250e-9,1e-6]),
        ('hold_leakage','leakage_v_per_s',[0,10,100,1000])]:
        for value in levels:
            cfg=AnalogConfig.ideal();setattr(cfg,field,value);fe=AnalogFrontEnd(cfg,seed=7)
            out=np.array([fe.convert(float(v)) for v in values]);error=out-quantize(values)
            rows.append({'effect':name,'parameter':field,'value':value,
                         'max_code_difference':int(np.max(np.abs(error))),
                         'mean_code_difference':float(np.mean(error)),
                         'different_codes':int(np.count_nonzero(error))})
    return rows


def plots(result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=ROOT/'report'/'figures';folder.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    static=result['static'];low=result['dynamic_low'];high=result['dynamic_high']
    fig,ax=plt.subplots(2,2,figsize=(12,7.5),layout='constrained')
    ax[0,0].step(static['sweep_v'],static['sweep_code'],where='post',color='#087f8c');ax[0,0].set(xlabel='Differential input (V)',ylabel='Output code',title='Transfer curve: nominal model')
    ax[0,1].plot(range(1,255),static['dnl_lsb'],color='#b46b19',label='DNL')
    ax[0,1].plot(range(1,256),static['inl_lsb'],color='#087f8c',label='Endpoint INL');ax[0,1].legend();ax[0,1].set(xlabel='Code / transition',ylabel='Error (LSB)',title='Static linearity; random noise disabled')
    for a,m,title in [(ax[1,0],low,'Low-frequency coherent sine'),(ax[1,1],high,'Higher-frequency coherent sine')]:
        f=np.arange(len(m['spectrum_dbfs']))*100000/m['samples']
        a.plot(f/1000,m['spectrum_dbfs'],lw=.7,color='#087f8c')
        a.set(xlabel='Frequency (kHz)',ylabel='Power per bin (dBFS)',ylim=(-120,0),title=f"{title}\nENOB {m['enob']:.3f}; SINAD {m['sinad_db']:.2f} dB")
    fig.suptitle('8-bit differential SAR ADC | actual RTL with a characterized analog model',fontsize=15)
    fig.savefig(folder/'adc-characterization.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    rows=result['mismatch']['results']
    ax.plot([x['unit_sigma_fraction']*100 for x in rows],[x['max_abs_inl_lsb'] for x in rows],marker='o',color='#087f8c')
    ax.set(xlabel='Assumed unit-capacitor mismatch sigma (%)',ylabel='Maximum |INL| across 200 instances (LSB)',title='Capacitor mismatch sensitivity; behavioural assumptions')
    fig.savefig(folder/'mismatch-sensitivity.png',dpi=160);plt.close(fig)


def run():
    t=time.time();cfg=configuration();print('Static characterization',flush=True)
    static=static_test(cfg);print('Low-frequency actual-RTL record',flush=True)
    low=dynamic_test(cfg,41);print('High-frequency actual-RTL record',flush=True)
    high=dynamic_test(cfg,821);print('Sensitivity experiments',flush=True)
    result={'configuration':asdict(cfg),'static':static,'dynamic_low':low,'dynamic_high':high,
            'mismatch':mismatch_sensitivity(),'isolated_effects':isolated_effects(cfg)}
    save('results/characterization.json',result);plots(result)
    phase(7,'Static, dynamic and sensitivity characterization',[
        {'name':'nominal static DNL target','passed':static['max_abs_dnl_lsb']<=.75,'measured_lsb':static['max_abs_dnl_lsb']},
        {'name':'nominal endpoint INL target','passed':static['max_abs_inl_lsb']<=1,'measured_lsb':static['max_abs_inl_lsb']},
        {'name':'monotonic and all 256 codes observed','passed':static['measured_monotonic'] and static['all_codes_observed']},
        {'name':'low-frequency uncorrected ENOB target','passed':low['enob']>=7,'enob':low['enob'],'sinad_db':low['sinad_db']},
        {'name':'both dynamic records use actual RTL','passed':low['rtl_in_loop'] and high['rtl_in_loop'],'samples_per_record':4096}],
        {'wall_seconds':time.time()-t,'higher_frequency_enob':high['enob'],'fidelity':cfg.fidelity})


if __name__=='__main__':run()
