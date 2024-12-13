`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07.05.2024 14:47:45
// Design Name: 
// Module Name: accu_trigger
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module accu_trigger # (
    parameter integer AXIS_TDATA_WIDTH = 8
)
(
    input aclk,
    input rst,
    input trigger,
    input [AXIS_TDATA_WIDTH-1:0] current_phase_tdata,
    input current_phase_tvalid,
    output accu_enable,
    output done_samples_valid
    );
    
    localparam state_width = 3;
    
    localparam state_stopped = 'd0;
    localparam state_starting = 'd1;
    localparam state_running = 'd2;
    localparam state_waiting = 'd3;
    localparam state_ending = 'd4;
    
    reg [state_width-1:0] state;
    reg [state_width-1:0] newstate;
    reg [AXIS_TDATA_WIDTH-1:0] phase;
    reg accu_enable_reg;
    reg dsv_reg;
    
    always @(posedge aclk) begin
      if (!rst)
        state <= state_stopped;
      else
        state <= newstate;
    end
    
    always @* begin
        case(state)
            state_stopped: begin
                if (trigger) newstate = state_starting;
                else newstate = state_stopped;
                end
            state_starting: begin
                newstate = state_running;
                end
            state_running: begin
                if (!trigger) newstate = state_waiting;
                else newstate = state_running;
                end
            state_waiting: begin
                if (current_phase_tdata == phase) newstate = state_ending;
                else newstate = state_waiting;
                end
            state_ending: begin
                newstate = state_stopped;
                end
            default: newstate = state_stopped;
        endcase
    end
    
    always @(posedge aclk) begin
        case(state)
            state_stopped: begin
                accu_enable_reg <= 1'b0;
                dsv_reg <= 1'b0;
                end
            state_starting: begin
                accu_enable_reg <= 1'b0;
                dsv_reg <= 1'b0;
                phase <= current_phase_tdata;
                end
            state_running: begin
                accu_enable_reg <= 1'b1;
                dsv_reg <= 1'b0;
                end
            state_waiting: begin
                accu_enable_reg <= 1'b1;
                dsv_reg <= 1'b0;
                end
            state_ending: begin
                accu_enable_reg <= 1'b0;
                dsv_reg <= 1'b1;
                end
            default: begin
                accu_enable_reg <= 1'b0;
                dsv_reg <= 1'b0;
                end
        endcase
     end
     
     assign accu_enable = accu_enable_reg;
     assign done_samples_valid = dsv_reg;
     
endmodule
