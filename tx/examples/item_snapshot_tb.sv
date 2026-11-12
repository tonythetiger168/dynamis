// SPDX-License-Identifier: Apache-2.0
import tx_pkg::*;

class item_header;
  int tag;
  function new(int tag);
    this.tag = tag;
  endfunction
endclass

class snapshot_item extends tx_recorder;
  local int addr;
  local int data;
  local int retries;
  local bit valid;
  local item_header header;

  function new(int addr, int data);
    this.addr = addr;
    this.data = data;
    this.header = new(7);
  endfunction

  function void complete(bit corrupt);
    retries++;
    valid = 1;
    data += corrupt ? 2 : 1;
  endfunction

  virtual function string do_record();
    return $sformatf("class=snapshot_item,addr=%0d,data=%0d,retries=%0d,valid=%0d,header.tag=%0d",
                     addr, data, retries, valid, header.tag);
  endfunction
endclass

module item_snapshot_tb;
  snapshot_item item;
  initial begin
    tx_open("items.jsonl");
    item = new(4, 16);
    item.record("item.before", $time);
    #5;
    item.complete($test$plusargs("corrupt"));
    item.record("item.after", $time);
    tx_close();
    $finish;
  end
endmodule
