`timescale 1ns/1ps
// Open, line-oriented VVP bridge: Python computes analog response to real RTL.
// Each STEP is at the falling edge. Inputs are applied for the next rising edge.
module interactive_tb;
    reg clk=0, rst_n=0, start=0, cmp_keep=0;
    wire ready,busy,sample_select,top_clamp,cmp_eval,data_valid;
    wire [7:0] trial_code,data;
    wire [2:0] state_debug,bit_debug;
    integer r,s,c,rc,cycle=0;
    sar_controller dut(.*);
    always #156.25 clk=~clk;
    initial begin
        if ($test$plusargs("waves")) begin
            $dumpfile("build/conversion.vcd"); $dumpvars(0,interactive_tb);
        end
        forever begin
            @(negedge clk);
            $display("STEP %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",cycle,state_debug,bit_debug,trial_code,data,data_valid,ready,busy,top_clamp,sample_select,cmp_eval);
            $fflush();
            rc=$fscanf(32'h80000000,"%d %d %d",r,s,c);
            if (rc!=3 || r<0) $finish;
            rst_n=(r!=0);start=(s!=0);cmp_keep=(c!=0);cycle=cycle+1;
        end
    end
endmodule
