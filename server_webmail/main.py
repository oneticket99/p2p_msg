# SPDX-License-Identifier: GPL-3.0-or-later
"""webmail.dopa.co.kr aiohttp backend skeleton — cycle 169.859 M3.

본 모듈 = M3 skeleton 단계. /healthz + 로그인 placeholder 페이지만.
실 IMAP/SMTP 통합 = M4 후속 cycle 169.860+.

Exec Plan: docs/exec-plans/active/2026-06-09-webmail-python-backend.md
"""

from __future__ import annotations

import logging
import os

from aiohttp import web

# 한글 주석: KST timezone + JSON 로그 = server/ 정합 의무 (cycle 169.857 Dovecot 정합)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("webmail")

# 한글 주석: nginx upstream `webmail:8090` 정합 — 8090 listen
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("WEBMAIL_PORT", "8090"))

# 한글 주석: 로그인 placeholder HTML — M4 후속 cycle 안 Jinja2 template 으로 교체 예정
LOGIN_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TooTalk 웹메일 — dopa.co.kr</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo",
        "Malgun Gothic", sans-serif;
      background: #f3f4f6;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .card {
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
      padding: 40px 32px;
      width: 360px;
    }
    h1 { font-size: 22px; margin: 0 0 8px; color: #1f2937; }
    p  { font-size: 14px; color: #4b5563; margin: 0 0 24px; }
    label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; }
    input {
      width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px;
      font-size: 14px; box-sizing: border-box; margin-bottom: 16px;
    }
    button {
      width: 100%; padding: 12px; background: #2563eb; color: #ffffff; border: 0;
      border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
    }
    .notice { font-size: 12px; color: #9ca3af; margin-top: 16px; text-align: center; }
  </style>
</head>
<body>
  <form class="card" method="POST" action="/login">
    <h1>TooTalk 웹메일</h1>
    <p>dopa.co.kr 계정으로 로그인</p>
    <label for="user">사용자명</label>
    <input id="user" name="user" type="text" placeholder="예: verify"
      autocomplete="username" required>
    <label for="password">패스워드</label>
    <input id="password" name="password" type="password"
      autocomplete="current-password" required>
    <button type="submit">로그인</button>
    <p class="notice">
      cycle 169.859 skeleton — IMAP 결선은 M4 후속 cycle 169.860+
    </p>
  </form>
</body>
</html>
"""


async def handle_healthz(request: web.Request) -> web.Response:
    """nginx /healthz 정합 — docker compose healthcheck + 외부 모니터링."""

    # 한글 주석: M3 단계 = backend skeleton, IMAP/SMTP dependency 부재 정합
    return web.json_response({"status": "ok", "cycle": "169.859", "stage": "skeleton"})


async def handle_index(request: web.Request) -> web.Response:
    """루트 = 로그인 페이지 redirect."""

    return web.HTTPFound("/login")


async def handle_login_get(request: web.Request) -> web.Response:
    """로그인 GET — placeholder HTML 응답.

    실 IMAP 인증 = M4 후속 cycle (imaplib.IMAP4_SSL + 세션 저장).
    """

    return web.Response(text=LOGIN_HTML, content_type="text/html", charset="utf-8")


async def handle_login_post(request: web.Request) -> web.Response:
    """로그인 POST — 미구현 placeholder.

    M4 후속 cycle 안 IMAP4_SSL LOGIN + aiohttp_session 안 자격 보관.
    """

    # 한글 주석: M3 skeleton — 503 응답 + 안내 (M4 후속 cycle 결선 의무)
    return web.Response(
        status=503,
        text="IMAP 결선 부재 — M4 후속 cycle 169.860 에서 활성 예정",
        content_type="text/plain",
        charset="utf-8",
    )


def build_app() -> web.Application:
    """aiohttp Application 조립.

    route 등록 + middleware (M4 후속 cycle 안 aiohttp_session 추가 예정).
    """

    app = web.Application()
    app.router.add_get("/healthz", handle_healthz)
    app.router.add_get("/", handle_index)
    app.router.add_get("/login", handle_login_get)
    app.router.add_post("/login", handle_login_post)
    return app


def main() -> None:
    """entry point — uvicorn 부재 정합으로 aiohttp web.run_app 직접 사용."""

    log.info(
        "webmail skeleton listen %s:%s (cycle 169.859 M3, IMAP=M4 후속 cycle)",
        LISTEN_HOST,
        LISTEN_PORT,
    )
    app = build_app()
    web.run_app(app, host=LISTEN_HOST, port=LISTEN_PORT, access_log=log)


if __name__ == "__main__":
    main()
