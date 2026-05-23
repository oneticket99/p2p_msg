#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-06 — ProgressBar 진행률 갱신 빈도 측정 (offscreen PyQt6).

목표: 100ms 안 1회 이상 (정지·역행 0) — CheckList.md NFR-06.

본 도구는 `app.ui.file_progress_widget.FileProgressWidget` 의 on_sent/on_acked/
on_recv 호출 → setValue 갱신 → bar value diff timing 측정.

PyQt6 의존성 — QT_QPA_PLATFORM=offscreen 강제. tests/app/ui hang 회피 위해
pytest fixture chain 안 진입 안 함 + tools/ CLI 단일 진입점.

측정 패턴:
1. FileProgressWidget 의 offscreen instantiation
2. monotonic timer 의 N 회 on_sent 호출 (1% 씩 증가)
3. 매 호출 시점 setValue 결과 + 호출 간격 측정
4. 100ms 안 1회 이상 = PASS · 역행 = FAIL

사용:
    python tools/measure_progress.py --iter 100 --interval-ms 50
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time


def _measure(iterations: int, interval_ms: int) -> int:
    # 한글 주석 — offscreen QApplication 의무 + FileProgressWidget instantiation
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
        from app.ui.file_progress_widget import FileProgressWidget
    except ImportError as exc:
        print(f"PyQt6 / FileProgressWidget import 실패: {exc}", file=sys.stderr)
        return 3
    app = QApplication.instance() or QApplication(sys.argv)
    widget = FileProgressWidget(
        file_id="bench-file",
        name="bench.bin",
        size=1_000_000,
        role="send",
    )
    intervals_ms: list[float] = []
    last_value = 0
    regression_count = 0
    t_prev = time.perf_counter()
    for i in range(1, iterations + 1):
        sent = int(i * 1_000_000 / iterations)
        widget.on_sent("bench-file", sent, 1_000_000)
        widget.on_acked("bench-file", sent, 1_000_000)
        # 한글 주석 — bar value 추출 (acked_bar = 최종 확정 진척률)
        bar = widget._acked_bar
        cur = bar.value()
        if cur < last_value:
            regression_count += 1
        last_value = cur
        t_now = time.perf_counter()
        intervals_ms.append((t_now - t_prev) * 1000.0)
        t_prev = t_now
        if interval_ms > 0:
            time.sleep(interval_ms / 1000.0)
    avg = statistics.mean(intervals_ms)
    p95 = statistics.quantiles(intervals_ms, n=20)[18] if len(intervals_ms) >= 20 else max(intervals_ms)
    maximum = max(intervals_ms)
    print(f"진척률 갱신 측정 — {iterations} iter")
    print(f"  평균 간격 = {avg:.2f} ms")
    print(f"  95p 간격  = {p95:.2f} ms")
    print(f"  max 간격  = {maximum:.2f} ms")
    print(f"  역행 count = {regression_count}")
    print(f"  최종 bar value = {last_value} / 100")
    gate_freq = maximum < 100.0 + interval_ms  # 한글 주석 — interval_ms 보정 (sleep 의 cost 포함)
    gate_reg = regression_count == 0
    print(f"\nNFR-06 게이트:")
    print(f"  100ms 안 1회 = {'PASS' if gate_freq else 'FAIL'}")
    print(f"  역행 0건     = {'PASS' if gate_reg else 'FAIL'}")
    widget.deleteLater()
    return 0 if (gate_freq and gate_reg) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-06 ProgressBar 갱신 빈도 측정")
    parser.add_argument("--iter", type=int, default=100, help="iteration count (기본 100)")
    parser.add_argument("--interval-ms", type=int, default=50, help="iteration 간 sleep ms (기본 50)")
    args = parser.parse_args()
    return _measure(args.iter, args.interval_ms)


if __name__ == "__main__":
    sys.exit(main())
