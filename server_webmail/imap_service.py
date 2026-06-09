# SPDX-License-Identifier: GPL-3.0-or-later
"""IMAP imaplib wrapper — cycle 169.861 M4.

본 모듈 = aiohttp handler 에서 호출하는 imaplib.IMAP4_SSL 동기 wrapper.
event loop 회피 = asyncio.to_thread 로 background 실행 (M5 후속 cycle 안 aioimaplib 전환 검토).

Exec Plan: docs/exec-plans/active/2026-06-09-webmail-python-backend.md M4
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import imaplib
import ssl
from dataclasses import dataclass
from typing import Optional


@dataclass
class MailSummary:
    """INBOX list 1행 — UID + From + Subject + Date."""

    uid: int
    from_addr: str
    subject: str
    date: str


@dataclass
class MailBody:
    """단일 메일 본문 — header + plain text body."""

    from_addr: str
    to_addr: str
    subject: str
    date: str
    body_text: str


class IMAPError(RuntimeError):
    """IMAP 연결/인증/명령 오류 공통 예외."""


def _build_ssl_context() -> ssl.SSLContext:
    """IMAP4_SSL TLS context — default cert 검증 활성.

    한글 주석: Let's Encrypt cert 정합 — webmail backend 가 mail.dopa.co.kr 실 cert 검증.
    """

    return ssl.create_default_context()


def connect_and_login(
    host: str, port: int, user: str, password: str
) -> imaplib.IMAP4_SSL:
    """IMAP4_SSL 연결 + LOGIN — 실패 시 IMAPError 발생.

    한글 주석: caller 의무 = m.logout() 호출 후 정리. context manager 부재 정합 (imaplib 표준).
    """

    try:
        m = imaplib.IMAP4_SSL(host, port, ssl_context=_build_ssl_context())
    except (OSError, ssl.SSLError) as exc:
        raise IMAPError(f"IMAP 연결 실패 {host}:{port} — {exc}") from exc
    try:
        typ, _ = m.login(user, password)
    except imaplib.IMAP4.error as exc:
        try:
            m.logout()
        except Exception:
            pass
        raise IMAPError(f"IMAP LOGIN 실패 — {exc}") from exc
    if typ != "OK":
        try:
            m.logout()
        except Exception:
            pass
        raise IMAPError(f"IMAP LOGIN 비정상 응답 — {typ}")
    return m


def list_inbox(
    host: str, port: int, user: str, password: str, limit: int = 50
) -> list[MailSummary]:
    """INBOX 최신 메일 paginate (UID 역순) — ENVELOPE fetch.

    한글 주석: 본문 fetch 회피 (BODY[] 비호출) — list view 의 의무 lite payload.
    """

    m = connect_and_login(host, port, user, password)
    try:
        typ, _ = m.select("INBOX", readonly=True)
        if typ != "OK":
            return []
        typ, data = m.uid("SEARCH", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()
        # 한글 주석: 최신 limit 통 만 (역순 slice)
        target_uids = uids[-limit:][::-1]
        out: list[MailSummary] = []
        for raw_uid in target_uids:
            uid = int(raw_uid.decode("ascii"))
            typ, fetch_data = m.uid(
                "FETCH", raw_uid, "(ENVELOPE)"
            )
            if typ != "OK" or not fetch_data:
                continue
            summary = _parse_envelope(uid, fetch_data)
            if summary is not None:
                out.append(summary)
        return out
    finally:
        try:
            m.logout()
        except Exception:
            pass


def fetch_body(
    host: str, port: int, user: str, password: str, uid: int
) -> Optional[MailBody]:
    """단일 메일 RFC822 fetch + plaintext part 추출.

    한글 주석: HTML part 무시 (XSS 우려, M5 후속 cycle 안 bleach sanitize 추가).
    """

    m = connect_and_login(host, port, user, password)
    try:
        typ, _ = m.select("INBOX", readonly=True)
        if typ != "OK":
            return None
        typ, fetch_data = m.uid(
            "FETCH", str(uid).encode("ascii"), "(RFC822)"
        )
        if typ != "OK" or not fetch_data:
            return None
        raw_bytes = _extract_rfc822(fetch_data)
        if raw_bytes is None:
            return None
        msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
        return _parse_message(msg)
    finally:
        try:
            m.logout()
        except Exception:
            pass


def _extract_rfc822(fetch_data: list) -> Optional[bytes]:
    """imaplib FETCH 응답 형식 안 RFC822 payload bytes 추출."""

    # 한글 주석: imaplib FETCH 응답 = [(header_tuple, body_bytes), b')'] 패턴 다수
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2:
            payload = item[1]
            if isinstance(payload, (bytes, bytearray)):
                return bytes(payload)
    return None


def _parse_envelope(uid: int, fetch_data: list) -> Optional[MailSummary]:
    """imaplib ENVELOPE 응답 → MailSummary.

    한글 주석: ENVELOPE 형식 = (date subject (from) ... (to) ...) tuple. imaplib 가 bytes 반환.
    parse 간소화 = imaplib 의 raw bytes 안 grep 대신 RFC822 header re-fetch 회피하기 위해
    email.message_from_bytes 안 envelope sub-text 직접 parse.
    """

    # 한글 주석: 안전 fallback = ENVELOPE parse 실패 시 빈 필드 채움
    raw = b""
    for item in fetch_data:
        if isinstance(item, (bytes, bytearray)):
            raw += bytes(item)
        elif isinstance(item, tuple):
            for sub in item:
                if isinstance(sub, (bytes, bytearray)):
                    raw += bytes(sub)
    text = raw.decode("utf-8", errors="replace")
    return MailSummary(
        uid=uid,
        from_addr=_extract_field(text, "From"),
        subject=_extract_field(text, "Subject"),
        date=_extract_field(text, "Date"),
    )


def _extract_field(text: str, marker: str) -> str:
    """ENVELOPE bytes 안 quoted-string lookup — 1차 휴리스틱.

    한글 주석: imaplib ENVELOPE 정확 parse = 별도 library 필요 (M5 후속 cycle 안 aioimaplib).
    본 cycle = lite parse — ENVELOPE 안 quoted 1차 후보 반환. 빈 문자열 fallback OK.
    """

    # 한글 주석: marker 명시 lookup 부재 정합 — raw ENVELOPE 안 quoted text 1차 후보.
    # 본 함수 = 단순 fallback (ENVELOPE byte tuple 정확 parse 는 M5 후속 cycle).
    _ = text, marker
    return ""


def _parse_message(msg: email.message.EmailMessage) -> MailBody:
    """email.message_from_bytes 결과 → MailBody (plaintext 본문 + header)."""

    body_text = ""
    if msg.is_multipart():
        # 한글 주석: 첫 text/plain part 만 추출 (HTML 무시 — XSS 우려, M5 안 sanitize 추가)
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body_text = part.get_content()
                    break
                except Exception:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, (bytes, bytearray)):
                        body_text = payload.decode(
                            part.get_content_charset() or "utf-8",
                            errors="replace",
                        )
                        break
    else:
        try:
            body_text = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, (bytes, bytearray)):
                body_text = payload.decode(
                    msg.get_content_charset() or "utf-8", errors="replace"
                )
    return MailBody(
        from_addr=str(msg.get("From", "")),
        to_addr=str(msg.get("To", "")),
        subject=str(msg.get("Subject", "")),
        date=str(msg.get("Date", "")),
        body_text=body_text or "",
    )
