# SPDX-License-Identifier: Apache-2.0
"""txdiff.py — Dynamis regression diff for transaction databases.

Compares two transaction DBs (Dynamis Core JSON or DPI JSONL) and
reports transactions that are missing, extra, or field-mismatched.
The CI gate: exit 0 = equivalent, exit 1 = differences found.

usage:
  python3 txdiff.py golden.json run.json [--ignore-time] [--json report.json]

Comparison is per-kind, in-order (transaction N of kind K in run A is
compared against transaction N of kind K in run B). Exact timestamps
are ignored by default — regression equivalence is about WHAT happened,
not exactly WHEN (use --ignore-time off to compare timestamps too).
"""

import json
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from txview import load_transactions      # reuse the normalizer


def diff_tx(a_path, b_path, ignore_time=True):
    """Return list of difference records."""
    a = load_transactions(a_path)
    b = load_transactions(b_path)
    diffs = []

    def by_kind(txs):
        d = {}
        for t0, t1, k, f in txs:
            d.setdefault(k, []).append((t0, t1, f))
        return d

    ka, kb = by_kind(a), by_kind(b)
    for kind in sorted(set(ka) | set(kb)):
        la, lb = ka.get(kind, []), kb.get(kind, [])
        n = max(len(la), len(lb))
        for i in range(n):
            if i >= len(la):
                diffs.append({'kind': 'extra', 'tx': kind, 'idx': i,
                              'in': 'B', 'fields': lb[i][2]})
                continue
            if i >= len(lb):
                diffs.append({'kind': 'missing', 'tx': kind, 'idx': i,
                              'in': 'A', 'fields': la[i][2]})
                continue
            (t0a, t1a, fa), (t0b, t1b, fb) = la[i], lb[i]
            mism = {fk: (fa.get(fk), fb.get(fk))
                    for fk in sorted(set(fa) | set(fb)) if fa.get(fk) != fb.get(fk)}
            if mism:
                diffs.append({'kind': 'fields', 'tx': kind, 'idx': i,
                              'mismatches': mism})
            elif not ignore_time and (t0a, t1a) != (t0b, t1b):
                diffs.append({'kind': 'time', 'tx': kind, 'idx': i,
                              'a': [t0a, t1a], 'b': [t0b, t1b]})
    return diffs


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    a, b = args[0], args[1]
    ignore_time = '--with-time' not in args
    diffs = diff_tx(a, b, ignore_time)

    if '--json' in args:
        out = args[args.index('--json') + 1]
        with open(out, 'w') as f:
            json.dump({'a': a, 'b': b, 'diffs': diffs}, f, indent=1)
        print(f"[txdiff] report -> {out}")

    if not diffs:
        print("[txdiff] EQUIVALENT — no transaction differences")
        sys.exit(0)
    print(f"[txdiff] {len(diffs)} difference(s):")
    for d in diffs:
        if d['kind'] == 'fields':
            m = ', '.join(f"{k}: {va!r} != {vb!r}"
                          for k, (va, vb) in d['mismatches'].items())
            print(f"  FIELD MISMATCH  {d['tx']}[{d['idx']}]  {m}")
        else:
            print(f"  {d['kind'].upper():15s} {d['tx']}[{d['idx']}]"
                  f"  fields={d.get('fields', d.get('mismatches', ''))}")
    sys.exit(1)


if __name__ == '__main__':
    main()
