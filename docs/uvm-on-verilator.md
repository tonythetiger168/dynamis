# Running UVM 1.2 on Verilator with Dynamis TX recording

Status: **the mixin (`tx/src/uvm_tx_pkg.sv`) parses cleanly against UVM 1.2
on Verilator v5.x `--timing`**. Full build recipes below; on VCS/Xcelium
everything here runs as-is.

## The seven workarounds (each cost us a debugging round)

1. **Never `include "uvm_macros.svh"` inside a package.** It is included
   by `uvm_pkg.sv` itself; a second inclusion corrupts macro state and
   cascades parse errors into later files ("unexpected end" with no
   preceding error).
2. **Never start a comment with the word "Verilator"** — `// Verilator ...`
   and `/*Verilator ...` are parsed as tool metacomments (case-insensitive)
   → `%Error-BADVLTPRAGMA`. Write "Workarounds for Verilator v5.x", not
   "// Verilator v5.x ...".
3. **Do not name methods `record`** — collides with a symbol in Verilator's
   UVM support and fails to parse. Dynamis uses `capture`/`capture_fields`.
4. **No declaration-with-initialization for class handles:**
   `tx_item tr = tx_item::type_id::create("tr");` misparses.
   Split: declare, then assign.
5. **No task calls (`` `uvm_info``) from functions.** Verilator reports
   this as an unlocalizable "unexpected endfunction".
6. **No timing controls inside class method statement blocks** — keep
   `#delay` at task top level; factor delay-free logic into functions.
7. **`uvm_hdl.c` has no fallback for open-source simulators** — the DPI
   HDL backplane `#error`s unless VCS/QUESTA/XCELIUM is defined. Fix both
   sides:
   - SV: add `+define+UVM_HDL_NO_DPI` to the command line (official guard;
     UVM then stubs `uvm_hdl_*` calls with a friendly message).
   - C: `uvm_dpi.cc` still `#include`s `uvm_hdl.c` unconditionally in
     current uvm-core. Comment that include out (or provide no-op
     implementations of the six `uvm_hdl_*` functions).

## Build recipe

```bash
UVM=https://codeload.github.com/accellera-official/uvm-core/tar.gz/refs/heads/main
curl -sL -o uvm.tgz $UVM && mkdir -p uvm && tar xzf uvm.tgz -C uvm --strip-components=1
sed 's|#include "uvm_hdl.c"|/* excluded: no vendor backend */|' \
    uvm/src/dpi/uvm_dpi.cc > uvm_dpi_patched.cc

verilator --binary --timing -Wno-fatal -j 4 \
  +define+UVM_HDL_NO_DPI \
  +incdir+$PWD/uvm/src +incdir+$PWD/uvm/src/macros \
  uvm/src/uvm_pkg.sv uvm_dpi_patched.cc \
  tx/src/tx_pkg.sv tx/src/uvm_tx_pkg.sv tx/src/txdpi.cpp \
  tx/examples/uvm_tx_tb.sv -o Vuvm
./obj_dir/Vuvm        # -> tx.jsonl (4x write + 1x done)
```

Notes: UVM's C++ output is large (~2000 files); builds need ~8 GB RAM
and an environment that does not reap build trees mid-compile — CI
runners are ideal. `tx_pkg.sv` must be listed before `uvm_tx_pkg.sv`.
