// SPDX-License-Identifier: Apache-2.0
// Minimal UVM 1.2 environment exercising the Dynamis TX recorder.
// Verified to PARSE and elaborate with Verilator v5.x --timing;
// full build/run recipe: docs/uvm-on-verilator.md. On VCS/Xcelium
// this file runs as-is (full UVM 1.2 support).
//
// Workarounds applied for Verilator v5.x compatibility:
//   - no timing controls inside class method statement blocks
//   - class handles declared before assignment (no decl-init)
//   - no uvm_info (a task) called from functions
//   - direct uvm_tx::capture calls instead of text macros
`timescale 1ns/1ps
import uvm_pkg::*;
`include "uvm_macros.svh"
import uvm_tx_pkg::*;

class tx_item extends uvm_sequence_item;
  `uvm_object_utils(tx_item)
  int addr;
  int data;
  function new(string name = "tx_item");
    super.new(name);
  endfunction
  function string convert2string();
    return $sformatf("addr=%0d,data=%0d", addr, data);
  endfunction
endclass

class my_monitor extends uvm_monitor;
  `uvm_component_utils(my_monitor)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void capture_one(int a);      // delay-free: capture one item
    tx_item tr;
    tr = tx_item::type_id::create("tr");
    tr.addr = a;
    tr.data = a * 16;
    uvm_tx::capture(tr, "write");
  endfunction
  task run_phase(uvm_phase phase);
    int i;                             // deterministic: CI-diffable
    repeat (4) begin
      #10;
      capture_one((i * 5 + 3) % 16);
      i++;
    end
    uvm_tx::capture_fields("done", "count=4");
    uvm_tx::close();
  endtask
endclass

class test extends uvm_test;
  `uvm_component_utils(test)
  my_monitor mon;
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    mon = my_monitor::type_id::create("mon", this);
  endfunction
endclass

module top;
  initial run_test("test");
endmodule
