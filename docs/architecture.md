# Differential SAR architecture

The input is differential with a nominal 0.9 V common mode. Its differential full-scale span is 1.0 V, from -0.5 to +0.5 V. Output coding is offset binary. Reference rails are 0.65 V and 1.15 V, so complementary differential CDAC switching produces a 1.0 V differential DAC span.

Each CDAC side contains 255 weighted unit capacitors and one dummy. During acquisition the top plates are clamped to 0.9 V and bottom plates track the corresponding input. After top-plate release the stored charge represents the input at that aperture. The dummy connects to the low reference on P and high reference on N during conversion. The comparator polarity is defined as keep=1 when top N >= top P.

For trial D, the ideal residual at top P minus top N is `-0.5 + D/256 - vin_diff`. The Python analytical quantizer, charge-derived binary search, RTL controller and analog model are separate implementations checked against this convention.

## Timing contract

All RTL is clocked by one 3.2 MHz clock. Start is accepted when ready is high. A request during busy is ignored. An accepted-start rising edge enters ACQUIRE. Six periods later the HOLD state releases the top-plate clamps. HOLD lasts one period, followed by SET/SETTLE/EVAL for each of eight bits. The comparator is reset outside EVAL and its decision is captured at the rising edge ending EVAL.

The final LSB decision and completed output register update on the same edge. Data-valid is high during DONE for one period. The next conversion can enter ACQUIRE directly from DONE. The measured initiation interval is 32 periods, while the accepted-start edge to output-valid edge spans 31 periods (9.6875 us). This distinction is deliberate. The first sampling aperture occurs six periods after the accepted start.

Reset assertion may be asynchronous. The external reset source must deassert at the falling core-clock edge (the timing model allows 0-0.25 ns after that edge), then hold reset inactive. This is the release phase used by the functional bridge. The SDC models this falling-edge relationship explicitly, and retains recovery/removal analysis. A reset source with arbitrary release timing needs a separate reset-release circuit before connecting to this core.

DAC trials remain stable for 625 ns before evaluation. Comparator evaluation has 312.5 ns, minus receiver setup/interface margin. Reset aborts a conversion and clears the result/valid state. The integration contract requires reset release and comparator sampling to meet digital timing; this is not an asynchronous comparator CDC design.

## Verification bridge

The portable testbench uses Icarus Verilog and a line-oriented Python bridge instead of cocotb/VPI. At each falling edge, VVP prints the actual RTL state and outputs. Python computes comparator response from those outputs and applies inputs for the next rising edge. The SystemVerilog controller is executed by a real RTL simulator; Python does not emulate its FSM. An independent direct quantizer checks completed output codes.

The behavioural analog model maintains held sample, capacitor mismatch, DAC residual, equivalent reference RC state and once-per-event noise draws. Fast standalone sweeps use its SAR conversion method; integrated dynamic records also run through actual RTL. SPICE-derived parameters and explicitly assumed parameters are identified separately in the results.

## Physical scope

Sampling/CDAC charge benches initially use ideal switches and ideal capacitors. Lumped acquisition and DAC-driver RC benches identify reduced-order settling constants. A transistor-level regenerative comparator uses the EEcircuit SKY130 port when supported; the earlier CMOS90 benchmark is retained as an exploratory run. Neither the complete ADC nor its physical layout is transistor-level sign-off verified. Thermal/mismatch assumptions in the Python model do not establish foundry-qualified noise or yield.
