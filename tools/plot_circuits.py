"""Plot actual online circuit measurements, separately from system-model results."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tools.common import ROOT


def run():
    data=json.loads((ROOT/'results/online-cloud/summary.json').read_text())['benches']
    manifest=json.loads((ROOT/'analog/spice/manifest.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
    for temp,color in [(0,'#476a9c'),(27,'#087f8c'),(85,'#b46b19')]:
        name=f'comparator-{temp}c.cir';cases=manifest[name][:5];m=data[name]['measurements']
        x=[c['differential_v']*1000 for c in cases]
        y=[m[f"delay_{c['index']}"]*1e9 for c in cases]
        axes[0].semilogx(x,y,'o-',label=f'{temp} C',color=color)
    axes[0].set(xlabel='Positive differential overdrive (mV)',ylabel='Comparator decision delay (ns)',
                title='SKY130 comparator: VCM 0.9 V, VDD 1.8 V')
    axes[0].legend(title='Temperature')
    cases=manifest['cdac-mos.cir'];m=data['cdac-mos.cir']['measurements'];errors=[]
    for c in cases:
        i=c['index'];errors.append((m[f'tp_{i}']-m[f'tn_{i}']-c['expected_residual_v'])*1e6)
    axes[1].bar(range(len(cases)),errors,color='#087f8c')
    axes[1].axhline(0,color='#666666',lw=.8)
    axes[1].set_xticks(range(len(cases)),[str(c['code']) for c in cases])
    axes[1].set(xlabel='CDAC trial code (six sampled-input cases)',ylabel='Differential residual error (uV)',
                title='MOS sampling clamps versus ideal charge equation')
    for a in axes:a.spines['top'].set_visible(False);a.spines['right'].set_visible(False)
    fig.suptitle('Online ngspice circuit measurements | nominal SKY130 port',fontsize=14)
    fig.savefig(ROOT/'report/figures/online-circuit-characterization.png',dpi=160);plt.close(fig)
    print('Online circuit figure generated from saved ngspice measurements')


if __name__=='__main__':run()
