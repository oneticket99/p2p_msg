#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-04 — 시그널링 단절 후 자동 재연결 성공률 측정 (chaos test).

목표: 30초 안 99% 이상 (CheckList.md NFR-04).

본 도구는 client 측 ws 강제 close + reconnect chain 의 success rate 측정.
실 server 안 chaos (kill -9 / network partition) 는 manual 의무 — 본 도구는
**client reconnect resilience** 측정.

측정 패턴:
1. ws client 의 JOIN 성공 후 OFFER 1건 송신 (warm-up)
2. ws client 의 force close (서버 단절 시뮬레이션)
3. 새 ws client 의 reconnect + JOIN 재성공 시점 측정 (30초 budget)
4. N 회 반복 → success rate 계산

사용:
    python tools/chaos_signaling.py --url ws://localhost:8765/ws --iter 20
    python tools/chaos_signaling.py --url ws://114.207.112.73:8765/ws --iter 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time

import aiohttp


async def _attempt_reconnect(
    url: str, room: str, peer_id: str, budget_seconds: float
) -> tuple[bool, float]:
    # 한글 주석 — budget 안 reconnect + JOIN 재성공 시점 측정 (지수 backoff 0.5/1.0/2.0/4.0 s)
    t0 = time.perf_counter()
    backoffs = [0.5, 1.0, 2.0, 4.0, 4.0, 4.0, 4.0, 4.0]
    attempt = 0
    while True:
        elapsed = time.perf_counter() - t0
        if elapsed >= budget_seconds:
            return False, elapsed
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url, timeout=3) as ws:
                    await ws.send_json({"type": "JOIN", "room": room, "peer_id": peer_id})
                    msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        payload = json.loads(msg.data)
                        if payload.get("type") in {"PEERS", "PEER_JOINED"}:
                            return True, time.perf_counter() - t0
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            pass
        sleep_s = backoffs[min(attempt, len(backoffs) - 1)]
        attempt += 1
        await asyncio.sleep(sleep_s)


async def _one_cycle(url: str, room: str, peer_id: str, budget: float) -> tuple[bool, float]:
    # 한글 주석 — 1 cycle = warm-up JOIN + force close + reconnect 측정
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, timeout=5) as ws:
                await ws.send_json({"type": "JOIN", "room": room, "peer_id": peer_id})
                msg = await asyncio.wait_for(ws.receive(), timeout=3.0)
                if msg.type != aiohttp.WSMsgType.TEXT:
                    return False, 0.0
                payload = json.loads(msg.data)
                if payload.get("type") not in {"PEERS", "PEER_JOINED"}:
                    return False, 0.0
                await ws.close()
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return False, 0.0
    return await _attempt_reconnect(url, room, peer_id, budget)


def _report(results: list[tuple[bool, float]], budget: float) -> int:
    # 한글 주석 — success rate + 평균 reconnect 시간 출력 + NFR-04 게이트 (≥ 99%)
    total = len(results)
    successes = [r for r in results if r[0]]
    success_count = len(successes)
    rate = (success_count / total * 100.0) if total else 0.0
    elapsed_list = [r[1] for r in successes]
    avg = statistics.mean(elapsed_list) if elapsed_list else 0.0
    p95 = statistics.quantiles(elapsed_list, n=20)[18] if len(elapsed_list) >= 20 else (max(elapsed_list) if elapsed_list else 0.0)
    print(f"chaos cycle 완료 — {total} 회")
    print(f"  성공 = {success_count} / {total}")
    print(f"  성공률 = {rate:.2f}% (게이트 ≥ 99%)")
    print(f"  reconnect 평균 = {avg:.3f} s (budget {budget:.0f}s)")
    print(f"  reconnect 95p  = {p95:.3f} s")
    gate = rate >= 99.0
    print(f"\nNFR-04 게이트:")
    print(f"  >= 99% = {'PASS' if gate else 'FAIL'}")
    return 0 if gate else 2


async def _run(url: str, room: str, iterations: int, budget: float) -> int:
    results: list[tuple[bool, float]] = []
    for i in range(iterations):
        peer_id = f"chaos-bench-{i}"
        ok, elapsed = await _one_cycle(url, room, peer_id, budget)
        print(f"  [{i+1}/{iterations}] {'OK' if ok else 'FAIL'} ({elapsed:.3f}s)")
        results.append((ok, elapsed))
    return _report(results, budget)


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-04 시그널링 재연결 chaos bench")
    parser.add_argument("--url", default="ws://localhost:8765/ws", help="signaling URL")
    parser.add_argument("--iter", type=int, default=10, help="cycle 횟수 (기본 10)")
    parser.add_argument("--budget", type=float, default=30.0, help="reconnect budget seconds (기본 30)")
    parser.add_argument("--room", default="chaos-bench-room", help="room_id")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.url, args.room, args.iter, args.budget))
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"연결 실패: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
