#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""WBS sqlite → static HTML viewer (cycle 169.561 신설).

data/wbs.sqlite 의 wbs_tasks 전수 row → docs/operations/wbs.html 생성.

기능:
- KPI 6 card (total / done / pending / in_progress / latest cycle / latest sha)
- cycle prefix group breakdown (top 20)
- 전체 row table (sortable header + status filter chip + cycle search input)
- vanilla CSS/JS (외부 의존 부재) + Toonation BI accent
"""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "wbs.sqlite"
HTML_OUT = ROOT / "docs/operations/wbs.html"
KST = timezone(timedelta(hours=9))


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"[wbs_view] {DB_PATH} 부재 — tools/wbs_init.py 선행 의무")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT cycle, directive, status, started_at, finished_at, commit_sha "
        "FROM wbs_tasks ORDER BY id DESC",
    )
    rows = [dict(r) for r in cur.fetchall()]

    total = len(rows)
    by_status = Counter(r["status"] for r in rows)
    latest_cycle = rows[0]["cycle"] if rows else "-"
    latest_sha = (rows[0]["commit_sha"] or "-")[:7] if rows else "-"
    latest_finished = (rows[0]["finished_at"] or "-")[:19] if rows else "-"

    prefixes = Counter()
    for r in rows:
        cyc = r["cycle"]
        prefix = ".".join(cyc.split(".")[:2]) if "." in cyc else cyc
        prefixes[prefix] += 1
    top_prefixes = prefixes.most_common(20)

    row_html = []
    for r in rows:
        cycle = html.escape(r["cycle"])
        status = html.escape(r["status"])
        sha = html.escape((r["commit_sha"] or "")[:7])
        finished = html.escape((r["finished_at"] or "")[:19])
        directive = html.escape(r["directive"])
        icon = {"done": "✓", "pending": "·", "in_progress": "→"}.get(r["status"], "?")
        row_html.append(
            f'<tr data-status="{status}" data-cycle="{cycle}">'
            f'<td class="icon">{icon}</td>'
            f'<td class="cycle">{cycle}</td>'
            f'<td class="status status-{status}">{status}</td>'
            f'<td class="sha"><code>{sha}</code></td>'
            f'<td class="finished">{finished}</td>'
            f'<td class="directive">{directive}</td>'
            f'</tr>'
        )

    prefix_chips = "".join(
        f'<span class="chip">{html.escape(p)} <em>{c}</em></span>'
        for p, c in top_prefixes
    )

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    html_body = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TooTalk WBS — directive row viewer</title>
<!-- 한글 주석: data/wbs.sqlite → static HTML. tools/gen_wbs_view.py 생성. -->
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#fafafa;color:#1f2937;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Roboto,sans-serif;font-size:14px;line-height:1.6}}
main{{max-width:1280px;margin:0 auto;padding:28px 24px 80px}}
header{{border-left:4px solid #7c3aed;padding:4px 0 4px 16px;margin-bottom:24px}}
header h1{{margin:0 0 6px;font-size:24px;color:#1f2937}}
header .meta{{font-size:12.5px;color:#6b7280}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:0 0 20px}}
.kpi .card{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px}}
.kpi .card .label{{font-size:11.5px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}}
.kpi .card .value{{font-size:20px;font-weight:700;color:#5b21b6}}
.kpi .card.done .value{{color:#16a34a}}
.kpi .card.pending .value{{color:#f59e0b}}
.kpi .card.in_progress .value{{color:#2563eb}}
.section-title{{font-size:13px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;margin:24px 0 10px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px}}
.chip{{display:inline-flex;align-items:center;gap:4px;background:#ede9fe;color:#5b21b6;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:500}}
.chip em{{font-style:normal;font-weight:700;color:#7c3aed}}
.filters{{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center}}
.filters input{{flex:1;min-width:200px;padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;font-family:inherit}}
.filter-btn{{background:#fff;border:1px solid #d1d5db;border-radius:6px;padding:6px 12px;font-size:12px;cursor:pointer;font-family:inherit;color:#4b5563}}
.filter-btn.active{{background:#7c3aed;color:#fff;border-color:#7c3aed}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;font-size:13px}}
th,td{{border-bottom:1px solid #f3f4f6;padding:7px 10px;text-align:left;vertical-align:top}}
th{{background:#7c3aed;color:#fff;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;cursor:pointer;user-select:none}}
th:hover{{background:#6d28d9}}
td.icon{{width:24px;color:#7c3aed;font-weight:700;text-align:center}}
td.cycle{{white-space:nowrap;font-family:"SFMono-Regular",Menlo,Consolas,monospace;font-size:12.5px}}
td.status{{white-space:nowrap;font-size:11.5px;text-transform:uppercase;font-weight:600;letter-spacing:0.4px}}
td.status-done{{color:#16a34a}}
td.status-pending{{color:#f59e0b}}
td.status-in_progress{{color:#2563eb}}
td.sha code{{background:#ede9fe;padding:1px 6px;border-radius:3px;font-size:11.5px;color:#5b21b6}}
td.finished{{white-space:nowrap;font-size:12px;color:#6b7280;font-family:"SFMono-Regular",Menlo,Consolas,monospace}}
td.directive{{font-size:13px;color:#1f2937}}
tr:nth-child(even) td{{background:#fafafa}}
tr.hide{{display:none}}
footer{{margin-top:32px;padding-top:18px;border-top:1px solid #e5e7eb;font-size:12px;color:#6b7280;text-align:center}}
</style>
</head>
<body>
<main>
<header>
  <h1>TooTalk WBS — directive row viewer</h1>
  <div class="meta">생성 시각 = {now_kst} · DB = <code>data/wbs.sqlite</code> · tool = <code>tools/gen_wbs_view.py</code></div>
</header>

<section class="kpi">
  <div class="card"><div class="label">total row</div><div class="value">{total}</div></div>
  <div class="card done"><div class="label">done</div><div class="value">{by_status.get("done", 0)}</div></div>
  <div class="card pending"><div class="label">pending</div><div class="value">{by_status.get("pending", 0)}</div></div>
  <div class="card in_progress"><div class="label">in_progress</div><div class="value">{by_status.get("in_progress", 0)}</div></div>
  <div class="card"><div class="label">latest cycle</div><div class="value">{html.escape(latest_cycle)}</div></div>
  <div class="card"><div class="label">latest sha</div><div class="value"><code>{html.escape(latest_sha)}</code></div></div>
</section>

<div class="section-title">cycle prefix group (top 20)</div>
<div class="chips">{prefix_chips}</div>

<div class="section-title">directive row ({total})</div>
<div class="filters">
  <input id="search" placeholder="cycle 또는 directive 검색…" autocomplete="off">
  <button class="filter-btn active" data-filter="all">전체</button>
  <button class="filter-btn" data-filter="done">done</button>
  <button class="filter-btn" data-filter="pending">pending</button>
  <button class="filter-btn" data-filter="in_progress">in_progress</button>
</div>

<table id="wbs-table">
  <thead><tr>
    <th></th>
    <th>cycle</th>
    <th>status</th>
    <th>sha</th>
    <th>finished_at (KST)</th>
    <th>directive</th>
  </tr></thead>
  <tbody>
    {"".join(row_html)}
  </tbody>
</table>

<footer>
  TooTalk(p2p_msg) · WBS M6 cache · directive 1건 = 1 row 등록 + status 갱신 · CLAUDE_HARNESS_IMPORTANT.md §A M6 정합
</footer>

<script>
(function() {{
  const rows = document.querySelectorAll('#wbs-table tbody tr');
  const searchInput = document.getElementById('search');
  const buttons = document.querySelectorAll('.filter-btn');
  let activeFilter = 'all';

  function applyFilter() {{
    const q = (searchInput.value || '').toLowerCase().trim();
    rows.forEach(tr => {{
      const status = tr.dataset.status;
      const cycle = (tr.dataset.cycle || '').toLowerCase();
      const directive = tr.querySelector('td.directive').textContent.toLowerCase();
      const matchStatus = activeFilter === 'all' || status === activeFilter;
      const matchQuery = !q || cycle.includes(q) || directive.includes(q);
      tr.classList.toggle('hide', !(matchStatus && matchQuery));
    }});
  }}

  buttons.forEach(b => b.addEventListener('click', () => {{
    buttons.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    activeFilter = b.dataset.filter;
    applyFilter();
  }}));
  searchInput.addEventListener('input', applyFilter);
}})();
</script>
</main>
</body>
</html>
"""

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html_body, encoding="utf-8")
    print(f"[wbs_view] {HTML_OUT} 갱신 — total={total} done={by_status.get('done', 0)}")
    conn.close()


if __name__ == "__main__":
    main()
