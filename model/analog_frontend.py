"""Stateful reduced-order differential sampler/CDAC/comparator model.

Capacitor errors are fixed unit realizations. Noise is sampled once per physical
event. The reference network is an equivalent differential RC approximation.
"""
from dataclasses import dataclass,asdict
import math
import numpy as np

TCLK=1/3200000
LSB=1/256


@dataclass
class AnalogConfig:
    name:str='nominal-behavioural'
    unit_cap_f:float=20e-15
    mismatch_sigma:float=.0025
    acquisition_tau_s:float=51.2e-9
    dac_tau_s:float=25.6e-9
    comparator_offset_v:float=.00035
    comparator_noise_rms_v:float=.00025
    sample_noise_rms_v:float=40.224e-6
    leakage_v_per_s:float=10.0
    reference_r_ohm:float=10.0
    reference_c_f:float=100e-9
    delay_base_s:float=0.0
    delay_log_s:float=0.0
    delay_floor_v:float=1e-6
    capture_margin_s:float=5e-9
    fidelity:str='behavioural; parameters explicitly assumed'

    @classmethod
    def ideal(cls):
        return cls(name='ideal',mismatch_sigma=0,acquisition_tau_s=0,dac_tau_s=0,
                   comparator_offset_v=0,comparator_noise_rms_v=0,sample_noise_rms_v=0,
                   leakage_v_per_s=0,reference_r_ohm=0,delay_base_s=0,delay_log_s=0,
                   fidelity='ideal behavioural')


class AnalogFrontEnd:
    def __init__(self,config=None,seed=20261019):
        self.config=config or AnalogConfig()
        self.rng=np.random.default_rng(seed)
        self.seed=seed
        units=1+self.rng.normal(0,self.config.mismatch_sigma,(2,256))
        if np.any(units<=0):raise ValueError('Nonpositive unit capacitor')
        groups=[]
        for row in units:
            cursor=0;g=[]
            for bit in range(8):
                m=1<<bit;g.append(float(np.sum(row[cursor:cursor+m])));cursor+=m
            g.append(float(row[-1]));groups.append(g)
        self.weights=np.asarray(groups)
        self.total=np.sum(self.weights,axis=1)
        self.track=0.;self.dac_state=0.;self.reference_scale=1.;self.previous_code=128
        self.sampled=0.;self.timeouts=0;self.last_delay=0.;self.last_residual=0.

    def acquire(self,vin,signal=None,sample_time_s=0):
        c=self.config;duration=6*TCLK
        if signal is None:
            self.track=float(vin)+(self.track-float(vin))*math.exp(-duration/c.acquisition_tau_s) if c.acquisition_tau_s else float(vin)
        elif not c.acquisition_tau_s:self.track=float(signal(sample_time_s))
        else:
            # Exact first-order update for a piecewise constant midpoint drive.
            dt=duration/64;alpha=math.exp(-dt/c.acquisition_tau_s)
            for j in range(64):
                target=float(signal(sample_time_s-duration+(j+.5)*dt))
                self.track=target+(self.track-target)*alpha
        self.sampled=self.track+self.rng.normal(0,c.sample_noise_rms_v)
        self.dac_state=self.sampled # Zero differential residual at top-clamp release.
        self.previous_code=128
        if c.reference_r_ohm:
            self.reference_scale=1+(self.reference_scale-1)*math.exp(-duration/(c.reference_r_ohm*c.reference_c_f))
        else:self.reference_scale=1.

    def dac_target(self,code):
        if self.config.mismatch_sigma==0:return (-.5+code/256)*self.reference_scale
        b=np.array([(code>>i)&1 for i in range(8)]+[0],dtype=float)
        # Both dummy connections are included; totals normalize each physical array.
        return .5*self.reference_scale*(np.dot(self.weights[0],b)/self.total[0]
                                       +np.dot(self.weights[1],b)/self.total[1]-1)

    def decision(self,code,bit):
        c=self.config
        if c.reference_r_ohm:
            tau=c.reference_r_ohm*c.reference_c_f
            self.reference_scale=1+(self.reference_scale-1)*math.exp(-3*TCLK/tau)
            toggles=(code^self.previous_code).bit_count()
            switched=sum((1<<i) for i in range(8) if (code^self.previous_code)&(1<<i))
            charge=switched*c.unit_cap_f*.5
            self.reference_scale-=2*charge/c.reference_c_f*math.exp(-2*TCLK/tau)
        self.previous_code=code
        target=self.dac_target(code)
        a=math.exp(-2*TCLK/c.dac_tau_s) if c.dac_tau_s else 0
        self.dac_state=target+(self.dac_state-target)*a
        age=(1+3*(7-bit)+2)*TCLK
        held=self.sampled-c.leakage_v_per_s*age
        noise=self.rng.normal(0,c.comparator_noise_rms_v)
        residual=held-self.dac_state+c.comparator_offset_v+noise
        self.last_residual=residual
        overdrive=max(abs(residual),c.delay_floor_v)
        self.last_delay=c.delay_base_s+c.delay_log_s*max(0.,math.log(LSB/overdrive))
        if self.last_delay>TCLK-c.capture_margin_s:
            self.timeouts+=1
            raise TimeoutError('Comparator decision exceeds its capture deadline')
        return int(residual>=0)

    def convert(self,vin,signal=None,sample_time_s=0):
        self.acquire(vin,signal,sample_time_s)
        code=0
        for bit in reversed(range(8)):
            trial=code|(1<<bit)
            if self.decision(trial,bit):code=trial
        return code


class RTLAnalogAdapter:
    """Generate one comparator decision per EVAL from actual observed RTL trials."""
    def __init__(self,frontend,vin,signal=None,sample_time_s=0):
        self.frontend=frontend;self.vin=vin;self.signal=signal;self.sample_time=sample_time_s
        self.acquired=False;self.last_bit=None;self.last_decision=0

    def __call__(self,snapshot):
        if snapshot.state==2 and not self.acquired:
            self.frontend.acquire(self.vin,self.signal,self.sample_time);self.acquired=True
        if snapshot.evaluate and snapshot.bit!=self.last_bit:
            assert self.acquired,'Comparator evaluated before sampling'
            self.last_decision=self.frontend.decision(snapshot.trial,snapshot.bit)
            self.last_bit=snapshot.bit
        return self.last_decision
