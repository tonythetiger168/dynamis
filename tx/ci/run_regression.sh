#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# run_regression.sh — Dynamis TX transaction regression gate.
# Simulates with a REAL simulator (Verilator), records transactions via
# DPI, diffs against golden, and on failure renders an evidence page.
# exit 0 = pass, exit 1 = fail (CI gate).

set -uo pipefail
cd "$(dirname "$0")/.."

export VERILATOR_ROOT="${VERILATOR_ROOT:-/mnt/agents/output/verilator-5.052}"
if [ -x "$VERILATOR_ROOT/bin/verilator" ]; then
  V="$VERILATOR_ROOT/bin/verilator"
else
  V="$(command -v verilator)" || { echo "verilator not found"; exit 2; }
fi

echo "=== [1/3] simulate + record (Verilator + DPI) ==="
cd examples
rm -rf obj_dir tx.jsonl
"$V" --binary --timing -Wno-fatal -I../src ../src/txdpi.cpp tx_demo_tb.sv \
     -o Vdemo > /tmp/tx_ci_build.log 2>&1 || { tail -5 /tmp/tx_ci_build.log; exit 2; }
./obj_dir/Vdemo > /dev/null
cd ..
echo "recorded $(wc -l < examples/tx.jsonl) transactions"

echo "=== [2/3] diff against golden ==="
if python3 tools/txdiff.py tests/golden/tx.jsonl examples/tx.jsonl \
        --json txdiff_report.json; then
    echo "=== CI PASS: transactions equivalent ==="
    exit 0
fi

echo "=== CI FAIL: rendering evidence ==="
python3 tools/txview.py examples/tx.jsonl -o txview_fail.html \
        --title "CI FAILURE - transaction diff"
echo "evidence: txview_fail.html, txdiff_report.json"
exit 1
