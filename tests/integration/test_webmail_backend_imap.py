# SPDX-License-Identifier: GPL-3.0-or-later
"""server_webmail backend e2e — cycle 169.861 M4 IMAP 결선.

본 test 의 커버 영역:

- aiohttp Application build (route 등록 정합 — /healthz/login/inbox/mail/logout)
- /healthz 200 + JSON status=ok cycle=169.861 stage=M4-imap-integrated
- /로 GET 세션 부재 시 /login 302
- /login GET 200 HTML 로그인 폼
- /login POST IMAP 실패 시 401 + 폼 재표시
- /login POST IMAP 성공 시(mock) 세션 저장 + /inbox 302
- /inbox 세션 부재 시 /login 302
- /inbox 세션 정합 시 IMAP list_inbox call + HTML render
- /mail/<uid> 세션 정합 시 IMAP fetch_body call + HTML render
- /logout 세션 invalidate + /login 302
- imap_service unit — IMAPError 분기

실 IMAP 서버 = mail.dopa.co.kr:993, mocked 처리.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from server_webmail import imap_service
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
    """build_app() 안 route 7개 등록 — /healthz + / + /login GET/POST + /logout + /inbox + /mail/<uid>."""

    app = build_app()
    routes = [
        (route.method, route.resource.canonical)
        for route in app.router.routes()
    ]
    assert ("GET", "/healthz") in routes
    assert ("GET", "/") in routes
    assert ("GET", "/login") in routes
    assert ("POST", "/login") in routes
    assert ("POST", "/logout") in routes
    assert ("GET", "/inbox") in routes
    assert ("GET", "/mail/{uid}") in routes


# ----------------------------------------------------------------------
# Test 2: /healthz
# ----------------------------------------------------------------------


async def test_healthz_returns_ok(client: TestClient) -> None:
    """/healthz GET → 200 + JSON status=ok cycle=169.861 stage=M4-imap-integrated."""

    resp = await client.get("/healthz")
    assert resp.status == 200
    body = await resp.json()
    assert body["status"] == "ok"
    assert body["cycle"] == "169.861"
    assert body["stage"] == "M4-imap-integrated"


# ----------------------------------------------------------------------
# Test 3: / 루트 세션 부재 → /login
# ----------------------------------------------------------------------


async def test_root_no_session_redirects_to_login(client: TestClient) -> None:
    """/ GET 세션 부재 → 302 + Location: /login."""

    resp = await client.get("/", allow_redirects=False)
    assert resp.status == 302
    assert resp.headers["Location"] == "/login"


# ----------------------------------------------------------------------
# Test 4: /login GET → 폼 HTML
# ----------------------------------------------------------------------


async def test_login_get_returns_html(client: TestClient) -> None:
    """/login GET → 200 + text/html 로그인 폼."""

    resp = await client.get("/login")
    assert resp.status == 200
    assert resp.content_type == "text/html"
    body = await resp.text()
    assert 'method="POST"' in body
    assert 'name="user"' in body
    assert 'name="password"' in body
    assert "TooTalk 웹메일" in body


# ----------------------------------------------------------------------
# Test 5: /login POST IMAP 실패 → 401 + 폼 재표시
# ----------------------------------------------------------------------


async def test_login_post_imap_fail_returns_401(client: TestClient) -> None:
    """/login POST IMAP LOGIN 실패 시 401 + 폼 재표시."""

    # 한글 주석: imap_service.connect_and_login mock — IMAPError raise
    with patch(
        "server_webmail.main.imap_service.connect_and_login",
        side_effect=imap_service.IMAPError("test IMAP LOGIN FAIL"),
    ):
        resp = await client.post(
            "/login",
            data={"user": "test", "password": "wrong"},
            allow_redirects=False,
        )
    assert resp.status == 401
    body = await resp.text()
    assert "로그인 실패" in body


# ----------------------------------------------------------------------
# Test 6: /login POST IMAP 성공 → 세션 저장 + /inbox 302
# ----------------------------------------------------------------------


async def test_login_post_imap_ok_redirects_inbox(client: TestClient) -> None:
    """/login POST IMAP LOGIN 성공 시 세션 저장 + /inbox 302."""

    # 한글 주석: imap_service.connect_and_login mock — Mock IMAP4_SSL 반환
    class _MockIMAP:
        def logout(self):
            return ("BYE", [b"LOGOUT received"])

    with patch(
        "server_webmail.main.imap_service.connect_and_login",
        return_value=_MockIMAP(),
    ):
        resp = await client.post(
            "/login",
            data={"user": "test", "password": "ok"},
            allow_redirects=False,
        )
    assert resp.status == 302
    assert resp.headers["Location"] == "/inbox"


# ----------------------------------------------------------------------
# Test 7: /inbox 세션 부재 → /login 302
# ----------------------------------------------------------------------


async def test_inbox_no_session_redirects_login(client: TestClient) -> None:
    """/inbox 세션 부재 시 /login 302."""

    resp = await client.get("/inbox", allow_redirects=False)
    assert resp.status == 302
    assert resp.headers["Location"] == "/login"


# ----------------------------------------------------------------------
# Test 8: /inbox 세션 정합 + IMAP mock → HTML render
# ----------------------------------------------------------------------


async def test_inbox_with_session_renders_html(client: TestClient) -> None:
    """/login 성공 → /inbox GET → IMAP list_inbox mock 호출 + HTML render."""

    class _MockIMAP:
        def logout(self):
            return ("BYE", [b"BYE"])

    fake_summaries = [
        imap_service.MailSummary(
            uid=1, from_addr="alice@example.com", subject="Hello", date="2026-06-09"
        ),
        imap_service.MailSummary(
            uid=2, from_addr="bob@example.com", subject="World", date="2026-06-09"
        ),
    ]
    with patch(
        "server_webmail.main.imap_service.connect_and_login",
        return_value=_MockIMAP(),
    ):
        await client.post(
            "/login",
            data={"user": "test", "password": "ok"},
            allow_redirects=False,
        )
    with patch(
        "server_webmail.main.imap_service.list_inbox",
        return_value=fake_summaries,
    ):
        resp = await client.get("/inbox")
    assert resp.status == 200
    body = await resp.text()
    assert "INBOX" in body
    assert "Hello" in body
    assert "alice@example.com" in body


# ----------------------------------------------------------------------
# Test 9: /mail/<uid> 세션 정합 + IMAP mock → HTML render
# ----------------------------------------------------------------------


async def test_mail_get_with_session_renders_body(client: TestClient) -> None:
    """/mail/<uid> GET → IMAP fetch_body mock 호출 + HTML render."""

    class _MockIMAP:
        def logout(self):
            return ("BYE", [b"BYE"])

    fake_body = imap_service.MailBody(
        from_addr="alice@example.com",
        to_addr="test@dopa.co.kr",
        subject="Hello",
        date="2026-06-09",
        body_text="loopback body content",
    )
    with patch(
        "server_webmail.main.imap_service.connect_and_login",
        return_value=_MockIMAP(),
    ):
        await client.post(
            "/login",
            data={"user": "test", "password": "ok"},
            allow_redirects=False,
        )
    with patch(
        "server_webmail.main.imap_service.fetch_body",
        return_value=fake_body,
    ):
        resp = await client.get("/mail/42")
    assert resp.status == 200
    body = await resp.text()
    assert "loopback body content" in body
    assert "Hello" in body


# ----------------------------------------------------------------------
# Test 10: /logout 세션 invalidate + /login 302
# ----------------------------------------------------------------------


async def test_logout_invalidates_and_redirects(client: TestClient) -> None:
    """/logout POST → 302 + Location: /login + 세션 invalidate."""

    class _MockIMAP:
        def logout(self):
            return ("BYE", [b"BYE"])

    with patch(
        "server_webmail.main.imap_service.connect_and_login",
        return_value=_MockIMAP(),
    ):
        await client.post(
            "/login",
            data={"user": "test", "password": "ok"},
            allow_redirects=False,
        )
    resp = await client.post("/logout", allow_redirects=False)
    assert resp.status == 302
    assert resp.headers["Location"] == "/login"
    # 한글 주석: 후속 /inbox 접근 시 세션 부재 → /login redirect 정합
    resp2 = await client.get("/inbox", allow_redirects=False)
    assert resp2.status == 302
    assert resp2.headers["Location"] == "/login"


# ----------------------------------------------------------------------
# Test 11: imap_service IMAPError 분기 (connect_and_login fail path)
# ----------------------------------------------------------------------


def test_imap_service_connect_raises_on_ssl_error() -> None:
    """imap_service.connect_and_login 안 IMAP4_SSL constructor 실패 → IMAPError."""

    with patch("server_webmail.imap_service.imaplib.IMAP4_SSL") as mock_ssl:
        mock_ssl.side_effect = OSError("test connection refused")
        with pytest.raises(imap_service.IMAPError, match="IMAP 연결 실패"):
            imap_service.connect_and_login("nonexistent.test", 993, "u", "p")


# ----------------------------------------------------------------------
# Test 12: MIME encoded-word header 디코드 (cycle 169.862 회수)
# ----------------------------------------------------------------------


def test_decode_header_utf8_encoded_word() -> None:
    """`=?UTF-8?B?...?=` MIME encoded-word → 사람 가독 문자열."""

    # 한글 주석: 동적 인코드 (base64 hardcode 회피 — 한글 character 정합 검증)
    import base64
    payload = base64.b64encode("황원표".encode("utf-8")).decode("ascii")
    raw = f"=?UTF-8?B?{payload}?= <user@example.com>"
    decoded = imap_service._decode_header_value(raw)
    assert "황원표" in decoded
    assert "<user@example.com>" in decoded


# ----------------------------------------------------------------------
# Test 13: HTML body → plaintext (cycle 169.862 회수)
# ----------------------------------------------------------------------


def test_html_to_plaintext_strips_tags_and_unescapes() -> None:
    """HTML body → entity unescape + tag strip 정합 (XSS 우려, M6 안 bleach)."""

    html_src = (
        "<p>안녕하세요&nbsp;홍원표&nbsp;이사입니다.</p>"
        "<div>&copy; 2026</div>"
        "<script>alert('xss')</script>"
    )
    text = imap_service._html_to_plaintext(html_src)
    assert "안녕하세요" in text
    assert "홍원표" in text
    # 한글 주석: &copy; → © (html.parser convert_charrefs=True)
    assert "©" in text
    # 한글 주석: script tag 안 본문 제외 정합 (XSS 차단)
    assert "alert" not in text


# ----------------------------------------------------------------------
# Test 14: _parse_header_fields 정합 (FROM/SUBJECT/DATE)
# ----------------------------------------------------------------------


def test_parse_header_fields_extracts_from_subject_date() -> None:
    """_parse_header_fields 안 BODY[HEADER.FIELDS] payload → MailSummary 정합."""

    header_bytes = (
        b"From: hongwon <user@example.com>\r\n"
        b"Subject: test\r\n"
        b"Date: Tue, 09 Jun 2026 16:38:51 +0900\r\n"
        b"\r\n"
    )
    fetch_data = [(b"123 (BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {N}", header_bytes), b")"]
    summary = imap_service._parse_header_fields(123, fetch_data)
    assert summary is not None
    assert summary.uid == 123
    assert summary.subject == "test"
    assert "Tue, 09 Jun 2026" in summary.date
    assert "user@example.com" in summary.from_addr
