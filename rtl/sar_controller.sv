`timescale 1ns/1ps
// Comparator must settle during EVAL before the receiving rising edge.
module sar_controller (
    input wire clk, input wire rst_n, input wire start, input wire cmp_keep,
    output wire ready, output wire busy, output wire sample_select,
    output wire top_clamp, output wire cmp_eval,
    output wire [7:0] trial_code, output reg [7:0] data,
    output wire data_valid, output wire [2:0] state_debug,
    output wire [2:0] bit_debug
);
    localparam IDLE=3'd0, ACQUIRE=3'd1, HOLD=3'd2, SET=3'd3,
               SETTLE=3'd4, EVAL=3'd5, DONE=3'd6;
    reg [2:0] state;
    reg [2:0] acquisition_count;
    reg [2:0] bit_index;
    reg [7:0] working;
    wire active_trial = state==SET || state==SETTLE || state==EVAL;
    wire [7:0] mask = 8'b1 << bit_index;
    assign trial_code = active_trial ? (working | mask) : 8'd128;
    wire [7:0] decided = cmp_keep ? trial_code : working;
    assign ready = state==IDLE || state==DONE;
    assign busy = !ready;
    assign sample_select = state==ACQUIRE || state==HOLD;
    assign top_clamp = state==ACQUIRE;
    assign cmp_eval = state==EVAL;
    assign data_valid = state==DONE;
    assign state_debug = state;
    assign bit_debug = bit_index;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; acquisition_count <= 0; bit_index <= 7;
            working <= 0; data <= 0;
        end else begin
            case (state)
                IDLE, DONE: begin
                    if (start) begin
                        state <= ACQUIRE; acquisition_count <= 0;
                        bit_index <= 7; working <= 0;
                    end else state <= IDLE;
                end
                ACQUIRE: begin
                    if (acquisition_count==5) state <= HOLD;
                    else acquisition_count <= acquisition_count + 1'b1;
                end
                HOLD: state <= SET;
                SET: state <= SETTLE;
                SETTLE: state <= EVAL;
                EVAL: begin
                    working <= decided;
                    if (bit_index==0) begin
                        data <= decided; // Includes this edge's LSB decision.
                        state <= DONE;
                    end else begin
                        bit_index <= bit_index - 1'b1;
                        state <= SET;
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
