// SPDX-License-Identifier: Apache-2.0
// tx_demo_tb.sv — commercial-path demo: class-based sequence items
// recorded through the DPI transaction recorder, running on a REAL
// simulator (Verilator here; same code runs on VCS/Xcelium).
// Drives a tiny DUT-like counter so items correlate with waveforms.

import tx_pkg::*;

class item extends tx_recorder;
  int addr;
  int data;
  function new(int a, int d);
    addr = a; data = d;
  endfunction
  virtual function string do_record();
    return $sformatf("addr=%0d,data=%0d", addr, data);
  endfunction
endclass

module tx_demo_tb;
  logic clk = 0, rst = 1;
  logic [3:0] count = 0;

  always #5 clk = ~clk;
  always @(posedge clk)
    if (rst) count <= 0; else count <= count + 1;

  item it;

  initial begin
    tx_open("tx.jsonl");
    #12 rst = 0;
    repeat (4) begin
      @(posedge clk);
      it = new(count, count * 16);
      it.record("write", $time);
      $display("[%0t] write addr=%0d data=%0d", $time, it.addr, it.data);
    end
    tx_record("done", $time, $sformatf("count=%0d", count));
    tx_close();
    $finish;
  end
endmodule
