import argparse,collections,json,time
import numpy as np
from model.ideal_adc import quantize,transitions,LSB
from model.sar_reference import convert
from tb.bridge import Bridge
from tools.common import ROOT,phase,save


def run(quick=False):
    rng=np.random.default_rng(20261019)
    points=list(-.5+(np.arange(256)+.5)*LSB)
    for v in transitions():points.extend([v-.001*LSB,v,v+.001*LSB])
    points.extend(rng.uniform(-.6,.6,100 if quick else 10000))
    states=set();edges=set();outcomes=set();latencies=set();trace_examples=[]
    t0=time.time()
    with Bridge(waves=True) as b:
        b.reset()
        for i,v in enumerate(points):
            code,trace,latency=b.convert(float(v),busy_starts=bool(i%2))
            assert code==quantize(v),(i,v,code,quantize(v))
            assert len([s for s in trace if s['evaluate']])==8
            trials=[s['trial'] for s in trace if s['evaluate']]
            assert trials==[x.trial_code for x in convert(float(v))[1]]
            for a,z in zip(trace,trace[1:]):
                states.add(a['state']);edges.add((a['state'],z['state']))
                if a['state'] in (3,4):assert a['trial']==z['trial']
                assert not (a['evaluate'] and a['clamp'])
            for s in trace:
                states.add(s['state'])
                if s['evaluate']:outcomes.add((s['bit'],int(v>=(-.5+s['trial']/256))))
            latencies.add(latency)
            assert latency==31
            if i in (0,127,128,255):trace_examples.append({'input_v':float(v),'code':code,'trace':trace})
            # DONE pulse lasts one cycle; output must remain stable when idle.
            b.step();assert not b.snapshot.valid and b.snapshot.data==code
        # Each of the 256 independent eight-decision sequences must reach its code.
        for pattern in range(256):
            code,_,_=b.convert(0,decision=lambda s,p=pattern:bool(p&(1<<s.bit)))
            assert code==pattern
            b.step()
        reset_states=[]
        for target in range(1,7):
            b.reset();b.step(start=1)
            for _ in range(40):
                if b.snapshot.state==target:break
                b.step(cmp=1)
            assert b.snapshot.state==target
            b.step(reset=0);assert b.snapshot.state==0 and not b.snapshot.valid
            b.step();assert not b.snapshot.valid
            code,_,_=b.convert(.123);assert code==quantize(.123)
            b.step();reset_states.append(target)
        # Continuous requests: no extra IDLE bubble, measured from accepted starts.
        b.reset();accept=[];done=[]
        for _ in range(32*20+3):
            s=b.snapshot
            if s.ready:accept.append(s.cycle)
            if s.valid:done.append(s.cycle)
            b.step(start=1,cmp=(.123>=(-.5+s.trial/256)))
        assert set(np.diff(accept))=={32},accept
        assert set(np.diff(done))=={32}
        assert len(outcomes)==16
    save('results/rtl-traces.json',trace_examples)
    result=phase(3,'Real RTL controller verification',[
        {'name':'ideal input and bit-trace equivalence','passed':True,'conversions':len(points)},
        {'name':'all comparator decision sequences','passed':True,'patterns':256},
        {'name':'reset in every non-idle state and recovery','passed':True,'states':reset_states},
        {'name':'all bit retain/clear outcomes','passed':len(outcomes)==16,'covered':len(outcomes)},
        {'name':'32-clock sustained initiation interval','passed':True,'clock_hz':3200000,'sample_rate_hz':100000},
        {'name':'output stability, one-cycle valid, trial stability, busy-start handling','passed':True}],
        {'latency_cycles':sorted(latencies),'fsm_states':sorted(states|{0}),
         'state_transitions':[list(x) for x in sorted(edges)],'wall_seconds':time.time()-t0,
         'simulator':'Icarus Verilog; actual synthesizable RTL with line-oriented closed-loop Python bridge',
         'deviation_from_plan':'Portable line protocol replaces cocotb/VPI; same actual RTL is observed and driven each cycle.'})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');a=p.parse_args();run(a.quick)
