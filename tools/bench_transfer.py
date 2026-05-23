#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-02 — 100MB 파일 송신 throughput bench (LAN 기준).

목표: ≥ 30Mbps 평균 (CheckList.md NFR-02).

본 도구는 WebRTC DataChannel 직결 throughput 이 아니라 **signaling relay** 경유
binary chunk 송수신 throughput 만 측정한다. 실 DataChannel 은 aiortc + PyQt6
양 클라 활성 의무 → NFR-02 측정 인프라 의 1차 step.

측정 패턴:
1. 2 ws client 동일 room JOIN (sender + receiver)
2. sender → receiver chunk N 회 송신 (chunk_size 기본 64KB, 총 100MB)
3. receiver 의 전체 byte 수신 완료 시점 측정
4. throughput = total_bytes / elapsed_seconds (Mbps 변환)

사용:
    python tools/bench_transfer.py --url ws://localhost:8765/ws --size-mb 100
    python tools/bench_transfer.py --url ws://114.207.112.73:8765/ws --size-mb 10
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time

import aiohttp


async def _join(ws: aiohttp.ClientWebSocketResponse, room: str, peer_id: str) -> None:
    await ws.send_json({"type": "JOIN", "room": room, "peer_id": peer_id})
    msg = await ws.receive(timeout=5.0)
    if msg.type != aiohttp.WSMsgType.TEXT:
        raise RuntimeError(f"JOIN 응답 type 불일치: {msg.type}")
    payload = json.loads(msg.data)
    if payload.get("type") not in {"PEERS", "PEER_JOINED"}:
        raise RuntimeError(f"JOIN ERROR: {payload}")


async def _receiver_loop(
    ws: aiohttp.ClientWebSocketResponse,
    expected_chunks: int,
    on_first_chunk: asyncio.Event,
    on_complete: asyncio.Event,
    counter: dict[str, int],
) -> None:
    # 한글 주석 — receiver 의 chunk 수신 — sdp field 안 base64 payload 추출 + count + total_bytes 누적
    received = 0
    total_bytes = 0
    while received < expected_chunks:
        msg = await ws.receive(timeout=30.0)
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        payload = json.loads(msg.data)
        if payload.get("type") != "OFFER":
            continue
        chunk_b64 = payload.get("sdp", "")
        chunk_bytes = base64.b64decode(chunk_b64) if chunk_b64 else b""
        total_bytes += len(chunk_bytes)
        received += 1
        if received == 1:
            on_first_chunk.set()
    counter["received"] = received
    counter["total_bytes"] = total_bytes
    on_complete.set()


async def _sender_loop(
    ws: aiohttp.ClientWebSocketResponse,
    room: str,
    receiver_id: str,
    chunk_size: int,
    chunk_count: int,
) -> None:
    # 한글 주석 — sender 의 chunk 송신 — random binary chunk base64 encode → OFFER envelope 안 sdp field 안 stash
    payload_chunk = os.urandom(chunk_size)
    encoded = base64.b64encode(payload_chunk).decode("ascii")
    for i in range(chunk_count):
        await ws.send_json({
            "type": "OFFER",
            "room": room,
            "to": receiver_id,
            "sdp": encoded,
            "seq": i,
        })


def _report(elapsed: float, total_bytes: int, received: int, expected: int) -> int:
    # 한글 주석 — throughput 결과 출력 + NFR-02 게이트 (≥ 30Mbps)
    if received == 0:
        print("chunk 수신 0건 — fail", file=sys.stderr)
        return 1
    mbps = (total_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0.0
    mbits = total_bytes * 8 / 1_000_000
    print(f"송수신 완료 — {received} / {expected} chunk, {total_bytes:,} bytes")
    print(f"  elapsed = {elapsed:.3f} s")
    print(f"  total   = {mbits:.2f} Mbit")
    print(f"  throughput = {mbps:.2f} Mbps")
    gate = mbps >= 30.0
    print(f"\nNFR-02 게이트:")
    print(f"  >= 30 Mbps = {'PASS' if gate else 'FAIL'}")
    return 0 if gate else 2


async def _run(url: str, room: str, size_mb: int, chunk_kb: int) -> int:
    chunk_size = chunk_kb * 1024
    total_bytes_target = size_mb * 1024 * 1024
    chunk_count = (total_bytes_target + chunk_size - 1) // chunk_size
    # 한글 주석 — base64 encode 의 size 33% 증가 → effective payload + envelope JSON 오버헤드 고려
    print(f"chunk_size = {chunk_size:,} bytes · count = {chunk_count} · target = {size_mb} MB")
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, timeout=10, max_msg_size=0) as rx_ws, session.ws_connect(url, timeout=10, max_msg_size=0) as tx_ws:
            await _join(rx_ws, room, "rx-bench")
            await _join(tx_ws, room, "tx-bench")
            on_first = asyncio.Event()
            on_complete = asyncio.Event()
            counter: dict[str, int] = {"received": 0, "total_bytes": 0}
            rx_task = asyncio.create_task(_receiver_loop(rx_ws, chunk_count, on_first, on_complete, counter))
            t0 = time.perf_counter()
            await _sender_loop(tx_ws, room, "rx-bench", chunk_size, chunk_count)
            try:
                await asyncio.wait_for(on_complete.wait(), timeout=120.0)
            except asyncio.TimeoutError:
                pass
            elapsed = time.perf_counter() - t0
            rx_task.cancel()
            return _report(elapsed, counter["total_bytes"], counter["received"], chunk_count)


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-02 파일 throughput bench (signaling relay 경유)")
    parser.add_argument("--url", default="ws://localhost:8765/ws", help="signaling URL")
    parser.add_argument("--size-mb", type=int, default=10, help="총 송신 크기 MB (기본 10)")
    parser.add_argument("--chunk-kb", type=int, default=64, help="chunk 크기 KB (기본 64)")
    parser.add_argument("--room", default="bench-transfer-room", help="room_id")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.url, args.room, args.size_mb, args.chunk_kb))
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"연결 실패: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
