# Minisim／Helios TX 整合紀錄

另已接入 Basanos pyuvm tinyalu 的 500 筆真實 TX，以外部獨立 ALU 值模型配對並通過 Helios gate（等價、錯值、缺筆）；產出 Dynamis HTML。詳見相鄰 basanos/INTEGRATION.md。未複製 Basanos 原始碼或合併模擬核心。

本地整合分支 codex/minisim-integration，基線 revision 2ba99a980913679a2fdd8b156d564c4693e1da9c。初次整合時原 TX source／license 未修改；後續 recorder 修正見下，未 push／merge。本 checkout 沒有 README 所提 core/，本輪不評估其模擬能力。

相鄰 Minisim 的 `tools/run_dynamis_integration.py` 將已經實測的 Minisim／Icarus counter traces 轉成 TX JSONL，再直接執行此 repo 的 tx/tools/txdiff.py（--with-time）與 txview.py（包含 Minisim VCD）。這是交易工具的實際跨 repo 接線，不是 engine 合併或 Minisim DPI 支援。

驗收：clean／width8／increment2 各 96 筆對各自的 RTL reference 一致；三組各注入錯誤值與缺交易，都得到指定 diff，9/9 比較關卡符合預期，另拒絕空輸入並產生 3 HTML。HTML 只驗證產生，未宣稱視覺 QA。證據在相鄰 minisim/build/dynamis-integration/summary.json，契約詳見 minisim/docs/DYNAMIS_INTEGRATION.md。

Helios `scripts/run_dynamis_gate.py` 提供非空輸入與 payload 檢查，保留 SHA／revision、時間比較及 raw diff，不生成 calibration label。其 5 個檢查涵蓋 pass、錯值、缺漏、空輸入、避免覆寫輸入。Dynamis comparator 依 kind 比較，不保證跨 kind 全域順序；後續需按協定定義排序政策。


## 後續修正：TX JSON escaping（2026-11-03）

tx/src/txdpi.cpp 原先直接以%s寫入kind/payload；引號、反斜線與換行等輸入可破壞JSONL。現在逐字元做JSON escaping，0x01..0x1f控制字元輸出為Unicode escape，保留有效UTF-8；null字串明確轉成空字串。API與一般交易schema維持。

`python tx/tests/test_txdpi.py` 用真正native C++ recorder編譯與JSON roundtrip測試普通字串、引號/反斜線、換行/tab/CR、全部非NUL控制字元、UTF-8、空字串，共6類；也檢查null字串。原版3類產生無效JSON，修正版6/6通過。預設需要G++與/usr/share/verilator/include/vltstd/svdpi.h。這是native recorder測試，不冒充完整DPI simulator regression；非UTF-8輸入與嵌入NUL尚未涵蓋。所有檔案保留原授權，未push/merge。

最終原檔回歸：tx/tests/test_txdpi.py **6/6**；另實際執行原 tx_demo_tb 的 Verilator 5.032/DPI demo，**5 筆交易與原 golden（--with-time）一致**。證據位於本聊天可寫目錄 dynamis-followup/repo-evidence.json 與 dpi-regression/summary.json。這增加真實 DPI demo 證據，但不是完整商業模擬器／長時間壓力驗證。


## 2026-11-03 09:20 Taipei：Minisim／Icarus pyuvm交易證據鏈

將原Basanos pyuvm在Minisim VPI產生的500筆交易對照既存Icarus seed0交易：payload與t逐筆一致，兩檔SHA256皆0c5ee26b23a01783bc0cd0f68779771b1ce0cc8dc289ee0e869af4ae2ee32224。另以獨立Python ALU式逐筆檢查500筆結果，五種operation皆出現。新增tests/compare_pyuvm_transactions.py，實際呼叫Dynamis/Helios --with-time四關卡：clean equivalent、錯值／缺筆／時間+1均different，4/4符合預期；每個gate保留input/tool SHA與Dynamis revision，不生成calibration label。

證據minisim/build/pyuvm-cross-backend。這次重用已保存的Icarus baseline，沒有新跑Icarus，也不宣稱一般設計證明；三項負例是交易檔mutant，不是原pyuvm DUT mutant。下一步對原pyuvm suite注入DUT錯誤及整合coverage holes，抽離重複host程式。原portfolio與OpenTitan/OpenCores排程不變，未推送。

## 2026-11-12 — UTF-8 transaction comparison

The comparator and HTML viewer read transaction files as UTF-8. JSONL
records are separated by line feeds, so a Unicode line separator inside
a JSON string stays in the transaction payload. A Windows CLI check
covered CRLF input, a Chinese payload with U+2028, equivalent and
different timestamps, and UTF-8 HTML output. This check used the
Dynamis tools directly.

### Inspecting SystemVerilog class fields

The Verilator DPI fixture in `tx/examples/item_snapshot_tb.sv` records the
same `snapshot_item` before and after an update. Its `do_record` method
exports the private fields `addr`, `data`, `retries`, `valid` and the nested
`header.tag` field. The fixture keeps the existing transaction wire format.

From the saved evidence directory `build/item-dpi-20261112`, use a scratch
copy of the three source files to reproduce the class-field test:

```sh
verilator --binary --timing -j 1 -Wno-fatal --top-module item_snapshot_tb tx_pkg.sv item_snapshot_tb.sv txdpi.cpp
./obj_dir/Vitem_snapshot_tb
mv items.jsonl clean.jsonl
./obj_dir/Vitem_snapshot_tb +corrupt
mv items.jsonl corrupt.jsonl
```

The clean post-update `data` is 17 and the negative case changes it to 18.
The recorded comparison identifies `item.after.data` as the only difference.
The original DPI demo also matched its five golden transactions with time
comparison enabled. See the saved build logs, `commands.jsonl`,
`item-diff.json` and `items.html`.
