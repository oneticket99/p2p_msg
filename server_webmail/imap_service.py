# SPDX-License-Identifier: GPL-3.0-or-later
"""IMAP imaplib wrapper — cycle 169.861 M4.

본 모듈 = aiohttp handler 에서 호출하는 imaplib.IMAP4_SSL 동기 wrapper.
event loop 회피 = asyncio.to_thread 로 background 실행 (M5 후속 cycle 안 aioimaplib 전환 검토).

Exec Plan: docs/exec-plans/active/2026-06-09-webmail-python-backend.md M4
"""

from __future__ import annotations

import email
import email.header
import email.policy
import email.utils
import html
import html.parser
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
    """INBOX 최신 메일 paginate (UID 역순) — BODY[HEADER.FIELDS] fetch.

    한글 주석: cycle 169.862 회수 — ENVELOPE byte tuple 휴리스틱 → BODY[HEADER.FIELDS] +
    email.message_from_bytes 정확 parse. From/Subject = MIME encoded-word 디코드 정합.
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
            # 한글 주석: BODY.PEEK = \Seen flag 무변경 (readonly 정합)
            typ, fetch_data = m.uid(
                "FETCH",
                raw_uid,
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
            )
            if typ != "OK" or not fetch_data:
                continue
            summary = _parse_header_fields(uid, fetch_data)
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


def _parse_header_fields(uid: int, fetch_data: list) -> Optional[MailSummary]:
    """imaplib BODY[HEADER.FIELDS] 응답 → MailSummary.

    한글 주석: BODY[HEADER.FIELDS (FROM SUBJECT DATE)] = RFC822 header text 만 반환.
    email.message_from_bytes 정확 parse + MIME encoded-word (=?UTF-8?B?...?=) 디코드.
    """

    raw_header = _extract_rfc822(fetch_data)
    if raw_header is None:
        # 한글 주석: 응답 안 bytes payload 부재 → 빈 필드 fallback
        return MailSummary(uid=uid, from_addr="", subject="", date="")
    try:
        msg = email.message_from_bytes(raw_header, policy=email.policy.default)
    except Exception:
        return MailSummary(uid=uid, from_addr="", subject="", date="")
    return MailSummary(
        uid=uid,
        from_addr=_decode_header_value(msg.get("From", "")),
        subject=_decode_header_value(msg.get("Subject", "")),
        date=_decode_header_value(msg.get("Date", "")),
    )


def _decode_header_value(raw: object) -> str:
    """MIME encoded-word 헤더 → 사람 가독 문자열.

    한글 주석: email.header.decode_header = `[(bytes/str, encoding), ...]` 반환.
    UTF-8 / EUC-KR / Latin-1 디코드 + concat 정합.
    """

    if raw is None:
        return ""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        parts = email.header.decode_header(raw)
    except Exception:
        return raw
    out: list[str] = []
    for piece, charset in parts:
        if isinstance(piece, bytes):
            try:
                out.append(piece.decode(charset or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                out.append(piece.decode("utf-8", errors="replace"))
        else:
            out.append(piece)
    return "".join(out).strip()


class _HTMLToText(html.parser.HTMLParser):
    """HTML body → plaintext (XSS sanitize + tag strip).

    한글 주석: M5 후속 cycle 안 bleach 도입 시 HTML 그대로 렌더 — 본 cycle = plain 강제.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1
        elif tag == "br":
            self._parts.append("\n")
        elif tag in ("p", "div", "tr", "li"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _html_to_plaintext(html_str: str) -> str:
    """HTML 문자열 → 사람 가독 plaintext (entity unescape + tag strip)."""

    parser = _HTMLToText()
    try:
        parser.feed(html_str)
        parser.close()
    except Exception:
        # 한글 주석: parser 실패 → 단순 entity unescape fallback
        return html.unescape(html_str)
    return parser.get_text()


def _parse_message(msg: email.message.EmailMessage) -> MailBody:
    """email.message_from_bytes 결과 → MailBody (plaintext 본문 + header).

    한글 주석: cycle 169.862 회수 — text/plain 우선 + 부재 시 text/html → strip tags + unescape.
    HTML 본문 → entity (&nbsp; 등) 사람 가독 plaintext 변환 (XSS 우려, M6 안 bleach 도입).
    """

    plain_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not plain_body:
                plain_body = _decode_part_body(part)
            elif ctype == "text/html" and not html_body:
                html_body = _decode_part_body(part)
            if plain_body and html_body:
                break
    else:
        ctype = msg.get_content_type()
        single = _decode_part_body(msg)
        if ctype == "text/html":
            html_body = single
        else:
            plain_body = single
    # 한글 주석: plain 우선 + html.unescape (plain 안 &nbsp; 등 entity 정리)
    if plain_body:
        body_text = html.unescape(plain_body)
    elif html_body:
        body_text = _html_to_plaintext(html_body)
    else:
        body_text = ""
    return MailBody(
        from_addr=_decode_header_value(msg.get("From", "")),
        to_addr=_decode_header_value(msg.get("To", "")),
        subject=_decode_header_value(msg.get("Subject", "")),
        date=_decode_header_value(msg.get("Date", "")),
        body_text=body_text,
    )


def _decode_part_body(part: email.message.EmailMessage) -> str:
    """단일 MIME part body → str (charset 추론 + errors=replace 정합)."""

    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
    except Exception:
        pass
    payload = part.get_payload(decode=True)
    if isinstance(payload, (bytes, bytearray)):
        return payload.decode(
            part.get_content_charset() or "utf-8", errors="replace"
        )
    return ""
