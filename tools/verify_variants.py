import numpy as np
from tb.bridge import Bridge
from model.ideal_adc import quantize,LSB
from tools.generate_variants import run as generate
from tools.common import save


def run():
    path=generate();values=list(-.5+(np.arange(256)+.5)*LSB)
    values.extend(np.random.default_rng(300).uniform(-.55,.55,512))
    with Bridge(rtl_source=str(path)) as bridge:
        bridge.reset()
        for v in values:
            code,trace,latency=bridge.convert(float(v),busy_starts=True)
            assert code==quantize(v) and latency==31
            assert len([s for s in trace if s['evaluate']])==8
        for state in range(1,7):
            bridge.reset();bridge.step(start=1)
            for _ in range(40):
                if bridge.snapshot.state==state:break
                bridge.step(cmp=1)
            assert bridge.snapshot.state==state
            bridge.step(reset=0);assert bridge.snapshot.state==0 and not bridge.snapshot.valid
    result={'status':'passed','one_hot_conversions':len(values),'reset_states':list(range(1,7)),
            'latency_cycles':31,'source':'rtl/sar_controller_onehot.sv',
            'implementation':'Explicit one-hot state register with external debug decoding; no reliance on automatic recoding.'}
    save('results/synthesis/variant-verification.json',result)
    print(result)
    return result


if __name__=='__main__':run()
