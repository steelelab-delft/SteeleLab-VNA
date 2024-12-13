`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 17.05.2024 11:26:46
// Design Name: 
// Module Name: fifo_filler
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


module fifo_filler #
(
    parameter integer AXIS_TDATA_WIDTH = 32,
    parameter integer VALUE_COUNT = 8
)
(
    input aclk,
    input rst,
    output [AXIS_TDATA_WIDTH-1:0] m_axis_tdata,
    output m_axis_tvalid,
    input m_axis_tready,
    output m_axis_tlast
);

    reg [AXIS_TDATA_WIDTH-1:0]  counter, next_count;
    reg                         done, next_done;
    
    always @(posedge aclk) begin
        if (!rst) begin
            counter = 10;
            done = 0;
        end
        if (m_axis_tready && !done) begin
            counter = next_count;
            done = next_done;
        end
    end
    
    always @* begin
        next_count = counter + 1;
        next_done = next_count >= (VALUE_COUNT+10);
    end

    assign m_axis_tdata = counter;
    assign m_axis_tvalid = !done;
    assign m_axis_tlast = next_done && !done;

endmodule
