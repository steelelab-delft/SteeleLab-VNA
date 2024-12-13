
`timescale 1 ns / 1 ps

module axis_to_wire #
(
  parameter integer AXIS_TDATA_WIDTH = 32,
  parameter integer OUT_WIDTH = 32
)
(
  // System signals
  input  wire                        aclk,
  output wire [OUT_WIDTH-1:0]        data,

  // Master side
  input  wire [AXIS_TDATA_WIDTH-1:0] s_axis_tdata,
  input  wire                        s_axis_tvalid
);

  reg  [OUT_WIDTH-1:0]        data_int;

  always @(posedge aclk)
  begin
    if (s_axis_tvalid)
    begin
      data_int = s_axis_tdata[OUT_WIDTH-1:0];
    end
  end
  
  assign data = data_int;

endmodule
