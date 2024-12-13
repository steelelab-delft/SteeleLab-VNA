
`timescale 1 ns / 1 ps

module axi_split #
(
  parameter integer AXIS_TDATA_WIDTH = 32,
  parameter integer OUT_WIDTH = 14
)
(
  // Input side
  input  wire                        aclk,
  input  wire [AXIS_TDATA_WIDTH-1:0] s_axis_tdata,
  input  wire                        s_axis_tvalid,
  
  // Output signals
  output wire [OUT_WIDTH-1:0]        data_lower,
  output wire [OUT_WIDTH-1:0]        data_upper
);

  reg  [OUT_WIDTH-1:0]        data_upper_int, data_lower_int;

  always @(posedge aclk)
  begin
    if (s_axis_tvalid)
    begin
      data_lower_int = s_axis_tdata[OUT_WIDTH-1:0];
      data_upper_int = s_axis_tdata[AXIS_TDATA_WIDTH/2 + OUT_WIDTH-1:AXIS_TDATA_WIDTH/2];
    end
  end
  
  assign data_upper = data_upper_int;
  assign data_lower = data_lower_int;

endmodule
