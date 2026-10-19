"""Generate self-contained benches for an online ngspice-compatible service."""
from pathlib import Path
from tools.common import ROOT,save

COMPARATOR='''
.subckt comparator ip inn clk vdd op on
Xtail0 tail clk 0 0 sky130_fd_pr__nfet_01v8 W=1.68u L=0.15u
Xtail1 tail clk 0 0 sky130_fd_pr__nfet_01v8 W=1.68u L=0.15u
X1 xp ip tail 0 sky130_fd_pr__nfet_01v8 W=1.68u L=0.15u
X2 xn inn tail 0 sky130_fd_pr__nfet_01v8 W=1.68u L=0.15u
Xn1 on op xp 0 sky130_fd_pr__nfet_01v8 W=1.26u L=0.15u
Xn2 op on xn 0 sky130_fd_pr__nfet_01v8 W=1.26u L=0.15u
Xp1 on op vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Xp2 op on vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Xr1 xp clk vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Xr2 xn clk vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Xr3 op clk vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Xr4 on clk vdd vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u
Cp op 0 20f
Cn on 0 20f
.ends comparator
'''


def comparator_deck(cases,temp=27,step='20p'):
    lines=['SKY130 comparator characterization','.include modelcard.skywater','.param mc_switch=0',f'.temp {temp}',COMPARATOR]
    manifest=[]
    for i,(vdiff,vcm,vdd) in enumerate(cases):
        suffix=str(i)
        lines.extend([f'Vdd{i} vdd{i} 0 {vdd}',f'Vip{i} ip{i} 0 {vcm+vdiff/2:.12g}',
                      f'Vin{i} in{i} 0 {vcm-vdiff/2:.12g}',
                      f'Vclk{i} clk{i} 0 PULSE(0 {vdd} 20n 100p 100p 20n 40n)',
                      f'Xc{i} ip{i} in{i} clk{i} vdd{i} op{i} on{i} comparator'])
        falling=f'on{i}' if vdiff>0 else f'op{i}'
        lines.extend([f'.meas tran delay_{i} TRIG v(clk{i}) VAL={vdd/2} RISE=1 TARG v({falling}) VAL={vdd/2} FALL=1',
                      f'.meas tran op_{i} FIND v(op{i}) AT=35n',f'.meas tran on_{i} FIND v(on{i}) AT=35n',
                      f'.meas tran charge_{i} INTEG i(Vdd{i}) FROM=20n TO=40n'])
        manifest.append(dict(index=i,differential_v=vdiff,common_mode_v=vcm,supply_v=vdd,temperature_c=temp))
    lines.extend([f'.tran {step} 80n','.end'])
    return '\n'.join(lines)+'\n',manifest


def cdac_deck():
    lines=['Differential sampled charge CDAC - ideal switches and capacitors',
           'Vcm cm 0 .9','Vtrack track 0 PWL(0 1.8 1.875u 1.8 1.876u 0)',
           '.model CLAMP SW(Ron=1 Roff=1e15 Vt=.9 Vh=.05)']
    manifest=[]
    for i,(vin,code) in enumerate([(-.49,0),(-.125,64),(0,127),(0,128),(.183,175),(.49,255)]):
        lines.extend([f'Sp{i} tp{i} cm track 0 CLAMP',f'Sn{i} tn{i} cm track 0 CLAMP',
                      f'Rp{i} tp{i} 0 1e14',f'Rn{i} tn{i} 0 1e14'])
        for bit in range(9):
            weight=(1<<bit) if bit<8 else 1
            high=bool(code&(1<<bit)) if bit<8 else False
            for side,initial,final in [('p',.9+vin/2,1.15 if high else .65),('n',.9-vin/2,.65 if high else 1.15)]:
                lines.extend([f'V{side}{i}_{bit} b{side}{i}_{bit} 0 PWL(0 {initial:.12g} 2u {initial:.12g} 2.005u {final})',
                              f'C{side}{i}_{bit} t{side}{i} b{side}{i}_{bit} {weight*20e-15:.12g}'])
        lines.extend([f'.meas tran tp_{i} FIND v(tp{i}) AT=2.625u',f'.meas tran tn_{i} FIND v(tn{i}) AT=2.625u'])
        manifest.append(dict(index=i,input_v=vin,code=code,expected_residual_v=-.5+code/256-vin))
    lines.extend(['.tran 1n 3u','.end'])
    return '\n'.join(lines)+'\n',manifest


def settling_deck():
    return '''Lumped acquisition and DAC-driver settling characterization
Vstep in 0 PULSE(0 1 1u 100p 100p 5u 10u)
Racq in aq 10k
Cacq aq 0 5.12p
Rdac in dq 5k
Cdac dq 0 5.12p
.tran 100p 2u
.meas tran acq_cross WHEN v(aq)=0.632120559 RISE=1
.meas tran dac_cross WHEN v(dq)=0.632120559 RISE=1
.meas tran acq_final FIND v(aq) AT=1.625u
.meas tran dac_final FIND v(dq) AT=1.625u
.end
'''


def mos_cdac_deck():
    text,manifest=cdac_deck()
    text=text.replace('Differential sampled charge CDAC - ideal switches and capacitors',
                      'Differential sampled CDAC with SKY130 MOS top-plate clamps\n.include modelcard.skywater\n.param mc_switch=0\nVdd vdd 0 1.8\nVtrackbar trackbar 0 PWL(0 0 1.875u 0 1.876u 1.8)')
    text=text.replace('.model CLAMP SW(Ron=1 Roff=1e15 Vt=.9 Vh=.05)','* Matched NMOS/PMOS transmission gates; ideal capacitor/reference sources retained.')
    for i in range(len(manifest)):
        for side in ['p','n']:
            old=f'S{side}{i} t{side}{i} cm track 0 CLAMP'
            new=f'X{side}{i}n t{side}{i} cm track 0 sky130_fd_pr__nfet_01v8 W=1.26u L=0.15u\nX{side}{i}p t{side}{i} cm trackbar vdd sky130_fd_pr__pfet_01v8 W=1.26u L=0.15u'
            text=text.replace(old,new)
    return text,manifest


def run():
    folder=ROOT/'analog'/'spice';folder.mkdir(parents=True,exist_ok=True)
    cases=[(sign*x,.9,1.8) for sign in (1,-1) for x in [.000390625,.0009765625,.001953125,.00390625,.015625]]
    cases.extend([(.001,.8,1.8),(.001,1.,1.8),(.001,.9,1.7),(.001,.9,1.9)])
    manifests={}
    for temp in [0,27,85]:
        text,manifest=comparator_deck(cases,temp)
        name=f'comparator-{temp}c.cir';(folder/name).write_text(text,encoding='utf-8');manifests[name]=manifest
    text,manifest=comparator_deck(cases,27,'10p');(folder/'comparator-convergence.cir').write_text(text,encoding='utf-8');manifests['comparator-convergence.cir']=manifest
    text,manifest=cdac_deck();(folder/'cdac-charge.cir').write_text(text,encoding='utf-8');manifests['cdac-charge.cir']=manifest
    text,manifest=mos_cdac_deck();(folder/'cdac-mos.cir').write_text(text,encoding='utf-8');manifests['cdac-mos.cir']=manifest
    (folder/'settling.cir').write_text(settling_deck(),encoding='utf-8')
    save('analog/spice/manifest.json',manifests)
    print('Generated circuit benches and exact case manifest')


if __name__=='__main__':run()
