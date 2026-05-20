#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""token-usage-30d.json + html generator — cycle 169.42 신설.

세션 jsonl 4 file aggregate + per_day + per_model + per_day_model + sessions_summary.
docs/operations/token-usage-30d.{json,html} 두 file rewrite.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = Path.home() / ".claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg"
JSON_OUT = ROOT / "docs/operations/token-usage-30d.json"
HTML_OUT = ROOT / "docs/operations/token-usage-30d.html"

PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.5},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.3},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0, "cache_write": 1.25, "cache_read": 0.1},
}


def cost_usd(model: str, usage: dict) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    return (
        usage.get("input_tokens", 0) * p["input"]
        + usage.get("output_tokens", 0) * p["output"]
        + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]
        + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
    ) / 1_000_000


def main() -> None:
    now_kst = datetime.now(KST)
    window_start = now_kst - timedelta(days=30)

    totals = defaultdict(int)
    per_day = defaultdict(lambda: defaultdict(int))
    per_model = defaultdict(lambda: defaultdict(int))
    per_day_model = defaultdict(lambda: defaultdict(int))
    sessions_summary = {}
    files_scanned = 0
    files_with_usage = 0
    parsed_messages = 0
    skipped_lines = 0
    total_cost = 0.0

    for jsonl in sorted(SESSIONS_DIR.glob("*.jsonl")):
        files_scanned += 1
        session_id = jsonl.stem
        session_data = {
            "session_id": session_id,
            "first_ts": None,
            "last_ts": None,
            "models": set(),
            "messages": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        has_usage = False
        with open(jsonl, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    skipped_lines += 1
                    continue
                if d.get("type") != "assistant":
                    continue
                msg = d.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                ts = d.get("timestamp")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KST)
                except Exception:
                    skipped_lines += 1
                    continue
                if dt < window_start:
                    continue
                model = msg.get("model") or "<synthetic>"
                date_key = dt.strftime("%Y-%m-%d")
                has_usage = True
                parsed_messages += 1
                u_input = usage.get("input_tokens", 0) or 0
                u_output = usage.get("output_tokens", 0) or 0
                u_cwrite = usage.get("cache_creation_input_tokens", 0) or 0
                u_cread = usage.get("cache_read_input_tokens", 0) or 0
                u_total = u_input + u_output + u_cwrite + u_cread
                c = cost_usd(model, usage)
                total_cost += c

                totals["input_tokens"] += u_input
                totals["output_tokens"] += u_output
                totals["cache_creation_input_tokens"] += u_cwrite
                totals["cache_read_input_tokens"] += u_cread
                totals["messages"] += 1
                totals["total_tokens"] += u_total

                for d_dict in (per_day[date_key], per_model[model], per_day_model[(date_key, model)]):
                    d_dict["input_tokens"] += u_input
                    d_dict["output_tokens"] += u_output
                    d_dict["cache_creation_input_tokens"] += u_cwrite
                    d_dict["cache_read_input_tokens"] += u_cread
                    d_dict["messages"] += 1
                    d_dict["total_tokens"] += u_total
                    d_dict["cost_usd"] += c

                session_data["models"].add(model)
                session_data["messages"] += 1
                session_data["total_tokens"] += u_total
                session_data["cost_usd"] += c
                if session_data["first_ts"] is None or dt < session_data["first_ts"]:
                    session_data["first_ts"] = dt
                if session_data["last_ts"] is None or dt > session_data["last_ts"]:
                    session_data["last_ts"] = dt
        if has_usage:
            files_with_usage += 1
            sessions_summary[session_id] = session_data

    totals["cost_usd"] = round(total_cost, 4)
    cache_total = totals["cache_creation_input_tokens"] + totals["cache_read_input_tokens"]
    cache_hit = (
        100.0 * totals["cache_read_input_tokens"] / cache_total if cache_total else 0.0
    )

    per_day_list = sorted(
        [{"date": d, **{k: v for k, v in vals.items() if k != "cost_usd"}, "cost_usd": round(vals["cost_usd"], 4)} for d, vals in per_day.items()],
        key=lambda r: r["date"],
    )
    per_model_list = [
        {"model": m, **{k: v for k, v in vals.items() if k != "cost_usd"}, "cost_usd": round(vals["cost_usd"], 4)}
        for m, vals in per_model.items()
    ]
    per_day_model_list = sorted(
        [{"date": k[0], "model": k[1], **{kk: vv for kk, vv in v.items() if kk != "cost_usd"}, "cost_usd": round(v["cost_usd"], 4)}
         for k, v in per_day_model.items()],
        key=lambda r: (r["date"], r["model"]),
    )
    sessions_list = [
        {
            "session_id": s["session_id"],
            "first_kst": s["first_ts"].strftime("%Y-%m-%d %H:%M") if s["first_ts"] else "",
            "last_kst": s["last_ts"].strftime("%Y-%m-%d %H:%M") if s["last_ts"] else "",
            "models": sorted(s["models"]),
            "messages": s["messages"],
            "total_tokens": s["total_tokens"],
            "cost_usd": round(s["cost_usd"], 8),
        }
        for s in sessions_summary.values()
    ]
    sessions_list.sort(key=lambda r: r["first_kst"])

    out = {
        "generated_at_kst": now_kst.strftime("%Y-%m-%d %H:%M:%S KST"),
        "window_start_kst": window_start.strftime("%Y-%m-%d %H:%M:%S"),
        "window_end_kst": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "files_scanned": files_scanned,
        "files_with_usage": files_with_usage,
        "parsed_messages": parsed_messages,
        "sessions": len(sessions_list),
        "skipped_lines": skipped_lines,
        "totals": dict(totals),
        "cache_hit_rate_percent": round(cache_hit, 2),
        "per_day": per_day_list,
        "per_model": per_model_list,
        "per_day_model": per_day_model_list,
        "sessions_summary": sessions_list,
        "pricing": PRICING,
    }

    JSON_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[token-usage] {JSON_OUT} 갱신 — sessions={len(sessions_list)} msgs={parsed_messages} cost=${out['totals']['cost_usd']:.2f}")

    # 한글 주석 — cycle 169.69 회수 (L-1 jinja robust) — escape + multiline + anchor 강화
    if HTML_OUT.exists():
        html = HTML_OUT.read_text(encoding="utf-8")
        import re
        # 한글 주석 — 생성 시각 line — anchor 강화 (<p class="gen"> opening tag)
        gen_pattern = re.compile(
            r'(<p class="gen">생성 시각: )[^·]+(· 집계 윈도우: )[^<]+',
            re.MULTILINE,
        )
        gen_replace = (
            f"\\g<1>{out['generated_at_kst']}\\g<2>"
            f"{out['window_start_kst']} ~ {out['window_end_kst']}"
        )
        new_html, n_gen = gen_pattern.subn(gen_replace, html, count=1)
        if n_gen == 0:
            # fallback (legacy pattern)
            new_html = re.sub(
                r"생성 시각: [^·]+· 집계 윈도우: [^<]+",
                f"생성 시각: {out['generated_at_kst']} · 집계 윈도우: {out['window_start_kst']} ~ {out['window_end_kst']}",
                html,
                count=1,
            )

        # 한글 주석 — 집계 윈도우 table row — th 안 KST text + td 내용 정확 match
        window_pattern = re.compile(
            r"(<th>집계 윈도우\s*\(KST\)</th>\s*<td>)[^<]+(</td>)"
        )
        window_replace = f"\\g<1>{out['window_start_kst']} ~ {out['window_end_kst']}\\g<2>"
        new_html, n_win = window_pattern.subn(window_replace, new_html, count=1)

        # 한글 주석 — cycle 169.87 회수 — 4 tbody dynamic re-render (stale row 차단)
        def _fmt(n):
            return f"{int(n):,}"

        def _fmt_cost(c):
            return f"${float(c):,.2f}"

        # §5 일별 누계 tbody
        per_day_rows = "".join(
            f"<tr><td>{r['date']}</td>"
            f"<td class='num'>{_fmt(r['messages'])}</td>"
            f"<td class='num'>{_fmt(r['input_tokens'])}</td>"
            f"<td class='num'>{_fmt(r['output_tokens'])}</td>"
            f"<td class='num'>{_fmt(r['cache_creation_input_tokens'])}</td>"
            f"<td class='num'>{_fmt(r['cache_read_input_tokens'])}</td>"
            f"<td class='num strong'>{_fmt(r['total_tokens'])}</td>"
            f"<td class='num cost'>{_fmt_cost(r['cost_usd'])}</td></tr>"
            for r in per_day_list
        )
        new_html, n_pd = re.subn(
            r"(<thead><tr>\s*<th>날짜 \(KST\)</th><th>메시지</th><th>input</th><th>output</th>\s*<th>cache create</th><th>cache read</th><th>총 토큰</th><th>비용 \(USD\)</th>\s*</tr></thead>\s*<tbody>)[\s\S]*?(</tbody>)",
            lambda m: m.group(1) + per_day_rows + m.group(2),
            new_html, count=1,
        )

        # §6 일자×모델 cross-tab tbody
        pdm_rows = "".join(
            f"<tr><td>{r['date']}</td>"
            f"<td><span class='chip chip-{r['model']}'>{r['model']}</span></td>"
            f"<td class='num'>{_fmt(r['messages'])}</td>"
            f"<td class='num'>{_fmt(r['total_tokens'])}</td>"
            f"<td class='num cost'>{_fmt_cost(r['cost_usd'])}</td></tr>"
            for r in per_day_model_list
            if r.get('total_tokens', 0) > 0 and r.get('model') != '<synthetic>'
        )
        new_html, n_pdm = re.subn(
            r"(<thead><tr>\s*<th>날짜 \(KST\)</th><th>모델</th><th>메시지</th><th>총 토큰</th><th>비용 \(USD\)</th>\s*</tr></thead>\s*<tbody>)[\s\S]*?(</tbody>)",
            lambda m: m.group(1) + pdm_rows + m.group(2),
            new_html, count=1,
        )

        # §7 session 단위 누계 tbody
        sess_rows = "".join(
            f"<tr><td><code>{r['session_id'][:8]}</code></td>"
            f"<td>{r['first_kst']}</td>"
            f"<td>{r['last_kst']}</td>"
            f"<td>{', '.join(sorted(r['models']))}</td>"
            f"<td class='num'>{_fmt(r['messages'])}</td>"
            f"<td class='num'>{_fmt(r['total_tokens'])}</td></tr>"
            for r in sessions_list
        )
        new_html, n_sess = re.subn(
            r"(<thead><tr>\s*<th>session</th><th>첫 활동 \(KST\)</th><th>마지막 활동 \(KST\)</th>\s*<th>모델</th><th>메시지</th><th>총 토큰</th>\s*</tr></thead>\s*<tbody>)[\s\S]*?(</tbody>)",
            lambda m: m.group(1) + sess_rows + m.group(2),
            new_html, count=1,
        )

        # 차트 D dict 갱신 — dates + per-day arrays + model totals
        dates = [r['date'] for r in per_day_list]
        chart_d = {
            "dates": dates,
            "total": [r['total_tokens'] for r in per_day_list],
            "input": [r['input_tokens'] for r in per_day_list],
            "output": [r['output_tokens'] for r in per_day_list],
            "cache_create": [r['cache_creation_input_tokens'] for r in per_day_list],
            "cache_read": [r['cache_read_input_tokens'] for r in per_day_list],
            "cost": [r['cost_usd'] for r in per_day_list],
            "model_labels": [m['model'] for m in per_model_list],
            "model_totals": [m['total_tokens'] for m in per_model_list],
            "model_costs": [m['cost_usd'] for m in per_model_list],
        }
        chart_json = json.dumps(chart_d, ensure_ascii=False)
        new_html, n_chart = re.subn(
            r"const D = \{[\s\S]*?\};",
            f"const D = {chart_json};",
            new_html, count=1,
        )

        HTML_OUT.write_text(new_html, encoding="utf-8")
        print(f"[token-usage] {HTML_OUT} timestamp 갱신 — n_gen={n_gen} n_win={n_win} n_pd={n_pd} n_pdm={n_pdm} n_sess={n_sess} n_chart={n_chart}")


if __name__ == "__main__":
    main()
