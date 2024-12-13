
// Made by ChatGPT with modifications

module test_packetiser(
    input aclk,
    input rst,
    output reg [63:0] val_1,
    output reg [31:0] cnt_1,
    output reg [63:0] val_2,
    output reg [31:0] cnt_2,
    output reg [63:0] val_3,
    output reg [31:0] cnt_3,
    output reg [63:0] val_4,
    output reg [31:0] cnt_4,
    output reg trigger
    );

    reg [31:0] cycle_count;

    always @(posedge aclk) begin
        if (!rst) begin
            cycle_count <= 32'b0;
            trigger <= 1'b0;
            val_1 <= 64'h12345678ABCDEF01;
            cnt_1 <= 32'h00000001;
            val_2 <= 64'h23456789BCDEF012;
            cnt_2 <= 32'h00000002;
            val_3 <= 64'h3456789ACDEF0123;
            cnt_3 <= 32'h00000003;
            val_4 <= 64'h456789ABDEF01234;
            cnt_4 <= 32'h00000004;
        end else begin
            if (cycle_count < 32'd124999999) begin
                cycle_count <= cycle_count + 1;
                trigger <= 1'b0;
            end else if (cycle_count == 32'd124999999) begin
                cycle_count <= 32'd0;
                //cycle_count <= cycle_count + 1;
                trigger <= 1'b1;
                // Change values for each trigger if needed
                val_1 <= val_1 + 64'h0101010101010101;
                cnt_1 <= cnt_1 + 32'h01010101;
                val_2 <= val_2 + 64'h0101010101010101;
                cnt_2 <= cnt_2 + 32'h01010101;
                val_3 <= val_3 + 64'h0101010101010101;
                cnt_3 <= cnt_3 + 32'h01010101;
                val_4 <= val_4 + 64'h0101010101010101;
                cnt_4 <= cnt_4 + 32'h01010101;
//            end else begin
//                cycle_count <= cycle_count;
//                trigger <= 1'b0;
            end
        end
    end

endmodule