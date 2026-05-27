# SPDX-License-Identifier: GPL-3.0-or-later
"""E2E 테스트 전용 픽스처 — Playwright 기반.

테스트 전략 — Playwright 브라우저 자동화 픽스처 제공(이벤트 루프·시그널링 서버·page context).
PyQt6 위젯 자동화는 본 영역 외(pytest-qt QTest). 본 conftest 는 e2e 디렉토리 공용 fixture 정의.

DESIGN.md §10.6 정합 — Playwright 의 다음 3 영역 적용:

1. **시그널링 서버 WebSocket E2E** — `aiohttp` 서버 의 브라우저 client 의 JOIN/OFFER/ANSWER 흐름 검증
2. **HTML 등가 시각 회귀** — `docs/html/` 6 HTML 의 screenshot 비교 (`page.screenshot()`)
3. **GitHub Release zip 첫 실행 캡처** — Phase 2+ 의 (PyInstaller zip 다운 + 첫 화면 capture)

PyQt6 데스크탑 위젯 직접 자동화 = Playwright 영역 외 (`pytest-qt` 의 `QTest` 사용).

사용자 directive 2026-05-17 — "qa 단계에 반드시 playwright 를 이용한 테스트도 명시해".
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def signaling_server_url() -> str:
    """시그널링 서버 E2E 의 기본 URL.

    실 배포 시 환경변수 ``E2E_SIGNALING_URL`` 의 override 가능.
    기본값 = 원격 테스트 서버 `ws://114.207.112.73:8765/ws`.
    로컬 임시 서버 검증은 ``live_signaling_server_url`` fixture 를 별도로 사용한다.
    """

    import os
    return os.environ.get("E2E_SIGNALING_URL", "ws://114.207.112.73:8765/ws")


@pytest.fixture(scope="session")
def live_signaling_server_url() -> Generator[str, None, None]:
    """브라우저 WebSocket E2E 전용 live aiohttp signaling server.

    Playwright page 안의 native WebSocket 이 실제 ``server.signaling`` router 를
    통과하도록 임시 loop thread + ephemeral port 로 서버를 띄운다.
    """

    from aiohttp import web
    from server.room import RoomRegistry
    from server.signaling import build_routes

    ready: "queue.Queue[tuple[str | None, BaseException | None]]" = queue.Queue(maxsize=1)
    state: dict[str, Any] = {}

    def _run_server() -> None:
        """별도 thread 안에서 aiohttp app lifecycle 을 소유한다."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner: web.AppRunner | None = None
        state["loop"] = loop

        async def _start() -> tuple[web.AppRunner, str]:
            app = web.Application()
            build_routes(app, RoomRegistry())
            app_runner = web.AppRunner(app)
            await app_runner.setup()
            site = web.TCPSite(app_runner, "127.0.0.1", 0)
            await site.start()
            # port=0 으로 OS 가 배정한 실제 포트를 읽어 Playwright 에 전달한다.
            sockets = site._server.sockets if site._server is not None else []  # type: ignore[attr-defined]
            if not sockets:
                raise RuntimeError("E2E signaling server socket 생성 실패")
            port = int(sockets[0].getsockname()[1])
            return app_runner, f"ws://127.0.0.1:{port}/ws"

        try:
            runner, url = loop.run_until_complete(_start())
            ready.put((url, None))
            loop.run_forever()
        except BaseException as exc:  # noqa: BLE001
            ready.put((None, exc))
        finally:
            if runner is not None:
                loop.run_until_complete(runner.cleanup())
            loop.close()

    thread = threading.Thread(
        target=_run_server,
        name="tootalk-e2e-signaling",
        daemon=True,
    )
    thread.start()

    url, exc = ready.get(timeout=5.0)
    if exc is not None:
        if isinstance(exc, PermissionError):
            pytest.skip(f"E2E signaling server 포트 바인딩 권한 부재 — {exc}")
        raise RuntimeError("E2E signaling server 기동 실패") from exc
    if url is None:
        raise RuntimeError("E2E signaling server URL 부재")

    yield url

    loop = state.get("loop")
    if loop is not None:
        loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5.0)


@pytest.fixture(scope="session")
def html_docs_base() -> str:
    """HTML 등가 문서 의 file:// base URL.

    `docs/html/` 6 HTML (Structure/ARCHITECTURE/FRONTEND/DESIGN/productization/vibe-coding)
    의 시각 회귀 검증 base.
    """

    from pathlib import Path
    docs_html = Path(__file__).resolve().parent.parent.parent / "docs" / "html"
    return f"file://{docs_html}"
