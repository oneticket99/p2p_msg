# SPDX-License-Identifier: GPL-3.0-or-later
"""aiosmtplib 기반 비동기 SMTP client — Phase 1 이메일 OTP 발송.

[[project-smtp-demo-server]] 정합 — 데모 서버 (114.207.112.73) postfix 자체 설치.

환경변수:
- SMTP_HOST (default 114.207.112.73)
- SMTP_PORT (default 587 — STARTTLS)
- SMTP_USER (SASL 사용자)
- SMTP_PASS (SASL 비번 — 외부 노출 절대 금지)
- SMTP_FROM (발송 이메일 — default no-reply@tootalk.example)
- SMTP_TLS (default 1 = STARTTLS 활성)
"""

from __future__ import annotations

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
        발송 주소. None 이면 환경변수 SMTP_FROM.

    Returns
    -------
    EmailMessage
        UTF-8 한글 본문 + Subject + headers 정합.
    """

    sender = from_email or _env_str("SMTP_FROM", "no-reply@tootalk.example")

    if purpose == "signup":
        subject = "[TooTalk] 회원가입 인증코드"
        body = (
            f"TooTalk 회원가입을 진행 중입니다.\n\n"
            f"인증코드: {code}\n\n"
            f"본 코드는 3분 후 만료됩니다.\n"
            f"본인이 요청하지 않은 경우 본 메일을 무시해주세요.\n"
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
    msg.set_content(body, charset="utf-8")
    return msg


async def send_otp_email(to_email: str, code: str, purpose: str) -> None:
    """OTP 메일 발송 — aiosmtplib + STARTTLS + SASL.

    Raises
    ------
    RuntimeError
        aiosmtplib 미설치 시.
    aiosmtplib.errors.SMTPException
        SMTP 서버 오류 — 호출자 try/except retry.
    """

    if aiosmtplib is None:
        raise RuntimeError(
            "aiosmtplib 미설치 — `pip install -r server/requirements.txt` 후 재시도"
        )

    host = _env_str("SMTP_HOST", "114.207.112.73")
    port = _env_int("SMTP_PORT", 587)
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    use_tls = _env_int("SMTP_TLS", 1) == 1

    msg = build_otp_email(to_email=to_email, code=code, purpose=purpose)

    log.info(
        "[SMTP] OTP 발송 host=%s port=%d to=%s purpose=%s",
        host,
        port,
        to_email,
        purpose,
    )

    ssl_ctx = ssl.create_default_context() if use_tls else None
    await aiosmtplib.send(
        msg,
        hostname=host,
        port=port,
        username=user or None,
        password=password or None,
        start_tls=use_tls,
        tls_context=ssl_ctx,
    )
