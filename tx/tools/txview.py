# SPDX-License-Identifier: Apache-2.0
"""txview.py — Dynamis View v0.1: transaction waveform renderer.

Reads a transaction database and optional VCD, emits a single
self-contained interactive HTML (pan/zoom, native tooltips).
No dependencies, no server — open the file in any browser.

usage:
  python3 txview.py tx.json [--vcd tx.vcd] [-o txview.html] [--title NAME]

Input formats (auto-detected):
  - Dynamis Core JSON:  [{"t0":..,"t1":..,"kind":..,"fields":{..}}]
  - Dynamis TX JSONL:   {"kind":..,"t":..,"payload":"k=v,k=v"}   (per line)
"""

import json
import re
import sys


# ---------------- input normalization ----------------

def load_transactions(path):
    """Return list of (t0, t1, kind, {field: value})."""
    raw = open(path).read().strip()
    txs = []
    if raw.startswith('['):                       # Dynamis Core JSON
        for r in json.loads(raw):
            txs.append((r['t0'], r['t1'], r['kind'],
                        {k: str(v) for k, v in r['fields'].items()}))
    else:                                         # DPI JSONL
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            fields = {}
            for kv in (r.get('payload') or '').split(','):
                if '=' in kv:
                    k, v = kv.split('=', 1)
                    fields[k.strip()] = v.strip()
            txs.append((r['t'], r['t'], r['kind'], fields))
    return txs


def load_vcd(path):
    """Minimal VCD parser: {name: [(t, value_str), ...]} ordered."""
    sigs, ids = {}, {}
    cur = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('$var'):
                _, _, w, i, name = line.split()[:5]
                ids[i] = (name, int(w))
                sigs.setdefault(name, [])
            elif line.startswith('$enddefinitions'):
                pass
            elif line.startswith('#'):
                cur = int(line[1:])
            elif line and line[0] in '01xz':
                i = line[1:]
                if i in ids:
                    sigs[ids[i][0]].append((cur, line[0]))
            elif line.startswith('b'):
                v, i = line[1:].split()
                if i in ids:
                    sigs[ids[i][0]].append((cur, v))
    return sigs


# ---------------- SVG rendering ----------------

LANE_H = 44
SIG_H = 30
LEFT_W = 150
TOP_H = 30


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def tx_svg(txs, x, t_max):
    """Transaction lanes; returns (svg_rows, lane_kinds)."""
    kinds = []
    for t0, t1, k, _ in txs:
        if k not in kinds:
            kinds.append(k)
    rows = []
    for lane, kind in enumerate(kinds):
        y = TOP_H + lane * LANE_H
        rows.append(f'<text x="{LEFT_W - 8}" y="{y + LANE_H // 2 + 4}" '
                    f'text-anchor="end" class="lbl">{esc(kind)}</text>')
        rows.append(f'<line x1="{LEFT_W}" y1="{y + LANE_H}" x2="{x(t_max)}" '
                    f'y2="{y + LANE_H}" class="grid"/>')
        for t0, t1, k, fields in txs:
            if k != kind:
                continue
            tip = f'{kind} @ {t0}' + ''.join(
                f'\n{esc(fk)} = {esc(fv)}' for fk, fv in fields.items())
            search = f'{kind} ' + ','.join(f'{fk}={fv}'
                                           for fk, fv in fields.items())
            if t1 > t0:                       # span: block
                rows.append(
                    f'<rect x="{x(t0)}" y="{y + 10}" width="{max(x(t1) - x(t0), 2)}" '
                    f'height="{LANE_H - 20}" rx="3" class="span" '
                    f'data-tx="{esc(search)}">'
                    f'<title>{esc(tip)}</title></rect>')
                if x(t1) - x(t0) > 40:
                    lbl = ','.join(fields.values()) or kind
                    rows.append(f'<text x="{x((t0 + t1) / 2)}" y="{y + LANE_H // 2 + 4}" '
                                f'text-anchor="middle" class="txlbl">{esc(lbl)}</text>')
            else:                             # point: diamond
                cx, cy = x(t0), y + LANE_H // 2
                d = 7
                rows.append(
                    f'<path d="M{cx} {cy - d} L{cx + d} {cy} L{cx} {cy + d} '
                    f'L{cx - d} {cy} Z" class="pt" data-tx="{esc(search)}">'
                    f'<title>{esc(tip)}</title></path>')
    return rows, kinds


def vcd_svg(vcd, x, t_max, y0):
    """Signal waveform rows below transaction lanes."""
    rows = []
    y = y0
    for name, changes in vcd.items():
        rows.append(f'<text x="{LEFT_W - 8}" y="{y + SIG_H // 2 + 4}" '
                    f'text-anchor="end" class="lbl sig">{esc(name)}</text>')
        rows.append(f'<line x1="{LEFT_W}" y1="{y + SIG_H}" x2="{x(t_max)}" '
                    f'y2="{y + SIG_H}" class="grid"/>')
        pts = [(0, changes[0][1] if changes else '0')] + changes + [(t_max, changes[-1][1] if changes else '0')]
        prev_y = y + SIG_H - 6
        for (ta, va), (tb, _) in zip(pts, pts[1:]):
            if va in ('0', '1'):
                yy = y + SIG_H - 6 if va == '1' else y + SIG_H - 4
                # draw step: horizontal at level, vertical transition
                lvl_hi, lvl_lo = y + 6, y + SIG_H - 6
                yy = lvl_hi if va == '1' else lvl_lo
                rows.append(f'<line x1="{x(ta)}" y1="{yy}" x2="{x(tb)}" y2="{yy}" class="wave"/>')
                rows.append(f'<line x1="{x(tb)}" y1="{lvl_hi}" x2="{x(tb)}" y2="{lvl_lo}" class="wave"/>')
            else:
                rows.append(f'<line x1="{x(ta)}" y1="{y + SIG_H // 2}" x2="{x(tb)}" '
                            f'y2="{y + SIG_H // 2}" class="wavex"/>')
        y += SIG_H
    return rows, y


HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
 body {{ font: 13px system-ui, sans-serif; margin: 0; background: #fafafa; }}
 #hdr {{ padding: 8px 12px; background: #1a237e; color: #fff; }}
 svg {{ display: block; cursor: grab; }}
 .lbl {{ font-size: 12px; fill: #333; }}
 .lbl.sig {{ fill: #555; font-size: 11px; }}
 .grid {{ stroke: #ddd; stroke-width: 1; }}
 .span {{ fill: #ffe0b2; stroke: #e65100; stroke-width: 1.5; }}
 .pt {{ fill: #e65100; }}
 .txlbl {{ font-size: 10px; fill: #e65100; pointer-events: none; }}
 .wave {{ stroke: #1565c0; stroke-width: 1.5; }}
 .wavex {{ stroke: #b71c1c; stroke-width: 1.5; stroke-dasharray: 4 2; }}
 .tick {{ stroke: #bbb; stroke-width: 1; }}
 .ticklbl {{ font-size: 10px; fill: #666; }}
 .hit {{ stroke: #d50000; stroke-width: 3; fill: #ef9a9a; }}
 .dim {{ opacity: 0.1; }}
 #q {{ margin-left: 16px; padding: 3px 8px; width: 220px; border: 0;
      border-radius: 3px; }}
 #cnt {{ margin-left: 8px; font-size: 12px; opacity: .85; }}
</style></head><body>
<div id="hdr"><b>{title}</b> — drag to pan, wheel to zoom
<input id="q" placeholder="search: addr==3, data&gt;10, or free text">
<span id="cnt"></span></div>
<svg id="view" width="100%" height="{height}">
<g id="world">{body}</g>
</svg>
<script>
const svg = document.getElementById('view');
const world = document.getElementById('world');
let scale = 1, tx = 0, ty = 0, drag = null;
function apply() {{ world.setAttribute('transform', `translate(${{tx}},${{ty}}) scale(${{scale}})`); }}
svg.addEventListener('wheel', e => {{
  const f = e.deltaY < 0 ? 1.2 : 1 / 1.2;
  const r = svg.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  tx = mx - (mx - tx) * f;  ty = my - (my - ty) * f;  scale *= f;
  apply(); e.preventDefault();
}}, {{ passive: false }});
svg.addEventListener('mousedown', e => drag = [e.clientX - tx, e.clientY - ty]);
window.addEventListener('mousemove', e => {{ if (drag) {{ tx = e.clientX - drag[0]; ty = e.clientY - drag[1]; apply(); }} }});
window.addEventListener('mouseup', () => drag = null);

// ---- transaction search: field predicates or free text; Enter jumps ----
const q = document.getElementById('q'), cnt = document.getElementById('cnt');
let hits = [], hidx = -1;
function parseQuery(s) {{
  s = s.trim();
  const m = s.match(/^([\\w.]+)\\s*(==|=|!=|>=|<=|>|<)\\s*(.+)$/);
  if (m) return {{ k: m[1], op: m[2], v: m[3] }};
  return s ? {{ text: s.toLowerCase() }} : null;
}}
function matchEl(el, query) {{
  const s = el.dataset.tx;
  if (query.text) return s.toLowerCase().includes(query.text);
  const m = s.match(new RegExp('(?:^|,)\\\\s*' + query.k + '=([^,]*)'));
  if (!m) return false;
  const a = m[1], b = query.v;
  const na = Number(a), nb = Number(b);
  const cmp = (isNaN(na) || isNaN(nb)) ? String(a).localeCompare(String(b))
                                       : na - nb;
  switch (query.op) {{
    case '==': case '=': return cmp === 0;
    case '!=': return cmp !== 0;
    case '>':  return cmp > 0;
    case '<':  return cmp < 0;
    case '>=': return cmp >= 0;
    case '<=': return cmp <= 0;
  }}
  return false;
}}
function doSearch(jump) {{
  const query = parseQuery(q.value);
  hits = [];
  document.querySelectorAll('[data-tx]').forEach(el => {{
    const on = query && matchEl(el, query);
    el.classList.toggle('hit', !!on);
    el.classList.toggle('dim', !!query && !on);
    if (on) hits.push(el);
  }});
  cnt.textContent = query ? hits.length + ' match(es)' : '';
  if (jump && hits.length) {{
    hidx = (hidx + 1) % hits.length;
    const bb = hits[hidx].getBBox();
    const wx = bb.x + bb.width / 2;
    const r = svg.getBoundingClientRect();
    tx = r.width / 2 - wx * scale;   // center on match, keep zoom
    apply();
  }}
}}
q.addEventListener('input', () => {{ hidx = -1; doSearch(false); }});
q.addEventListener('keydown', e => {{ if (e.key === 'Enter') doSearch(true); }});
</script></body></html>"""


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    src = args[0]
    vcd_path = args[args.index('--vcd') + 1] if '--vcd' in args else None
    out = args[args.index('-o') + 1] if '-o' in args else 'txview.html'
    title = args[args.index('--title') + 1] if '--title' in args else 'Dynamis View'
    txs = load_transactions(src)
    vcd = load_vcd(vcd_path) if vcd_path else {}
    t_max = max([t1 for _, t1, _, _ in txs] + [0])
    if vcd:
        t_max = max(t_max, max((c[-1][0] for c in vcd.values()), default=0))
    t_max = t_max * 1.05 + 1
    W = 1200
    x = lambda t: LEFT_W + t / t_max * (W - LEFT_W - 20)

    body, kinds = tx_svg(txs, x, t_max)
    y_end = TOP_H + len(kinds) * LANE_H
    if vcd:
        rows, y_end = vcd_svg(vcd, x, t_max, y_end)
        body += rows
    # time axis ticks
    for i in range(11):
        t = t_max * i / 10
        body.append(f'<line x1="{x(t)}" y1="{TOP_H}" x2="{x(t)}" y2="{y_end}" class="tick"/>')
        body.append(f'<text x="{x(t)}" y="{TOP_H - 8}" text-anchor="middle" class="ticklbl">{int(t)}</text>')
    height = y_end + 40
    open(out, 'w').write(HTML.format(title=esc(title), height=height,
                                     body='\n'.join(body)))
    print(f"[txview] {out}: {len(txs)} transactions, "
          f"{len(vcd)} signals, t_max={t_max:.0f}")


if __name__ == '__main__':
    main()
