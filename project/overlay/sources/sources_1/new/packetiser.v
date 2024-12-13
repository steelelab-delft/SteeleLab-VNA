`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.05.2024 11:58:55
// Design Name: 
// Module Name: packetiser
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

// Made by ChatGPT without modification..

module packetiser(
    input [63:0] val_1,
    input [31:0] cnt_1,
    input [63:0] val_2,
    input [31:0] cnt_2,
    input [63:0] val_3,
    input [31:0] cnt_3,
    input [63:0] val_4,
    input [31:0] cnt_4,
    input trigger,
    input aclk,
    input rst,
    output reg [31:0] M_AXIS_OUT_tdata,
    output reg M_AXIS_OUT_tvalid,
    input M_AXIS_OUT_tready,
    output reg M_AXIS_OUT_tlast
    );

    // State machine states
    localparam IDLE = 2'b00;
    localparam SEND_WORDS = 2'b01;
    
    reg [1:0] state, next_state;

    // Registers to hold the data
    reg [63:0] val_reg_1, val_reg_2, val_reg_3, val_reg_4;
    reg [31:0] cnt_reg_1, cnt_reg_2, cnt_reg_3, cnt_reg_4;
    reg [3:0] word_count;
    
    // Registering input values on trigger
    always @(posedge aclk) begin
        if (!rst) begin
            val_reg_1 <= 64'b0;
            cnt_reg_1 <= 32'b0;
            val_reg_2 <= 64'b0;
            cnt_reg_2 <= 32'b0;
            val_reg_3 <= 64'b0;
            cnt_reg_3 <= 32'b0;
            val_reg_4 <= 64'b0;
            cnt_reg_4 <= 32'b0;
        end else if (trigger) begin
            val_reg_1 <= val_1;
            cnt_reg_1 <= cnt_1;
            val_reg_2 <= val_2;
            cnt_reg_2 <= cnt_2;
            val_reg_3 <= val_3;
            cnt_reg_3 <= cnt_3;
            val_reg_4 <= val_4;
            cnt_reg_4 <= cnt_4;
        end
    end
    
    // State machine for packetizing data
    always @(posedge aclk) begin
        if (!rst) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end
    
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (trigger) begin
                    next_state = SEND_WORDS;
                end
            end
            SEND_WORDS: begin
                if (word_count == 4'd11 && M_AXIS_OUT_tready) begin
                    next_state = IDLE;
                end
            end
        endcase
    end
    
    always @(posedge aclk) begin
        if (!rst) begin
            word_count <= 4'b0;
            M_AXIS_OUT_tdata <= 32'b0;
            M_AXIS_OUT_tvalid <= 1'b0;
            M_AXIS_OUT_tlast <= 1'b0;
        end else if (state == SEND_WORDS) begin
            if (M_AXIS_OUT_tready) begin
                word_count <= word_count + 4'b1;
                M_AXIS_OUT_tvalid <= 1'b1;
                
                case (word_count)
                    4'd0: M_AXIS_OUT_tdata <= val_reg_1[31:0];
                    4'd1: M_AXIS_OUT_tdata <= val_reg_1[63:32];
                    4'd2: M_AXIS_OUT_tdata <= cnt_reg_1;
                    4'd3: M_AXIS_OUT_tdata <= val_reg_2[31:0];
                    4'd4: M_AXIS_OUT_tdata <= val_reg_2[63:32];
                    4'd5: M_AXIS_OUT_tdata <= cnt_reg_2;
                    4'd6: M_AXIS_OUT_tdata <= val_reg_3[31:0];
                    4'd7: M_AXIS_OUT_tdata <= val_reg_3[63:32];
                    4'd8: M_AXIS_OUT_tdata <= cnt_reg_3;
                    4'd9: M_AXIS_OUT_tdata <= val_reg_4[31:0];
                    4'd10: M_AXIS_OUT_tdata <= val_reg_4[63:32];
                    4'd11: begin
                        M_AXIS_OUT_tdata <= cnt_reg_4;
                        M_AXIS_OUT_tlast <= 1'b1;
                    end
                endcase
            end
        end else begin
            word_count <= 4'b0;
            M_AXIS_OUT_tvalid <= 1'b0;
            M_AXIS_OUT_tlast <= 1'b0;
        end
    end

endmodule
