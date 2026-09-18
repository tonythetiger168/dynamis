# SPDX-License-Identifier: Apache-2.0
"""diffview.py — render a txdiff report as a comparison PNG.
Golden lane vs run lane per transaction kind; mismatches in red.
This is the CI-failure report image for READMEs and PR comments.

usage: python3 diffview.py golden.json run.json [-o diff.png]
"""

import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from txdiff import diff_tx
from txview import load_transactions


def main():
    args = sys.argv[1:]
    a_path, b_path = args[0], args[1]
    out = args[args.index('-o') + 1] if '-o' in args else 'diff.png'
    diffs = diff_tx(a_path, b_path)
    bad = {(d['tx'], d['idx']) for d in diffs}

    def by_kind(txs):
        d = {}
        for t0, t1, k, f in txs:
            d.setdefault(k, []).append((t0, t1, f))
        return d

    ka, kb = by_kind(load_transactions(a_path)), by_kind(load_transactions(b_path))
    kinds = list(dict.fromkeys(list(ka) + list(kb)))
    t_max = max((t1 for kk in (ka, kb) for v in kk.values()
                 for _, t1, _ in v), default=1) * 1.1 + 1

    fig, axes = plt.subplots(len(kinds) * 2, 1,
                             figsize=(10, 1.1 * len(kinds) * 2 + 0.8),
                             sharex=True)
    if len(kinds) == 1:
        axes = [axes]
    fig.suptitle(f"txdiff: {a_path.split('/')[-1]} vs {b_path.split('/')[-1]}"
                 f" — {len(diffs)} difference(s)")

    for i, kind in enumerate(kinds):
        for j, (kk, tag, color) in enumerate(((ka, 'golden', '#1565c0'),
                                              (kb, 'run', '#2e7d32'))):
            ax = axes[i * 2 + j]
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.set_ylabel(f'{kind}\n{tag}', rotation=0, ha='right',
                          va='center', fontsize=8)
            for idx, (t0, t1, fields) in enumerate(kk.get(kind, [])):
                is_bad = (kind, idx) in bad and j == 1
                c, ec = ('#ffcdd2', '#b71c1c') if is_bad else ('#bbdefb', color)
                ax.add_patch(plt.Rectangle(
                    (t0, 0.2), max(t1 - t0, t_max * 0.01), 0.6,
                    facecolor=c, edgecolor=ec, linewidth=2 if is_bad else 1.2))
                lbl = ','.join(fields.values())
                ax.text(t0 + (t1 - t0) / 2, 0.5, lbl, ha='center',
                        va='center', fontsize=8,
                        color='#b71c1c' if is_bad else '#333')
            ax.set_xlim(0, t_max)
    axes[-1].set_xlabel('time')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=110)
    print(f"[diffview] wrote {out} ({len(diffs)} differences highlighted)")


if __name__ == '__main__':
    main()
