`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 29.05.2024 15:33:49
// Design Name: 
// Module Name: stretcher
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


module stretcher(
    input aclk,
    input rst,
    input [15:0] packet_length,
    input [31:0] S_AXIS_IN_tdata,
    input S_AXIS_IN_tvalid,
    input S_AXIS_IN_tlast,
	input M_AXIS_OUT_tready,
    output [31:0] M_AXIS_OUT_tdata,
    output M_AXIS_OUT_tvalid,
    output M_AXIS_OUT_tlast,
	output S_AXIS_IN_tready
    );
    
    reg [31:0] counter;	
	reg readyToRumble;
	reg [31:0] packet_lengthmo_reg;
    
    always @(posedge aclk) begin
    	if (!rst) begin
			counter <= 32'd0;
			packet_lengthmo_reg <= {16'b0, packet_length-1};
			readyToRumble <= 1'b0;	
		end
		else begin
			if (S_AXIS_IN_tlast) counter <= counter + 1;
			if (counter < packet_lengthmo_reg) begin
				readyToRumble <= 1'b0;	
			end else if (counter == packet_lengthmo_reg) begin
				if (S_AXIS_IN_tlast == 0) readyToRumble <= 1'b1;		  
			end else if (counter > packet_lengthmo_reg) begin
				counter <= 32'd0;
			end else begin
				counter <= 0;
				readyToRumble <= 1'b0;	
			end
		end	
    end
		 
		 
     
     assign M_AXIS_OUT_tdata = S_AXIS_IN_tdata;
     assign M_AXIS_OUT_tvalid = S_AXIS_IN_tvalid;
     assign M_AXIS_OUT_tlast = readyToRumble & S_AXIS_IN_tlast;
	 assign S_AXIS_IN_tready = M_AXIS_OUT_tready;
     
endmodule