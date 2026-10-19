# Requirement and evidence matrix

| ID | Requirement | Test/evidence |
|---|---|---|
| ADC-01 | 8-bit offset-binary quantizer over 1 V differential span | tests/test_reference.py; phase 2 |
| ADC-02 | Correct CDAC scaling, dummy and polarity | phase 1 equations; online cdac-charge.cir |
| RTL-01 | Eight decisions, including the final LSB | full phase 3 input/decision regression |
| RTL-02 | Busy requests ignored; reset abort/recovery | phase 3 protocol tests |
| RTL-03 | 32-period initiation interval and one-period valid | phase 3 continuous-request tests |
| MOD-01 | Stored sample and causal nonideality states | tests/test_analog.py; phase 4 |
| MOD-02 | Separate assumed and SPICE-derived parameters | phase 6 validation and model provenance |
| ANA-01 | Circuit computations executed online | EEcircuit logs and GitHub-hosted cloud artifacts |
| ANA-02 | Comparator polarity, delay and operating-point sensitivity | online comparator characterization |
| ADC-03 | Nominal max abs DNL <= 0.75 and endpoint INL <= 1 LSB | phase 7 static characterization |
| ADC-04 | Nominal low-frequency uncorrected ENOB >= 7 | phase 7 coherent sine test |
| DIG-01 | Mapped controller, no unintended latches | phase 8 Yosys report |
| DIG-02 | Constrained pre-layout setup/hold timing | phase 8 OpenSTA report |
| REL-01 | Reproducible source, tests and evidence | phase 9 release audit |

These are project design requirements. A pass applies only to the documented simulation configuration and analysis scope. Failed targets are retained in results.
