#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-01 — WebSocket 시그널링 RTT bench (LAN 기준).

목표: 평균 RTT < 100ms · 95p < 200ms (CheckList.md NFR-01).

본 도구는 WebRTC DataChannel 직결 RTT 가 아니라 **시그널링 round-trip** 만 측정한다.
실 DataChannel RTT 는 PyQt6 + aiortc 의 실 binding 의존성 + 양 클라이언트 활성 필요 →
NFR-01 측정 인프라 의 1차 step.

측정 패턴:
1. 2 ws client 의 동일 room JOIN (alice + bob)
2. alice → bob 의 OFFER envelope N 회 round-trip
3. send_t0 → bob.recv → bob.send ANSWER → alice.recv = RTT
4. 평균/95p/min/max + jitter 출력

사용:
    python tools/bench_rtt.py --url ws://localhost:8765/ws --iter 100
    python tools/bench_rtt.py --url ws://114.207.112.73:8765/ws --iter 50

원격 demo 서버: ws://114.207.112.73:8765/ws (project_smtp_demo_server 참조).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from typing import Any

import aiohttp


async def _join(ws: aiohttp.ClientWebSocketResponse, room_id: str, peer_id: str) -> None:
    # 한글 주석 — JOIN envelope 송신 + PEERS 응답 1건 소비 (server protocol field = "room" + "peer_id")
    await ws.send_json({"type": "JOIN", "room": room_id, "peer_id": peer_id})
    msg = await ws.receive(timeout=5.0)
    if msg.type != aiohttp.WSMsgType.TEXT:
        raise RuntimeError(f"JOIN 응답 type 불일치: {msg.type}")
    payload = json.loads(msg.data)
    if payload.get("type") not in {"PEERS", "PEER_JOINED"}:
        raise RuntimeError(f"JOIN 응답 type 불일치: {payload.get('type')}")


async def _bob_echo_loop(ws: aiohttp.ClientWebSocketResponse, room_id: str, alice_id: str, stop: asyncio.Event) -> None:
    # 한글 주석 — bob 의 echo — OFFER 수신 직후 즉시 ANSWER 송신
    while not stop.is_set():
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        payload = json.loads(msg.data)
        if payload.get("type") == "OFFER":
            seq = payload.get("seq", 0)
            await ws.send_json({
                "type": "ANSWER",
                "room": room_id,
                "to": alice_id,
                "sdp": "",
                "seq": seq,
            })


async def _alice_measure(
    ws: aiohttp.ClientWebSocketResponse,
    room_id: str,
    bob_id: str,
    iterations: int,
) -> list[float]:
    # 한글 주석 — alice 의 RTT 측정 loop — OFFER 송신 직후 ANSWER 수신 시간 차
    rtts: list[float] = []
    for i in range(iterations):
        t0 = time.perf_counter()
        await ws.send_json({
            "type": "OFFER",
            "room": room_id,
            "to": bob_id,
            "sdp": "",
            "seq": i,
        })
        while True:
            msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            payload = json.loads(msg.data)
            if payload.get("type") == "ANSWER" and payload.get("seq") == i:
                rtt_ms = (time.perf_counter() - t0) * 1000.0
                rtts.append(rtt_ms)
                break
    return rtts


def _report(rtts: list[float], iterations: int) -> int:
    # 한글 주석 — 측정 결과 출력 + NFR-01 게이트 (평균 < 100ms + 95p < 200ms)
    if not rtts:
        print("RTT 측정 실패 — 0 sample", file=sys.stderr)
        return 1
    avg = statistics.mean(rtts)
    p95 = statistics.quantiles(rtts, n=20)[18] if len(rtts) >= 20 else max(rtts)
    minimum = min(rtts)
    maximum = max(rtts)
    jitter = statistics.stdev(rtts) if len(rtts) > 1 else 0.0
    print(f"RTT 측정 완료 — {len(rtts)} / {iterations} 샘플")
    print(f"  평균 = {avg:.2f} ms")
    print(f"  95p  = {p95:.2f} ms")
    print(f"  min  = {minimum:.2f} ms")
    print(f"  max  = {maximum:.2f} ms")
    print(f"  jitter (stdev) = {jitter:.2f} ms")
    gate_avg = avg < 100.0
    gate_p95 = p95 < 200.0
    print(f"\nNFR-01 게이트:")
    print(f"  평균 < 100ms = {'PASS' if gate_avg else 'FAIL'}")
    print(f"  95p  < 200ms = {'PASS' if gate_p95 else 'FAIL'}")
    return 0 if (gate_avg and gate_p95) else 2


async def _run(url: str, iterations: int, room_id: str) -> int:
    # 한글 주석 — main 진입점 — alice/bob 2 ws 동시 spawn + RTT 측정
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, timeout=10) as alice_ws, session.ws_connect(url, timeout=10) as bob_ws:
            await _join(bob_ws, room_id, "bob-bench")
            await _join(alice_ws, room_id, "alice-bench")
            stop = asyncio.Event()
            bob_task = asyncio.create_task(_bob_echo_loop(bob_ws, room_id, "alice-bench", stop))
            try:
                rtts = await _alice_measure(alice_ws, room_id, "bob-bench", iterations)
            finally:
                stop.set()
                await asyncio.wait_for(bob_task, timeout=2.0)
            return _report(rtts, iterations)


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-01 시그널링 RTT bench")
    parser.add_argument("--url", default="ws://localhost:8765/ws", help="signaling WebSocket URL")
    parser.add_argument("--iter", type=int, default=100, help="반복 횟수 (기본 100)")
    parser.add_argument("--room", default="bench-room", help="사용 room_id")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.url, args.iter, args.room))
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"연결 실패: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
