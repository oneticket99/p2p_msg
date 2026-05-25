# SPDX-License-Identifier: GPL-3.0-or-later
"""SignalingClient 실 aiohttp WS server chaos 재연결 통합 test — cycle 169.788 (NFR-04).

Codex 전면평가 P1 — "실 서버 강제 close 기반 e2e chaos 필요, NFR-04 VERIFIED 아님" 회수.
기존 `test_signaling_reconnect.py` 는 `_connect_once`/`asyncio.sleep` 를 mock 으로 격리한
FSM 단위 검증이었다. 본 test 는 **실 aiohttp WebSocket server** 를 동적 port 에 띄우고,
1회차 연결 수락 후 server 가 WS 를 강제 close → SignalingClient 가:

1. 비정상 drop 감지 → RECONNECTING 상태 전이
2. backoff 재연결 → 2회차 연결 성공 → CONNECTED
3. 마지막 JOIN 식별자로 reJOIN (2회차 server 가 JOIN 재수신)

를 실 WS 왕복으로 검증한다. StatusBar ERROR 미오표시(RECONNECTING 정상 경로) 정합.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from aiohttp import WSMsgType, web

from app.core.app_state import AppState
from app.net.signaling_client import SignalingClient

pytestmark = pytest.mark.integration


class _ChaosServer:
    """1회차 연결을 강제 close, 2회차 연결의 JOIN 을 기록하는 chaos WS server."""

    def __init__(self) -> None:
        self.connections = 0
        self.rejoined = asyncio.Event()
        self.rejoin_payload: dict | None = None
        self.runner: web.AppRunner | None = None
        self.port = 0

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.connections += 1
        conn_idx = self.connections
        if conn_idx == 1:
            # 1회차 — 첫 메시지(JOIN) 수신 후 강제 close (chaos drop 모사)
            try:
                await asyncio.wait_for(ws.receive(), timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                pass
            await ws.close(code=1011)  # 비정상 종료 코드
            return ws
        # 2회차 — reJOIN 수신 기록
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except Exception:
                    continue
                if payload.get("type") == "JOIN":
                    self.rejoin_payload = payload
                    self.rejoined.set()
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                break
        return ws

    async def start(self) -> str:
        app = web.Application()
        app.router.add_get("/ws", self._ws_handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        # 동적 port 추출
        self.port = list(self.runner.addresses)[0][1]
        return f"ws://127.0.0.1:{self.port}/ws"

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()


class TestSignalingChaosReconnect:
    """실 WS server 강제 close → RECONNECTING → reconnect → reJOIN."""

    @pytest.mark.asyncio
    async def test_chaos_close_triggers_reconnect_rejoin(self) -> None:
        AppState.instance().reset() if hasattr(AppState.instance(), "reset") else None
        server = _ChaosServer()
        url = await server.start()
        client = SignalingClient(config=SimpleNamespace(signaling_url=url))
        client._reconnect_base_delay = 0.05  # backoff 즉시화
        client._reconnect_max_delay = 0.2

        states: list[str] = []
        client.connection_state_changed.connect(states.append)  # type: ignore[arg-type]

        try:
            await client.connect()
            await client.join("room-chaos", "peer-X")
            # server 1회차 close → client 재연결 + reJOIN 대기
            await asyncio.wait_for(server.rejoined.wait(), timeout=15.0)

            # reJOIN payload 가 마지막 JOIN 식별자 보존
            assert server.rejoin_payload is not None
            assert server.rejoin_payload.get("room") == "room-chaos"
            assert server.rejoin_payload.get("peer_id") == "peer-X"
            # 2회차 이상 연결 = 재연결 발생
            assert server.connections >= 2
            # RECONNECTING 상태가 emit 됨 (StatusBar 가 ERROR 아닌 RECONNECTING 표시)
            assert "RECONNECTING" in states
            assert "CONNECTED" in states
        finally:
            await client.disconnect()
            await server.stop()
