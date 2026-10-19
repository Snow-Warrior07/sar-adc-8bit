# Retained failed experiments and corrections

## MOS sampling-clamp terminal order

An added sampled-CDAC bench replaced ideal top-plate switches with SKY130 transmission gates. Its first run did not preserve the sampled differential charge: all top plates converged near 66.6 mV, with a maximum differential error of 0.125 V. The previously verified ideal-switch CDAC bench still passed.

The cause was a swapped gate/source order in the generated MOS subcircuit instances. The SKY130 primitive interface is drain, gate, source, body. The initial instance incorrectly supplied drain, common-mode, control, body. The corrected instance supplies drain, control, common-mode, body; complementary NMOS/PMOS controls now drive the gates.

The first netlist, measurements, phase report and workflow provenance are retained in results/failures/mos-clamp-initial/. The corrected bench is rerun online. Its measured residual must meet the declared 0.1 LSB tolerance before the phase is accepted.

## Toolchain setup

Early cloud runs stopped because OpenSTA is not packaged in the selected Ubuntu repository. The timing job now builds a pinned source revision with its dependencies. The model port also requires supported device geometry bins: the tail transistor uses two parallel 1.68 um devices instead of one unsupported 3.36 um instance. Failed workflow history is retained.

## FSM implementation comparison

Automatic recoding did not extract the exported/debugged FSM reliably. The comparison therefore uses explicit binary and one-hot RTL implementations, each simulated against the same expected conversion and timing contract. Area includes the external debug decoding in both variants.

## Reset-removal timing contract

The first pre-layout timing run allowed reset deassertion 0.2 ns after a rising edge. OpenSTA reported -0.200661 ns worst removal slack, although ordinary data setup/hold paths passed. The functional bridge already changes reset at a falling edge. The corrected SDC expresses that external falling-edge reset-release contract explicitly, with 0-0.25 ns input delay relative to the falling edge. Recovery/removal checks remain enabled. The original report and constraints are retained in results/failures/reset-removal-initial/.
