#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""NFR-02 — WebRTC DataChannel 직결 throughput bench (LAN 기준).

목표: ≥ 30Mbps 평균 (CheckList.md NFR-02).

cycle 169.593 의 signaling relay bench (tools/bench_transfer.py) = 22 Mbps —
relay overhead 제약. 본 도구 = **aiortc 양 peer 의 동일 프로세스 안 DataChannel
직결** 측정. signaling 부재 — SDP offer/answer 의 in-process pipe.

aiortc 양 peer + DataChannel + send chunk N + 수신 누적 + Mbps 환산.

사용:
    python tools/bench_datachannel.py --size-mb 100 --chunk-kb 16
    python tools/bench_datachannel.py --size-mb 10 --chunk-kb 64
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    _AIORTC = True
except ImportError:
    _AIORTC = False


async def _run(size_mb: int, chunk_kb: int) -> int:
    # 한글 주석 — aiortc 양 peer in-process + DataChannel offer/answer in-memory SDP exchange
    if not _AIORTC:
        print("aiortc 미설치 — `pip install aiortc` 의무", file=sys.stderr)
        return 3
    chunk_size = chunk_kb * 1024
    total_target = size_mb * 1024 * 1024
    chunk_count = (total_target + chunk_size - 1) // chunk_size
    print(f"chunk_size = {chunk_size:,} bytes · count = {chunk_count} · target = {size_mb} MB")

    pc1 = RTCPeerConnection()
    pc2 = RTCPeerConnection()
    received_bytes = 0
    received_count = 0
    done = asyncio.Event()
    t_first: float | None = None
    payload = os.urandom(chunk_size)

    @pc2.on("datachannel")
    def _on_dc(channel):
        # 한글 주석 — pc2 의 수신 channel — chunk 수신 count + total_bytes 누적
        @channel.on("message")
        def _on_msg(msg):
            nonlocal received_bytes, received_count, t_first
            if isinstance(msg, (bytes, bytearray)):
                received_bytes += len(msg)
            received_count += 1
            if t_first is None:
                t_first = time.perf_counter()
            if received_count >= chunk_count:
                done.set()

    dc1 = pc1.createDataChannel("bench")
    open_event = asyncio.Event()

    @dc1.on("open")
    def _on_open():
        open_event.set()

    # 한글 주석 — SDP offer/answer in-process exchange
    offer = await pc1.createOffer()
    await pc1.setLocalDescription(offer)
    await pc2.setRemoteDescription(pc1.localDescription)
    answer = await pc2.createAnswer()
    await pc2.setLocalDescription(answer)
    await pc1.setRemoteDescription(pc2.localDescription)

    try:
        await asyncio.wait_for(open_event.wait(), timeout=10.0)
    except asyncio.TimeoutError:
        print("DataChannel open timeout", file=sys.stderr)
        await pc1.close()
        await pc2.close()
        return 1

    t0 = time.perf_counter()
    for _ in range(chunk_count):
        dc1.send(payload)
        # 한글 주석 — buffered amount 안 too-high 회피 — pause + drain
        if dc1.bufferedAmount > 16 * 1024 * 1024:
            while dc1.bufferedAmount > 4 * 1024 * 1024:
                await asyncio.sleep(0.01)
    try:
        await asyncio.wait_for(done.wait(), timeout=120.0)
    except asyncio.TimeoutError:
        pass
    elapsed = time.perf_counter() - t0
    await pc1.close()
    await pc2.close()

    if received_bytes == 0:
        print("chunk 수신 0건 — fail", file=sys.stderr)
        return 1
    mbps = (received_bytes * 8) / (elapsed * 1_000_000)
    mbits = received_bytes * 8 / 1_000_000
    print(f"송수신 완료 — {received_count} / {chunk_count} chunk, {received_bytes:,} bytes")
    print(f"  elapsed = {elapsed:.3f} s")
    print(f"  total   = {mbits:.2f} Mbit")
    print(f"  throughput = {mbps:.2f} Mbps")
    gate = mbps >= 30.0
    print(f"\nNFR-02 게이트:")
    print(f"  >= 30 Mbps = {'PASS' if gate else 'FAIL'}")
    return 0 if gate else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="NFR-02 DataChannel 직결 throughput bench")
    parser.add_argument("--size-mb", type=int, default=10, help="총 송신 크기 MB (기본 10)")
    parser.add_argument("--chunk-kb", type=int, default=16, help="chunk 크기 KB (기본 16, DataChannel 권장 max 16KB)")
    args = parser.parse_args()
    return asyncio.run(_run(args.size_mb, args.chunk_kb))


if __name__ == "__main__":
    sys.exit(main())
