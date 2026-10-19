create_clock -name core_clk -period 312.5 [get_ports clk]
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
