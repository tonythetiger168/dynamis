// SPDX-License-Identifier: Apache-2.0
// tx_pkg.sv — simulator-agnostic transaction recording package.
// Works on Verilator, VCS, and Xcelium unchanged (pure DPI-C + SV).
//
// Usage:
//   import tx_pkg::*;
//   initial tx_open("tx.jsonl");
//   ... tx_record("item", $sformatf("addr=%0d,data=%0d", a, d));
//   final tx_close();

package tx_pkg;

  import "DPI-C" function void tx_open(input string path);
  import "DPI-C" function void tx_record(input string kind,
                                         input longint  t,
                                         input string   payload);
  import "DPI-C" function void tx_close();

  // Recordable base class: extend it, implement do_record(),
  // then call rec.record("kind", $time) — fields serialize automatically
  // when the subclass builds the payload string in do_record.
  class tx_recorder;
    function void record(string kind, longint t);
      tx_record(kind, t, this.do_record());
    endfunction
    virtual function string do_record();
      return "";
    endfunction
  endclass

endpackage
