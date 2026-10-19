# Reproduction environment

Install Python 3.11 or newer and the packages in requirements.txt in a virtual environment. Install Icarus Verilog, Yosys and, for static timing, OpenSTA. The manual GitHub-hosted online lab installs circuit tools and builds a pinned OpenSTA revision. No hardware is required.

The initial development run used Python 3.12.14 and the official OSS CAD Suite Windows portable build dated 2026-10-17. The suite is excluded from Git. On this host, Icarus native compilation required execution outside the restricted application sandbox and an explicit absolute `-B` library path; this is handled by tb/bridge.py for the portable suite. Normal Linux system installations use their ordinary executable paths.

Commands from the repository root:

```text
python -m pip install -r requirements.txt
python -m pytest -q
python -m tools.verify_foundations
python -m tools.verify_rtl
python -m tools.verify_analog
python -m tools.generate_circuits
```

Circuit simulations for the published run are performed in the online lab or EEcircuit rather than with a local circuit installation. Paste the saved netlist into the online editor and use its Run and Info tabs for the scalar measurements. The phase-zero RC result was transcribed from the online Info output after its CSV download interface stalled. Cloud runs retain full logs, source-model hashes, netlist hashes, and job provenance.

OpenSTA timing results are pre-layout. They include an explicit external comparator input-delay assumption, not transistor-level timing co-simulation or routed parasitics. Reproduction commands for characterization and the final report are documented in the README as their scripts are added.
