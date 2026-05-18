# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 auth REST API client — 회원가입 + OTP + 로그인 + 비번 재설정.

aiohttp + qasync 정합 — UI dialog 단 호출 시 GUI freeze 없음.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuthResult:
    """auth 응답 통합 dataclass."""

    ok: bool
    user_id: Optional[int] = None
    token: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    next_step: Optional[str] = None


class AuthClient:
    """REST endpoint wrapper.

    Parameters
    ----------
    base_url : str
        서버 base URL (예: `http://114.207.112.73:8765`).
    session : aiohttp.ClientSession | None
        외부 주입 가능 — None 이면 인스턴스 내부 생성.
    """

    def __init__(self, base_url: str, session: Optional[aiohttp.ClientSession] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._owns_session = session is None

    async def close(self) -> None:
        """내부 ClientSession close."""

        if self._owns_session and self._session is not None:
            await self._session.close()

    async def _post(self, path: str, payload: dict) -> AuthResult:
        """JSON POST + 응답 파싱 + AuthResult 변환."""

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

        url = f"{self._base_url}{path}"
        try:
            async with self._session.post(url, json=payload) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    return AuthResult(
                        ok=False,
                        error_code=data.get("error", "HTTP_ERROR"),
                        error_message=data.get("message", f"HTTP {resp.status}"),
                    )
                return AuthResult(
                    ok=bool(data.get("ok")),
                    user_id=data.get("user_id"),
                    token=data.get("token"),
                    next_step=data.get("next"),
                )
        except aiohttp.ClientError as exc:
            log.error("[auth_client] network err url=%s err=%r", url, exc)
            return AuthResult(
                ok=False,
                error_code="NETWORK",
                error_message=f"네트워크 오류: {exc}",
            )

    async def register(self, email: str, username: str, password: str) -> AuthResult:
        return await self._post(
            "/api/auth/register",
            {"email": email, "username": username, "password": password},
        )

    async def verify_otp(self, email: str, code: str) -> AuthResult:
        return await self._post(
            "/api/auth/verify",
            {"email": email, "code": code},
        )

    async def login(self, email: str, password: str) -> AuthResult:
        return await self._post(
            "/api/auth/login",
            {"email": email, "password": password},
        )

    async def request_reset(self, email: str) -> AuthResult:
        return await self._post(
            "/api/auth/reset/request",
            {"email": email},
        )

    async def consume_reset(self, email: str, code: str, new_password: str) -> AuthResult:
        return await self._post(
            "/api/auth/reset/consume",
            {"email": email, "code": code, "new_password": new_password},
        )
