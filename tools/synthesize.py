import argparse,hashlib,json,re,shutil,subprocess,urllib.request
from pathlib import Path
from tools.common import ROOT,executable,tool_env,save,phase
from tools.generate_variants import run as generate_variants

LIB_REV='7bcaf475c884e15f674e428aa04dbf92bd0426ed'
LIB_URL='https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/'+LIB_REV+'/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'


def run(no_sta=False):
    generate_variants()
    build=ROOT/'build';build.mkdir(exist_ok=True)
    folder=ROOT/'.tools';folder.mkdir(exist_ok=True)
    lib=folder/'sky130_fd_sc_hd__tt_025C_1v80.lib'
    if not lib.exists():
        with urllib.request.urlopen(LIB_URL,timeout=90) as r:lib.write_bytes(r.read())
    libpath=lib.as_posix()
    results={}
    for encoding in ['binary','one-hot']:
        variant=encoding.replace('-','_')
        source='rtl/sar_controller.sv' if encoding=='binary' else 'rtl/sar_controller_onehot.sv'
        commands=f'''read_liberty -lib {libpath}
read_verilog -sv {source}
hierarchy -check -top sar_controller
proc
opt
fsm -norecode
opt
techmap
opt
dfflibmap -liberty {libpath}
abc -liberty {libpath}
clean
check -assert
tee -o build/{variant}.json stat -json -liberty {libpath}
write_verilog -noattr -noexpr build/{variant}.v
'''
        script=build/(variant+'.ys');script.write_text(commands,encoding='utf-8')
        r=subprocess.run([executable('yosys'),'-s',str(script)],cwd=ROOT,env=tool_env(),text=True,capture_output=True,timeout=120)
        (build/(variant+'-synth.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError('Synthesis failed: '+(r.stdout+r.stderr)[-2000:])
        raw=json.loads((build/(variant+'.json')).read_text())
        module=next(v for k,v in raw['modules'].items() if k.lstrip('\\')=='sar_controller')
        cells=module.get('num_cells_by_type',{})
        assert not any('latch' in c.lower() or 'dlxt' in c.lower() for c in cells)
        results[encoding]={'cell_count':module.get('num_cells'),'area_um2':module.get('area',module.get('cell_area')),
                           'cells':cells,'timing':None,'source':source}
        if not no_sta:
            if not shutil.which('sta'):raise RuntimeError('OpenSTA executable required for timing phase')
            sdc='''create_clock -name core_clk -period 312.5 [get_ports clk]
set_clock_uncertainty -setup 0.5 [get_clocks core_clk]
set_clock_uncertainty -hold 0.05 [get_clocks core_clk]
set_input_delay -clock core_clk -max 20.0 [get_ports {start cmp_keep}]
set_input_delay -clock core_clk -min 0.2 [get_ports {start cmp_keep}]
# External reset controller deasserts at the falling core-clock edge.
# Assertion remains asynchronous; recovery/removal are analyzed, not waived.
set_input_delay -clock core_clk -clock_fall -max 0.25 [get_ports rst_n]
set_input_delay -clock core_clk -clock_fall -min 0.0 [get_ports rst_n]
set_input_transition 0.2 [get_ports {start cmp_keep rst_n}]
set_output_delay -clock core_clk -max 5.0 [all_outputs]
set_output_delay -clock core_clk -min 0.0 [all_outputs]
set_load 0.02 [all_outputs]
'''
            constraints=ROOT/'constraints';constraints.mkdir(exist_ok=True)
            (constraints/'core.sdc').write_text(sdc,encoding='utf-8')
            tcl=f'''read_liberty {libpath}
read_verilog build/{variant}.v
link_design sar_controller
read_sdc constraints/core.sdc
check_setup -verbose
report_checks -path_delay max -group_path_count 5 -digits 6
report_checks -path_delay min -group_path_count 5 -digits 6
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_checks -unconstrained -group_path_count 5
exit
'''
            tclfile=build/(variant+'.tcl');tclfile.write_text(tcl,encoding='utf-8')
            sta=subprocess.run(['sta','-exit',str(tclfile)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            log=sta.stdout+'\n'+sta.stderr;(build/(variant+'-sta.log')).write_text(log,encoding='utf-8')
            matches=re.findall(r'worst slack\s+(?:max|min)?\s*([-+\d.]+)',log,re.I)
            if sta.returncode or re.search(r'\bError:',log):raise RuntimeError('OpenSTA failed: '+log[-3000:])
            results[encoding]['timing']={'worst_slack_values_ns':[float(x) for x in matches],
                                        'scope':'pre-layout; ideal clock; no extracted interconnect; 20 ns max comparator input delay assumption',
                                        'log':f'build/{variant}-sta.log'}
    payload={'library_url':LIB_URL,'library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),
             'corner':'SKY130 HD TT 25C 1.80 V','variants':results,
             'scope':'RTL controller only. Analog devices, reference circuits, clock tree, pads and routing excluded.'}
    save('results/synthesis/summary.json',payload)
    if not no_sta:
        slacks=[s for v in results.values() for s in v['timing']['worst_slack_values_ns']]
        gate=phase(8,'SKY130 synthesis and pre-layout static timing',[
            {'name':'mapped controller; no unintended latches','passed':True},
            {'name':'OpenSTA timing reports produced','passed':len(slacks)>=4},
            {'name':'setup, hold, recovery and removal slack nonnegative','passed':bool(slacks) and min(slacks)>=0,'slack_values_ns':slacks}],payload)
        if gate['status']!='passed':raise RuntimeError('Static timing failed a phase-eight gate')
    else:print(json.dumps(payload,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--no-sta',action='store_true');run(p.parse_args().no_sta)
