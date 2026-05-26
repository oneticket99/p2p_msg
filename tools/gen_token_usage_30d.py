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
# 한글 주석 — cycle 169.541: working dir 동적 resolve + legacy path 합산 (이전 oneticket_toonation + 현 1ticket 양쪽 scan)
# Claude Code projects dir naming = abs_path 의 `/` + `_` + `.` 모두 `-` swap (leading `/` 의 swap = leading `-`)
_PROJECT_SLUG = str(ROOT).replace("/", "-").replace("_", "-").replace(".", "-")
SESSIONS_DIRS = [
    Path.home() / ".claude/projects" / _PROJECT_SLUG,
    Path.home() / ".claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg",
]
SESSIONS_DIR = SESSIONS_DIRS[0]  # backward compat alias (단일 dir reference 보존)
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

    # 한글 주석 — cycle 169.541: 양쪽 SESSIONS_DIRS scan + dedupe (session_id stem 기준)
    _jsonl_paths = []
    _seen_stems = set()
    for _d in SESSIONS_DIRS:
        if not _d.exists():
            continue
        for _p in sorted(_d.glob("*.jsonl")):
            if _p.stem in _seen_stems:
                continue
            _seen_stems.add(_p.stem)
            _jsonl_paths.append(_p)
    for jsonl in _jsonl_paths:
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

    # 한글 주석 — cycle 169.555: 이전 머신 (oneticket_toonation) 의 aggregate backup json merge
    # raw jsonl 부재 → bak json 의 per_day + sessions_summary + totals union 합산.
    # session_id 또는 date 중복 시점 = bak 우선 retain (전 머신 history 보존), 신 entry 추가 only.
    _BAK_JSON = ROOT / "docs/operations/token-usage-30d.json.bak.json"
    if _BAK_JSON.exists():
        try:
            bak = json.loads(_BAK_JSON.read_text(encoding="utf-8"))
            # per_day union (date key 중복 = current 우선 retain)
            _cur_dates = {e["date"] for e in out["per_day"]}
            _merged_pd = list(out["per_day"])
            for _e in bak.get("per_day", []):
                if _e.get("date") not in _cur_dates:
                    _merged_pd.append(_e)
            _merged_pd.sort(key=lambda r: r["date"])
            out["per_day"] = _merged_pd
            # per_day_model union (date+model 복합 키 중복 = current 우선)
            _cur_dm = {(e["date"], e["model"]) for e in out["per_day_model"]}
            _merged_dm = list(out["per_day_model"])
            for _e in bak.get("per_day_model", []):
                if (_e.get("date"), _e.get("model")) not in _cur_dm:
                    _merged_dm.append(_e)
            _merged_dm.sort(key=lambda r: (r["date"], r["model"]))
            out["per_day_model"] = _merged_dm
            # sessions_summary union (session_id 중복 = current 우선)
            _cur_sids = {s["session_id"] for s in out["sessions_summary"]}
            _merged_ss = list(out["sessions_summary"])
            for _s in bak.get("sessions_summary", []):
                if _s.get("session_id") not in _cur_sids:
                    _merged_ss.append(_s)
            _merged_ss.sort(key=lambda r: r.get("first_kst", ""))
            out["sessions_summary"] = _merged_ss
            out["sessions"] = len(_merged_ss)
            # 한글 주석 — 날짜 기준 union 뒤 totals/per_model 재계산: bak 중복 날짜로 총합이 부풀지 않도록 방어
            _fields = ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                       "cache_read_input_tokens", "messages", "total_tokens")
            _new_totals = {k: 0 for k in _fields}
            _new_cost = 0.0
            for _e in out["per_day"]:
                for _k in _fields:
                    _new_totals[_k] += _e.get(_k, 0)
                _new_cost += _e.get("cost_usd", 0.0)
            _new_totals["cost_usd"] = round(_new_cost, 4)
            out["totals"] = _new_totals
            _models = defaultdict(lambda: defaultdict(int))
            for _e in out["per_day_model"]:
                _m = _e.get("model") or "<synthetic>"
                for _k in _fields:
                    _models[_m][_k] += _e.get(_k, 0)
                _models[_m]["cost_usd"] += _e.get("cost_usd", 0.0)
            out["per_model"] = [
                {"model": _m, **{_k: _v for _k, _v in _vals.items() if _k != "cost_usd"},
                 "cost_usd": round(_vals.get("cost_usd", 0.0), 4)}
                for _m, _vals in _models.items()
            ]
            out["parsed_messages"] = out["totals"].get("messages", 0)
            out["files_scanned"] = out.get("files_scanned", 0) + bak.get("files_scanned", 0)
            # cache_hit_rate_percent 재계산
            _ct = out["totals"].get("cache_creation_input_tokens", 0) + out["totals"].get("cache_read_input_tokens", 0)
            out["cache_hit_rate_percent"] = round(
                100.0 * out["totals"].get("cache_read_input_tokens", 0) / _ct if _ct else 0.0, 2,
            )
            # window_start = bak 더 오래된 시점 retain
            _bak_ws = bak.get("window_start_kst")
            if _bak_ws and _bak_ws < out["window_start_kst"]:
                out["window_start_kst"] = _bak_ws
            print(f"[token-usage] bak merge — bak sessions={bak.get('sessions',0)} msgs={bak.get('parsed_messages',0)} cost=${bak.get('totals',{}).get('cost_usd',0):.2f}")
        except Exception as _exc:
            print(f"[token-usage] bak merge 실패 graceful — {_exc!r}")

    # 한글 주석 — cycle 169.556: bak merge 후 HTML render 안 local var reassign (stale list → merged retain)
    per_day_list = out["per_day"]
    per_model_list = out["per_model"]
    per_day_model_list = out["per_day_model"]
    sessions_list = out["sessions_summary"]
    totals = out["totals"]
    parsed_messages = out["parsed_messages"]

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

        # 6 KPI card 갱신 — 총 토큰 + 메시지 + session + 활성 일수 + 추정 비용 + 캐시 적중률
        # 한글 주석 — cycle 169.515 — session 0 graceful (totals dict empty 시점 .get(0) fallback 의무)
        t = out['totals']
        active_days = len(per_day_list)
        total_tokens = t.get('total_tokens', 0)
        # 한글 주석 — cycle 169.541: local var rename `cost_usd` → `cost_total_usd` (module function shadow 회피)
        cost_total_usd = t.get('cost_usd', 0.0)
        avg_daily_token = total_tokens // active_days if active_days else 0
        avg_daily_cost = cost_total_usd / active_days if active_days else 0.0
        cache_read = t.get('cache_read_input_tokens', 0)
        cache_creation = t.get('cache_creation_input_tokens', 0)
        input_tokens = t.get('input_tokens', 0)
        messages_count = t.get('messages', 0)
        cache_denom = cache_read + cache_creation + input_tokens
        cache_hit_pct = (100.0 * cache_read / cache_denom) if cache_denom else 0.0

        kpi_patterns = [
            (r"(<div class=\"label\">총 토큰</div>\s*<div class=\"value\">)[^<]+(</div>)",
             f"\\g<1>{_fmt(total_tokens)}\\g<2>"),
            (r"(<div class=\"label\">총 assistant 메시지</div>\s*<div class=\"value\">)[^<]+(</div>)",
             f"\\g<1>{_fmt(messages_count)}\\g<2>"),
            (r"(<div class=\"label\">분석 session</div>\s*<div class=\"value\">)[^<]+(</div>)",
             f"\\g<1>{len(sessions_list)}\\g<2>"),
            (r"(<div class=\"label\">활성 일수</div>\s*<div class=\"value\">)[^<]+(</div>\s*<div class=\"sub\">일평균 )[^ ]+( token</div>)",
             f"\\g<1>{active_days}\\g<2>{_fmt(avg_daily_token)}\\g<3>"),
            (r"(<div class=\"label\">추정 비용</div>\s*<div class=\"value\">)[^<]+(</div>\s*<div class=\"sub\">일평균 )[^<]+(</div>)",
             f"\\g<1>{_fmt_cost(cost_total_usd)}\\g<2>{_fmt_cost(avg_daily_cost)}\\g<3>"),
            (r"(<div class=\"label\">캐시 적중률</div>\s*<div class=\"value\">)[^<]+(</div>)",
             f"\\g<1>{cache_hit_pct:.1f}%\\g<2>"),
        ]
        n_kpi = 0
        for pat, rep in kpi_patterns:
            new_html, n = re.subn(pat, rep, new_html, count=1)
            n_kpi += n

        # §2 모델별 누계 tbody (synthetic 0-token row 도 표시 — 기존 패턴 유지)
        # 한글 주석 — cycle 169.515 — total_tokens 변수 활용 (session 0 graceful)
        total_t = total_tokens or 1
        per_model_rows = "".join(
            f"<tr><td><span class='chip chip-{m['model']}'>{m['model']}</span></td>"
            f"<td class='num'>{_fmt(m['messages'])}</td>"
            f"<td class='num'>{_fmt(m['input_tokens'])}</td>"
            f"<td class='num'>{_fmt(m['output_tokens'])}</td>"
            f"<td class='num'>{_fmt(m['cache_creation_input_tokens'])}</td>"
            f"<td class='num'>{_fmt(m['cache_read_input_tokens'])}</td>"
            f"<td class='num strong'>{_fmt(m['total_tokens'])}</td>"
            f"<td class='num'>{100.0 * m['total_tokens'] / total_t:.2f}%</td>"
            f"<td class='num cost'>{_fmt_cost(m['cost_usd'])}</td></tr>"
            for m in per_model_list
        )
        new_html, n_pm = re.subn(
            r"(<thead><tr>\s*<th>모델</th><th>메시지</th><th>input</th><th>output</th>\s*<th>cache create</th><th>cache read</th><th>총 토큰</th><th>점유율</th><th>비용 \(USD\)</th>\s*</tr></thead>\s*<tbody>)[\s\S]*?(</tbody>)",
            lambda m: m.group(1) + per_model_rows + m.group(2),
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
        print(f"[token-usage] {HTML_OUT} 갱신 — n_gen={n_gen} n_win={n_win} n_kpi={n_kpi} n_pd={n_pd} n_pm={n_pm} n_pdm={n_pdm} n_sess={n_sess} n_chart={n_chart}")


if __name__ == "__main__":
    main()
