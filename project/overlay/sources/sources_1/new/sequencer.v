`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.05.2024 08:35:10
// Design Name: 
// Module Name: sequencer
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


module sequencer(
    input aclk,
    input rst,
    input [31:0] dead_time,
    input [31:0] point_time,
    input [31:0] trig_config,
    output gen1_trigger,
    output gen2_trigger,
    output accumulator_trigger
    );
    
    reg [31:0] counter;
    reg first_sample;
    
    reg [31:0] dead_time_reg;
    reg [31:0] point_time_reg;
    // Trigger config input is split into multiple registers
    reg [31:0] trig_time_reg;
    reg trig1_invert_reg;
    reg trig1_first_reg;
    reg trig1_rest_reg;
    reg trig2_invert_reg;
    reg trig2_first_reg;
    reg trig2_rest_reg;
    
    reg accumulator_trigger_reg;
    reg generator_trigger_reg;
    
    wire gen1_first, gen1_rest;
    wire gen2_first, gen2_rest;

    // Sequential logic to count clock cycles and handle reset
    always @(posedge aclk) begin
        if (!rst) begin
            // Reset state
            counter <= 32'b0;
            first_sample <= 1'b1;
            accumulator_trigger_reg <= 1'b0;
            generator_trigger_reg <= 1'b0;
            
            // Parse and latch inputs
			dead_time_reg <= dead_time;
			point_time_reg <= point_time;
			trig_time_reg <= {8'b0, trig_config[23:0]};
			trig1_invert_reg <= trig_config[24];
			trig1_first_reg <= trig_config[25];
			trig1_rest_reg <= trig_config[26];
			trig2_invert_reg <= trig_config[28];
			trig2_first_reg <= trig_config[29];
			trig2_rest_reg <= trig_config[30];
        end
        else begin
            // Increment counter on every clock cycle
            counter <= counter + 1;
            
            // Check if we should be outputting generator trigger
            if (counter < trig_time_reg) begin
                generator_trigger_reg <= 1'b1;
            end
            else begin
                generator_trigger_reg <= 1'b0;
            end
            
            // Check if we should be outputting accumulator trigger
            // gt instead of ge means we lose a cycle but that is required for packetiser trigger
            if (counter > dead_time_reg) begin
                accumulator_trigger_reg <= 1'b1;
            end
            else begin
                accumulator_trigger_reg <= 1'b0;
            end
            
            // End of sample
            if (counter >= point_time_reg) begin
                // Reset counter but clear first_sample
                counter <= 32'd0;
                first_sample <= 1'b0;
                // Don't latch inputs again, a sweep should have constant settings
            end
        end
    end
	
//	assign gentrig_point = generator_trigger_reg;
//	assign gentrig_sweep = first_sample ? generator_trigger_reg : 1'b0;
//	assign gentrig_not_first = first_sample ? 1'b0 : generator_trigger_reg;
//	assign gen1_trigger = trig1_invert_reg ^ (trig1_type_reg ? (trig1_first_reg ? gentrig_point : gentrig_not_first) : gentrig_sweep);
	
	assign gen1_first = trig1_first_reg & generator_trigger_reg;
	assign gen1_rest = trig1_rest_reg & generator_trigger_reg;
	assign gen1_trigger = trig1_invert_reg ^ (first_sample ? gen1_first : gen1_rest);
    
	assign gen2_first = trig2_first_reg & generator_trigger_reg;
	assign gen2_rest = trig2_rest_reg & generator_trigger_reg;
	assign gen2_trigger = trig2_invert_reg ^ (first_sample ? gen2_first : gen2_rest);
    
	assign accumulator_trigger = accumulator_trigger_reg;
    
endmodule
