# SPDX-License-Identifier: GPL-3.0-or-later
"""server_webmail backend skeleton e2e — cycle 169.859 M3.

본 test 의 커버 영역:

- aiohttp Application build (route 등록 정합)
- /healthz endpoint 200 + JSON status
- / 루트 → /login 302 redirect
- /login GET → 200 HTML (로그인 폼)
- /login POST → 503 (M4 후속 cycle 결선 대기)

실 IMAP/SMTP 통합 = M4 후속 cycle 169.860+.
"""

from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from server_webmail.main import build_app


@pytest.fixture
async def client() -> TestClient:
    """aiohttp TestClient — 본 cycle skeleton 검증용."""

    app = build_app()
    server = TestServer(app)
    async with TestClient(server) as cli:
        yield cli


# ----------------------------------------------------------------------
# Test 1: route 등록 정합
# ----------------------------------------------------------------------


async def test_build_app_routes_registered() -> None:
    """build_app() 안 route 4개 등록 — /healthz GET + / GET + /login GET/POST."""

    app = build_app()
    routes = [
        (route.method, route.resource.canonical)
        for route in app.router.routes()
    ]
    assert ("GET", "/healthz") in routes
    assert ("GET", "/") in routes
    assert ("GET", "/login") in routes
    assert ("POST", "/login") in routes


# ----------------------------------------------------------------------
# Test 2: /healthz
# ----------------------------------------------------------------------


async def test_healthz_returns_ok(client: TestClient) -> None:
    """/healthz GET → 200 + JSON status=ok."""

    resp = await client.get("/healthz")
    assert resp.status == 200
    body = await resp.json()
    assert body["status"] == "ok"
    assert body["cycle"] == "169.859"
    assert body["stage"] == "skeleton"


# ----------------------------------------------------------------------
# Test 3: / 루트 → /login redirect
# ----------------------------------------------------------------------


async def test_root_redirects_to_login(client: TestClient) -> None:
    """/ GET → 302 + Location: /login."""

    resp = await client.get("/", allow_redirects=False)
    assert resp.status == 302
    assert resp.headers["Location"] == "/login"


# ----------------------------------------------------------------------
# Test 4: /login GET → HTML
# ----------------------------------------------------------------------


async def test_login_get_returns_html(client: TestClient) -> None:
    """/login GET → 200 + text/html 로그인 폼."""

    resp = await client.get("/login")
    assert resp.status == 200
    assert resp.content_type == "text/html"
    body = await resp.text()
    # 한글 주석: 로그인 폼 필수 요소 — POST action + user/password input + 한글 안내
    assert 'method="POST"' in body or 'method="post"' in body
    assert 'name="user"' in body
    assert 'name="password"' in body
    assert "TooTalk 웹메일" in body


# ----------------------------------------------------------------------
# Test 5: /login POST → 503 (M4 후속 cycle placeholder)
# ----------------------------------------------------------------------


async def test_login_post_returns_503_placeholder(client: TestClient) -> None:
    """/login POST → 503 (M4 후속 cycle IMAP 결선 대기 placeholder)."""

    resp = await client.post(
        "/login", data={"user": "verify", "password": "test"}
    )
    assert resp.status == 503
    body = await resp.text()
    assert "M4" in body or "결선" in body
