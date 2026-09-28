// SPDX-License-Identifier: Apache-2.0
// uvm_tx_pkg.sv — Dynamis TX recorder for UVM 1.2.
// Drop this file next to your UVM testbench; zero changes to the
// monitor's transaction flow beyond one line:
//
//     import uvm_tx_pkg::*;
//     ...
//     uvm_tx::capture(tr);              // kind = transaction type name
//     uvm_tx::capture(tr, "write");     // explicit kind
//     uvm_tx::capture_fields("irq", "id=3,level=1");  // raw fields
//
// Works on any simulator that runs UVM 1.2 + DPI-C: VCS, Xcelium,
// and (experimentally) Verilator v5.x with --timing. The tx database
// lands in tx.jsonl; visualize with tools/txview.py, gate with
// tools/txdiff.py.
//
// NOTE: methods are named `capture`, not `record` — `record` collides
// with a symbol in Verilator's UVM support and fails to parse there.

package uvm_tx_pkg;

  import uvm_pkg::*;
  import "DPI-C" function void tx_open(input string path);
  import "DPI-C" function void tx_record(input string kind,
                                         input longint  t,
                                         input string   payload);
  import "DPI-C" function void tx_close();

  class uvm_tx;

    static local bit m_opened = 0;

    // Open the database once per simulation (idempotent).
    static function void open(string path = "tx.jsonl");
      if (!m_opened) begin
        tx_open(path);
        m_opened = 1;
      end
    endfunction

    static function void close();
      if (m_opened) begin
        tx_close();
        m_opened = 0;
      end
    endfunction

    // Capture any uvm_sequence_item: kind = $typename (overridable),
    // payload = convert2string() output (free-form, still searchable
    // as text in txview).
    static function void capture(uvm_sequence_item tr,
                                 string kind = "",
                                 longint t = -1);
      string k;
      open();
      k = (kind == "") ? $typename(tr) : kind;
      if (t < 0) t = $time;
      tx_record(k, t, tr.convert2string());
    endfunction

    // Capture with exact k=v fields (shows field tooltips in txview).
    static function void capture_fields(string kind,
                                        string fields,
                                        longint t = -1);
      open();
      if (t < 0) t = $time;
      tx_record(kind, t, fields);
    endfunction

  endclass

  // Convenience macros for monitors:
  `define DYNAMIS_TX_CAPTURE(tr) \
    uvm_tx::capture(tr)

  `define DYNAMIS_TX_CAPTURE_KIND(tr, kind) \
    uvm_tx::capture(tr, kind)

endpackage
