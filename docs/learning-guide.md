# Understanding and defending this project

## Work through one conversion

For a differential input of 0.183 V, the ideal output is `floor((0.183+0.5)*256) = 174`.

| Bit | Trial | Trial differential DAC voltage | Decision |
|---|---:|---:|---|
| 7 | 128 | 0.00000000 V | Keep |
| 6 | 192 | 0.25000000 V | Clear |
| 5 | 160 | 0.12500000 V | Keep |
| 4 | 176 | 0.18750000 V | Clear |
| 3 | 168 | 0.15625000 V | Keep |
| 2 | 172 | 0.17187500 V | Keep |
| 1 | 174 | 0.17968750 V | Keep |
| 0 | 175 | 0.18359375 V | Clear |

The output is 10101110. The code-center reconstruction is 0.181640625 V. The final bit must be decided before publishing the result.

## Read the evidence in this order

1. Derive the CDAC equations in architecture.md; check the dummy capacitor and comparator polarity.
2. Run the independent reference tests and inspect results/reference-traces.json.
3. Read rtl/sar_controller.sv alongside the timing trace in results/rtl-traces.json.
4. Inspect how tb/bridge.py drives actual simulated RTL from observed outputs.
5. Disable every imperfection in model/analog_frontend.py, then enable one at a time.
6. Inspect the online SPICE netlists, source hashes and measurement logs.
7. Compare the fitted comparator delay against the held-out points in results/surrogate-validation.json.
8. Inspect static and FFT analysis, including the gain/offset correction convention.
9. Compare the explicit binary and one-hot controllers under the same cell library and timing constraints.

## Questions you should be able to answer

- Why does the CDAC use 256 total unit capacitors rather than 255?
- Why is the top-plate residual the negative of input-minus-DAC?
- What is the input common-mode voltage, and why does the comparator need it controlled?
- Which clock edge samples the analog input? Why is DONE later?
- What changes if acquisition or DAC settling is too short?
- Why are mismatch draws fixed per simulated instance and noise draws made once per event?
- Why are the large binary capacitors modelled as sums of unit capacitors?
- What is the difference between comparator offset, random noise and delayed resolution?
- Why does a two-flop synchronizer change this comparator timing architecture?
- How do DNL and INL differ? Which rail-code widths are excluded here?
- Why were FFT bins 41 and 821 selected for a 4096-sample record?
- Why is the reported ENOB a simulation result with model assumptions?
- Which circuits were actually simulated online at transistor level, and which remain reduced-order or ideal?
- What does the SKY130 mapped controller area include, and what is excluded?
- Why can positive pre-layout timing slack change after placement and routing?

## Honest project description

This project implements and verifies real SAR RTL, runs selected circuit simulations online, and calibrates part of an analog model against those measurements. The complete ADC has not been fabricated, laid out or verified as a full transistor-level feedback loop. Noise/mismatch assumptions and process coverage are explicit in the report. Keep those distinctions when explaining the project in an interview.
