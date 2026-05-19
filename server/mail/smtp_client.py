# SPDX-License-Identifier: GPL-3.0-or-later
"""aiosmtplib 기반 비동기 SMTP client — Phase 1 이메일 OTP 발송.

[[project-smtp-demo-server]] 정합 — mail.dopa.co.kr (114.207.112.73) postfix 설치 완료.
사이클 129 SMTP 자동 설치 chain 결과 — listen 25/465/587/8891 PASS.

설정 우선순위
-------------
1. server.config.SMTPConfig.from_env() — .env → .env.<ENV> → .env.smtp override chain.
2. 직접 os.environ 접근 = SMTPConfig 미로드 환경 전용 fallback.

TLS 모드
--------
- STARTTLS (port 587): connect → EHLO → STARTTLS → auth LOGIN
- SMTPS   (port 465): connect_tls → EHLO → auth LOGIN

retry/backoff
-------------
- 3회 시도 + 지수 백오프 (1s → 2s → 4s) — 호출자 try/except 비차단.
"""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
from email.message import EmailMessage
from typing import Optional

log = logging.getLogger(__name__)

try:
    import aiosmtplib
except ImportError:  # pragma: no cover - 의존성 미설치 환경
    aiosmtplib = None  # type: ignore[assignment]

# retry 설정 — 3회 시도, 지수 백오프 (1s → 2s → 4s)
_RETRY_COUNT = 3
_RETRY_BASE_SECONDS = 1.0


def _env_str(key: str, default: str) -> str:
    """환경변수 문자열 — 빈값 폴백."""

    raw = os.environ.get(key, "").strip()
    return raw if raw else default


def _env_int(key: str, default: int) -> int:
    """환경변수 정수 폴백."""

    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_from_address() -> str:
    """SMTP 발송 주소 결정 — 환경변수 키 alias 처리."""

    # SMTP_FROM_ADDRESS (신키) → SMTP_FROM (.env.smtp 구키) 순서 fallback
    addr = os.environ.get("SMTP_FROM_ADDRESS", "").strip()
    if not addr:
        addr = os.environ.get("SMTP_FROM", "").strip()
    return addr or "noreply@dopa.co.kr"


def _resolve_smtp_params() -> tuple[str, int, str, str, str]:
    """환경변수 → SMTP 연결 파라미터 추출.

    Returns
    -------
    tuple
        (host, port, user, password, tls_mode)
    """

    host = _env_str("SMTP_HOST", "mail.dopa.co.kr")
    port = _env_int("SMTP_PORT", 587)
    user = os.environ.get("SMTP_USER", "").strip()
    # SMTP_PASSWORD (신키) → SMTP_PASS (.env.smtp 구키) 순서 fallback
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if not password:
        password = os.environ.get("SMTP_PASS", "").strip()
    tls_mode = os.environ.get("SMTP_TLS", "STARTTLS").strip().upper()
    return host, port, user, password, tls_mode


def build_otp_email(
    *,
    to_email: str,
    code: str,
    purpose: str,
    from_email: Optional[str] = None,
) -> EmailMessage:
    """OTP 발송용 EmailMessage 생성.

    Parameters
    ----------
    to_email : str
        수신자.
    code : str
        OTP 평문 6자리 (app.core.security.generate_otp_code 산출).
    purpose : str
        'signup' 또는 'password_reset' — subject 분기.
    from_email : str | None
        발송 주소. None 이면 _resolve_from_address default.

    Returns
    -------
    EmailMessage
        UTF-8 한글 본문 + Subject + headers 정합.
    """

    sender = from_email or _resolve_from_address()

    if purpose == "signup":
        subject = "[TooTalk] 회원가입 인증코드"
        body = (
            f"TooTalk 회원가입을 진행 중입니다.\n\n"
            f"인증코드: {code}\n\n"
            f"본 코드는 3분 후 만료됩니다.\n"
            f"요청한 적이 없다면 본 메일을 무시해주세요.\n"
        )
    elif purpose == "password_reset":
        subject = "[TooTalk] 비밀번호 재설정 인증코드"
        body = (
            f"TooTalk 비밀번호 재설정을 요청하셨습니다.\n\n"
            f"인증코드: {code}\n\n"
            f"본 코드는 3분 후 만료됩니다.\n"
            f"요청하지 않으셨다면 즉시 비밀번호를 변경하세요.\n"
        )
    else:
        raise ValueError(f"알 수 없는 purpose: {purpose!r}")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    # 한글 본문 UTF-8 encode 명시
    msg.set_content(body, charset="utf-8")
    return msg


async def _send_once(
    msg: EmailMessage,
    host: str,
    port: int,
    user: str,
    password: str,
    tls_mode: str,
) -> None:
    """단일 SMTP 연결 + 발송 — retry 상위에서 호출."""

    ssl_ctx = ssl.create_default_context()

    if tls_mode == "SMTPS":
        # SMTPS — connect_tls (465) — TLS wrap 즉시
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=user or None,
            password=password or None,
            use_tls=True,
            tls_context=ssl_ctx,
        )
    else:
        # STARTTLS — connect plaintext → STARTTLS upgrade (587)
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=user or None,
            password=password or None,
            start_tls=True,
            tls_context=ssl_ctx,
        )


async def send_otp_email(to_email: str, code: str, purpose: str) -> None:
    """OTP 메일 발송 — aiosmtplib + STARTTLS/SMTPS + SASL + retry.

    발송 실패 시 지수 백오프 3회 재시도 후 최종 예외를 raise.
    호출자 (register.py / reset_password.py) try/except 비차단 처리.

    Raises
    ------
    RuntimeError
        aiosmtplib 미설치 시.
    Exception
        3회 재시도 후에도 SMTP 오류 발생 시.
    """

    if aiosmtplib is None:
        raise RuntimeError(
            "aiosmtplib 미설치 — `pip install -r server/requirements.txt` 후 재시도"
        )

    host, port, user, password, tls_mode = _resolve_smtp_params()
    msg = build_otp_email(to_email=to_email, code=code, purpose=purpose)

    log.info(
        "[SMTP] OTP 발송 시도 host=%s port=%d tls=%s to=%s purpose=%s",
        host, port, tls_mode, to_email, purpose,
    )

    # 지수 백오프 retry (3회)
    last_exc: Optional[Exception] = None
    for attempt in range(1, _RETRY_COUNT + 1):
        try:
            await _send_once(msg, host, port, user, password, tls_mode)
            log.info("[SMTP] OTP 발송 성공 to=%s attempt=%d", to_email, attempt)
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = _RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            log.warning(
                "[SMTP] 발송 실패 attempt=%d/%d to=%s err=%r — %.1fs 대기",
                attempt, _RETRY_COUNT, to_email, exc, wait,
            )
            if attempt < _RETRY_COUNT:
                await asyncio.sleep(wait)

    # 3회 모두 실패 — 최종 예외 re-raise
    raise last_exc  # type: ignore[misc]
