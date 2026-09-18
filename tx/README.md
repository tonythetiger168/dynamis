# Dynamis TX

**Simulator-agnostic transaction intelligence.** Record what your
testbench actually did — on Verilator, VCS, or Xcelium, unchanged —
then diff, search, and visualize it.

## Why

Every major simulator locks its debug data to its own waveform format.
Dynamis TX breaks that lock with the DPI-C standard: one recording
layer, every simulator, one portable transaction database (JSONL).

## Components

| tool | purpose |
|---|---|
| `src/txdpi.cpp` | DPI-C recorder (~50 lines), JSONL output, crash-safe |
| `src/tx_pkg.sv` | SV package: `tx_recorder` base class, one `record()` call per transaction |
| `tools/txview.py` | transaction + waveform → single interactive HTML (pan/zoom, no deps) |
| `tools/txdiff.py` | regression diff between two runs; exit 1 on difference (CI gate) |

## Quick start

```bash
# 1. record (Verilator example; identical code runs on VCS/Xcelium)
verilator --binary --timing -Wno-fatal src/txdpi.cpp examples/tx_demo_tb.sv -o Vdemo
./obj_dir/Vdemo          # produces tx.jsonl

# 2. visualize
python3 tools/txview.py tx.jsonl -o txview.html

# 3. regression diff
python3 tools/txdiff.py golden.jsonl run.jsonl   # exit 0 = equivalent
```

## UVM integration (sketch)

```systemverilog
class my_item extends uvm_sequence_item;
  `uvm_object_utils(my_item)
  int addr, data;
  function string convert2string();
    return $sformatf("addr=%0d,data=%0d", addr, data);
  endfunction
  // in the monitor: tx_record("write", $time, tr.convert2string());
endclass
```

## The story

Built by the Dynamis team — authors of a from-scratch SystemVerilog
simulator (`../dynamis`), cross-validated line-for-line against
Verilator 5.052. We know exactly what a transaction is, because we
implemented the event scheduler underneath it.
