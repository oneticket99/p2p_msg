#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-03 — 앱 cold start → 메인 윈도우 노출 시간 측정.

목표: < 2.0s (M2 MacBook 기준) — CheckList.md NFR-03.

본 도구는 PyInstaller 산출물 (dist/TooTalk.app / dist/TooTalk/TooTalk) 의
spawn 시점 → "메인 윈도우 노출" 시점 측정. macOS 의 경우 `open -W -a` 의 startup
overhead 가 있어 spawn 안 fork 직접 측정. Linux/Windows 도 subprocess.Popen 직접.

측정 시점:
1. subprocess.Popen spawn t0
2. 프로세스 의 stdout 안 ready marker 검출 (또는 child process 가용 검출)
3. t1 - t0 = cold start

ready marker: app/main.py 의 init 안 `READY` print 또는 logging.info("ready").
대체: Qt window 가용까지 polling — child pid 의 active window 확인 (manual 보조).

사용:
    python tools/measure_cold_start.py --binary dist/TooTalk.app --iter 5
    python tools/measure_cold_start.py --binary dist/TooTalk/TooTalk --iter 5
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import time


def _resolve_binary(path: str) -> str:
    # 한글 주석 — .app bundle path 의 경우 안 binary 경로 해석 (Contents/MacOS/TooTalk)
    if path.endswith(".app") and os.path.isdir(path):
        macho = os.path.join(path, "Contents", "MacOS", "TooTalk")
        if os.path.exists(macho):
            return macho
        # 한글 주석 — 다른 binary 이름 fallback (Contents/MacOS 안 첫 파일)
        macos_dir = os.path.join(path, "Contents", "MacOS")
        if os.path.isdir(macos_dir):
            candidates = [f for f in os.listdir(macos_dir) if os.access(os.path.join(macos_dir, f), os.X_OK)]
            if candidates:
                return os.path.join(macos_dir, candidates[0])
    return path


def _one_run(binary: str, timeout: float) -> float | None:
    # 한글 주석 — Popen spawn → 'window shown' / 'ready' marker 검출 + elapsed 측정
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")  # 한글 주석 — headless 측정 (GUI display 없음)
    env.setdefault("TOOTALK_COLD_START_PROBE", "1")
    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )
    except OSError as exc:
        print(f"binary spawn 실패: {exc}", file=sys.stderr)
        return None
    ready_t: float | None = None
    deadline = t0 + timeout
    try:
        while time.perf_counter() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                if proc.poll() is not None:
                    break
                continue
            low = line.lower()
            if any(k in low for k in ("ready", "main window", "qmainwindow", "started", "window shown")):
                ready_t = time.perf_counter() - t0
                break
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    return ready_t


def _report(samples: list[float]) -> int:
    # 한글 주석 — 5회 측정 결과 + NFR-03 게이트 (< 2.0s)
    if not samples:
        print("측정 sample 0건 — ready marker 미검출 fail", file=sys.stderr)
        return 1
    avg = statistics.mean(samples)
    minimum = min(samples)
    maximum = max(samples)
    print(f"cold start 측정 — {len(samples)} 회")
    print(f"  평균 = {avg:.3f} s")
    print(f"  min  = {minimum:.3f} s")
    print(f"  max  = {maximum:.3f} s")
    gate = avg < 2.0
    print(f"\nNFR-03 게이트:")
    print(f"  < 2.0s = {'PASS' if gate else 'FAIL'}")
    return 0 if gate else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-03 cold start 측정")
    parser.add_argument("--binary", default="dist/TooTalk.app", help="binary 또는 .app 경로")
    parser.add_argument("--iter", type=int, default=5, help="측정 횟수 (기본 5)")
    parser.add_argument("--timeout", type=float, default=10.0, help="ready marker timeout seconds (기본 10)")
    args = parser.parse_args()
    binary = _resolve_binary(args.binary)
    if not os.path.exists(binary):
        print(f"binary 부재: {binary}", file=sys.stderr)
        return 1
    print(f"binary = {binary}")
    samples: list[float] = []
    for i in range(args.iter):
        t = _one_run(binary, args.timeout)
        if t is not None:
            samples.append(t)
            print(f"  [{i+1}/{args.iter}] {t:.3f} s")
        else:
            print(f"  [{i+1}/{args.iter}] 측정 실패")
    return _report(samples)


if __name__ == "__main__":
    sys.exit(main())
