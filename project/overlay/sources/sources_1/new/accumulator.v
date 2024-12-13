`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07.05.2024 14:43:35
// Design Name: 
// Module Name: accumulator
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


module accumulator(
    input aclk,
    input enable,
    input rst,
    input [31:0] in_value,
    output [63:0] out_value,
    output [31:0] sample_count
    );
    
    localparam state_width = 3;
    
    localparam state_waiting = 'd0;
    localparam state_accumulating = 'd1;
    localparam state_output = 'd2;
    
    reg [state_width-1:0] state;
    reg [state_width-1:0] newstate;
    reg [63:0] accu_total;
    reg [31:0] samplecountreg;
    
    always @(posedge aclk) begin
      if (!rst)
        state <= state_waiting;
      else
        state <= newstate;
    end
    
    always @* begin
        case(state)
            state_waiting: begin
                if (enable) newstate = state_accumulating;
                else newstate = state_waiting;
            end
            state_accumulating: begin
                if (enable == 1'b0) newstate = state_output;
                else newstate = state_accumulating;
            end
            state_output: begin
                newstate = state_waiting;
            end
            default: newstate = state_waiting;
        endcase
    end
    
    always @(posedge aclk) begin
        case(state)
            state_waiting: begin
                accu_total <= 64'd0;
                samplecountreg <= 32'd0;
            end
            state_accumulating: begin
                accu_total <= accu_total + {{32{in_value[31]}}, in_value[31:0]};
                samplecountreg <= samplecountreg + 1;
            end
            state_output: begin
                accu_total <= accu_total + {{32{in_value[31]}}, in_value[31:0]};
                samplecountreg <= samplecountreg + 1;
            end
            default: begin
                accu_total <= 64'd0;
                samplecountreg <= 32'd0;
            end
        endcase
     end
     
     assign sample_count = samplecountreg;
     assign out_value = accu_total;

endmodule
