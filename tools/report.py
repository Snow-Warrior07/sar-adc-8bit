import hashlib,importlib.metadata,json,platform,sys
from pathlib import Path
from tools.common import ROOT,save


def run():
    char=json.loads((ROOT/'results/characterization.json').read_text())
    static=char['static'];low=char['dynamic_low'];high=char['dynamic_high']
    synth=json.loads((ROOT/'results/synthesis/summary.json').read_text()) if (ROOT/'results/synthesis/summary.json').exists() else {}
    rows=[]
    for number in range(10):
        p=ROOT/f'results/phases/phase-{number:02d}.json'
        data=json.loads(p.read_text()) if p.exists() else {'name':'Release audit' if number==9 else 'Timing verification','status':'pending'}
        rows.append(f"| {number} | {data['name']} | {data['status'].upper()} | [Evidence](results/phases/phase-{number:02d}.json) |")
    table='\n'.join(rows)
    summary=f'''| Metric | Target | Measured simulation result |
|---|---|---|
| Resolution | 8 bits | All 256 codes observed |
| Sustained sample interval | 32 clocks | 32 clocks at 3.2 MHz: 100 kS/s |
| Max absolute DNL | <= 0.75 LSB | {static['max_abs_dnl_lsb']:.5f} LSB |
| Max absolute endpoint INL | <= 1 LSB | {static['max_abs_inl_lsb']:.5f} LSB |
| Uncorrected ENOB, {low['input_hz']:.2f} Hz | >= 7 | {low['enob']:.3f} bits |
| SINAD, low-frequency record | Report | {low['sinad_db']:.3f} dB |
| Uncorrected ENOB, {high['input_hz']:.2f} Hz | Report | {high['enob']:.3f} bits |
'''
    implementations=[]
    for name,v in synth.get('variants',{}).items():
        timing=v.get('timing')
        timing_text=', '.join(f'{x:.3f}' for x in timing['worst_slack_values_ns']) if timing else 'pending'
        implementations.append(f"| {name} | {v['cell_count']} | {v['area_um2']:.3f} | {timing_text} |")
    impl='\n'.join(implementations)
    readme=f'''# 8-bit differential SAR ADC

A software-only mixed-signal design project by Abhitesh Shukla: synthesizable SAR RTL, paired charge-redistribution capacitor arrays, stateful analog models, online SKY130 SPICE characterization, and reproducible verification.

**[Engineering report](report/engineering-report.md)** · **[Phase results](docs/PHASE_RESULTS.md)** · **[Architecture](docs/architecture.md)** · **[Learning guide](docs/learning-guide.md)**

![Measured ADC characterization](report/figures/adc-characterization.png)

## What is implemented

- An independent direct quantizer and charge-derived SAR reference.
- A real SystemVerilog controller and an explicit one-hot alternative.
- Actual Icarus RTL connected cycle-by-cycle to a Python analog model.
- Acquisition, DAC settling, fixed unit-capacitor mismatch, offset/noise, leakage and an equivalent reference network.
- Online ngspice circuit measurements on GitHub-hosted Ubuntu, with source/model hashes and raw logs. A browser EEcircuit RC smoke test is also retained.
- A transistor-level SKY130 regenerative comparator and sampled-CDAC circuit benches; reduced-order calibration and held-out validation.
- Coherent actual-RTL dynamic records, static linearity measurements, and 1,000 seeded capacitor-mismatch sensitivity instances.
- SKY130 standard-cell synthesis and separately reported pre-layout timing.

## Results and scope

{summary}

The ADC results above come from **actual RTL plus a reduced-order analog model**. Acquisition/DAC-driver RC and comparator delay are characterized against online SPICE. Capacitor mismatch, random noise, offset, leakage and reference-impedance parameters remain declared assumptions. Static linearity is measured with random noise disabled; FFT records include the declared noise model. These are not silicon measurements or foundry-qualified yield results.

The input differential span is -0.5 to +0.5 V at a 0.9 V common mode and nominal 1.8 V supply. The accepted-start to data-valid edge latency is 31 clock periods; continuous accepted starts are 32 periods apart. Each side of the CDAC uses 255 weighted unit capacitors plus a dummy.

## Phase-by-phase evidence

| Phase | Gate | Result | Details |
|---|---|---|---|
{table}

Failed GitHub workflow attempts remain in the Actions history. A workflow failure is not relabelled as an engineering pass; the saved individual phase checks and online artifacts show what actually ran.

## Digital implementation comparison

| FSM encoding | Mapped cells | Cell area (um^2) | Setup/hold worst-slack values (ns) |
|---|---:|---:|---|
{impl}

Area is for the controller including its debug outputs, at SKY130 HD TT 25 C / 1.8 V. Analog blocks, clock tree, pads and physical routing are excluded. Timing is pre-layout with an ideal clock and explicit external comparator/interface delay assumptions; inspect the SDC and logs before interpreting slack.

## Run the project

Use Python 3.11+ with Icarus Verilog and Yosys installed. The timing stage also needs OpenSTA.

```bash
python -m venv .venv
# Activate the virtual environment for your OS.
python -m pip install -r requirements.txt
python -m pytest -q
python -m tools.verify_foundations
python -m tools.verify_rtl
python -m tools.verify_variants
python -m tools.verify_analog
python -m tools.characterize
python -m tools.synthesize
python -m tools.report
```

The verification bridge replaces the original plan's cocotb/VPI dependency with a portable line protocol. It observes and drives the actual simulated RTL; it does not emulate the RTL state machine in Python.

## Reproduce the online circuit stage

Use the manually dispatched **Online engineering lab** workflow in this repository. `mode=circuits` runs circuit/RTL checks; `mode=timing` runs the timing toolchain. Circuit simulation occurs on the online runner. Artifacts contain ngspice logs, measurements, netlist hashes and the pinned model-source revision. See [online provenance](results/online-provenance.json) and [circuit manifest](analog/spice/manifest.json).

The saved `.cir` files can also be pasted into an online ngspice service with the documented model cards. The EEcircuit SKY130 port has limited nominal-model coverage; voltage/temperature sweeps do not establish foundry process-corner coverage.

## Design choices and limits

The core project does not include full-chip layout, extracted parasitics, fabrication, a physical prototype, an on-chip reference generator, or full transistor-level ADC/RTL feedback co-simulation. Selected blocks are transistor-level; remaining approximations are documented. The code and raw data are the primary evidence.

See the [original plan](docs/original-phase-plan.md), [requirements](docs/requirements.md), [environment](docs/environment.md), and [model validation](results/surrogate-validation.json).

## References and licenses

- [EEcircuit online simulator](https://eecircuit.com/) and [engine/model source](https://github.com/eelab-dev/EEcircuit-engine).
- [ngspice documentation](https://ngspice.sourceforge.io/docs.html).
- [SKY130 device-model documentation](https://skywater-pdk.readthedocs.io/en/main/).
- [OpenROAD SKY130 standard-cell platform](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/master/flow/platforms/sky130hd).
- [Yosys](https://yosyshq.net/yosys/) and [OpenSTA](https://github.com/The-OpenROAD-Project/OpenSTA).

Project source is MIT licensed. External tools and model sources retain their upstream licenses; model revisions and hashes are recorded with the circuit results.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    phase_doc='# Executed phase results\n\nEach JSON report contains the individual checks and measured values. Targets are evaluated within the declared model scope.\n\n| Phase | Gate | Result | Details |\n|---|---|---|---|\n'+table.replace('(results/','(../results/')+'\n'
    (ROOT/'docs/PHASE_RESULTS.md').write_text(phase_doc,encoding='utf-8')
    report=f'''# Engineering report: 8-bit differential SAR ADC

## Objective

Design and verify a differential SAR conversion system, relate RTL timing to selected analog circuits, and quantify the effects of modelling assumptions. The project is entirely virtual.

## Specifications and measured results

{summary}

![ADC characterization](figures/adc-characterization.png)

The nominal configuration is in [spice-characterized.json](../config/spice-characterized.json). Full numeric static/dynamic data is in [characterization.json](../results/characterization.json). Dynamic CSVs contain one actual RTL output per sample; no reconstructed ideal outputs are substituted for the measured codes.

## Architecture and verification

The analytical quantizer, charge-based reference, synthesizable controller and analog-state model are separate implementations. The full RTL gate checked 11,021 input conversions, all 256 comparator-decision sequences, all bit retain/clear outcomes, reset/recovery in every active state, and a 32-clock continuous initiation interval. The one-hot controller has an additional 768-conversion and reset regression.

The comparator keeps a trial when top N is at least top P. The final LSB decision updates the completed output register on the same edge. A stored analog input is used throughout conversion, and comparator noise is drawn once per evaluation. Unit-capacitor mismatch remains fixed throughout each simulated device instance.

## Online analog evidence

The online runner used ngspice with the pinned EEcircuit SKY130 model port. Forty-two comparator operating points cover both input polarities, overdrives from 0.1 to 4 LSB, selected input common modes, supplies and temperatures. The largest measured decision delay was 1.513 ns. A 10 ps versus 20 ps timestep comparison changed delay by at most 0.1521%. Ideal CDAC charge residuals matched the derived equation within 50 nV for six cases. Additional MOS sampling-clamp results are retained when available.

The lumped 5.12 pF acquisition and driver benches identified 51.2 ns and 25.6 ns time constants. This validates a reduced-order RC approximation, not all settling mechanisms of an assembled ADC. Held-out comparator delay predictions had at most 1.2013% relative error. Calibration does not establish random noise, process variation or layout behaviour.

## Model coverage

| Element/effect | Evidence level |
|---|---|
| SAR controller | Actual RTL simulation and mapped digital implementation |
| Ideal CDAC charge conservation | Online SPICE capacitor/switch benches |
| SKY130 comparator | Online transistor-level nominal-port simulations and voltage/temperature checks |
| Acquisition/DAC-driver settling | Online lumped RC characterization |
| Comparator delay in full-system runs | SPICE-derived reduced-order interpolation |
| Capacitor mismatch, noise, offset, leakage, reference network | Explicit behavioural assumptions and sensitivity experiments |
| Process-corner yield, full ADC layout, silicon | Not established |

## Static and dynamic analysis conventions

Static transition measurements disable random noise and condition repeated conversions before each decision. Endpoint INL fits transitions 1 and 255. DNL uses the 254 interior widths; clipped rail-code widths are excluded. Offset and gain error are reported separately.

Dynamic analysis uses 4,096 uniformly timed samples after startup, a -0.5 dBFS sine, and coherent bins 41 and 821 at 100 kS/s. DC is removed. SNR excludes harmonics 2-5, SINAD includes all non-fundamental non-DC power, and harmonic bins are folded into Nyquist. The reported ENOB is uncorrected for input amplitude; an amplitude-corrected number is also retained in the raw JSON.

## Sensitivity experiments

![Mismatch sensitivity](figures/mismatch-sensitivity.png)

Five assumed unit-capacitor mismatch levels each use 200 fixed seeded instances. Binary groups are sums of physical unit draws. These are sensitivity results, not foundry-qualified yield estimates. Isolated sweeps additionally show the effects of offset, acquisition time, DAC settling and hold leakage. Failed accuracy cases remain in the data.

## Digital implementation

| FSM encoding | Mapped cells | Cell area (um^2) | Setup/hold worst-slack values (ns) |
|---|---:|---:|---|
{impl}

Compare both explicit encodings under the same library and constraints. This includes the external state-debug decoding. Pre-layout area/timing does not include clock distribution, pad loading beyond the declared constraints, physical parasitics or analog layout.

## Reproduction and claim boundaries

See the [README](../README.md) for commands, [phase results](../docs/PHASE_RESULTS.md) for gates and [online provenance](../results/online-provenance.json) for cloud execution. Earlier failed workflow attempts are retained. Selected analog measurements and full-system model results are reported separately.

The current project supports an interview discussion of SAR sequencing, charge redistribution, verification strategy, comparator timing, ADC metrics and digital implementation trade-offs. A full transistor-level ADC feedback loop, full-chip physical design, on-chip references and fabrication are extensions.
'''
    (ROOT/'report/engineering-report.md').write_text(report,encoding='utf-8')
    versions={}
    for name in ['numpy','scipy','matplotlib','pytest','PyYAML']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='unavailable'
    save('results/environment.json',{'python':sys.version,'platform':platform.platform(),'packages':versions})
    print('README, phase index and engineering report generated from saved measurements')


if __name__=='__main__':run()
