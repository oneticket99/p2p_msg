"""E2E 테스트 전용 픽스처 — Playwright 기반.

DESIGN.md §10.6 정합 — Playwright 측 다음 3 영역 적용:

1. **시그널링 서버 WebSocket E2E** — `aiohttp` 서버 측 브라우저 client 측 JOIN/OFFER/ANSWER 흐름 검증
2. **HTML 등가 시각 회귀** — `docs/html/` 6 HTML 측 screenshot 비교 (`page.screenshot()`)
3. **GitHub Release zip 첫 실행 캡처** — Phase 2+ 측 (PyInstaller zip 다운 + 첫 화면 capture)

PyQt6 데스크탑 위젯 직접 자동화 = Playwright 영역 외 (`pytest-qt` 측 `QTest` 사용).

사용자 directive 2026-05-17 — "qa 단계에 반드시 playwright 를 이용한 테스트도 명시해".
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def signaling_server_url() -> str:
    """시그널링 서버 E2E 측 기본 URL.

    실 배포 시 환경변수 ``E2E_SIGNALING_URL`` 측 override 가능.
    Phase 1 = `ws://127.0.0.1:8765/ws` (로컬 실행 가정).
    Phase 2+ = 데모 서버 `wss://signal.tootalk.example/ws` (TLS 도입 후).
    """

    import os
    return os.environ.get("E2E_SIGNALING_URL", "ws://127.0.0.1:8765/ws")


@pytest.fixture(scope="session")
def html_docs_base() -> str:
    """HTML 등가 문서 측 file:// base URL.

    `docs/html/` 6 HTML (Structure/ARCHITECTURE/FRONTEND/DESIGN/productization/vibe-coding)
    측 시각 회귀 검증 base.
    """

    from pathlib import Path
    docs_html = Path(__file__).resolve().parent.parent.parent / "docs" / "html"
    return f"file://{docs_html}"
