# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 117 — sensitive 데이터 redact filter.

API key / JWT / 비번 / 이메일 / 카드번호 / 주민번호 의 log 노출 차단.
정합 = [[feedback-db-audit-timestamp-ip-activity]] 의 PII protection.

설계 결정
---------
- pattern + replacement 의 list-of-tuple — caller 영역 확장 가능.
- record.msg + record.args + extras 의 모든 string field 의 일괄 redact.
- raw match 의 substring 보존 — 첫 N자 + `***` + 마지막 N자 (트레이싱 가능
  + secret 비노출).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Pattern, Tuple


_REDACT_TAIL = "***"


def _mask(match: re.Match) -> str:
    """match group 의 mask — `prefix***suffix` 형식."""

    text = match.group(0)
    if len(text) <= 8:
        return _REDACT_TAIL
    return f"{text[:3]}{_REDACT_TAIL}{text[-2:]}"


# 의무 redact pattern — secret/PII 노출 차단
DEFAULT_REDACT_PATTERNS: Tuple[Tuple[Pattern[str], str], ...] = (
    # Anthropic / OpenAI / generic API key (sk- prefix 32+ char)
    (re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"), "sk-***"),
    # Bearer / JWT — Authorization header value 의 token
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{20,}"), "Bearer ***"),
    # JWT 3 segment (eyJxxx.yyy.zzz)
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "jwt-***"),
    # 비번 (password / passwd) = value 의 redact
    (re.compile(r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?([^'\"\s,}]+)", re.IGNORECASE), r"\1=***"),
    # api_key = value
    (re.compile(r"(api[\s_-]?key)['\"]?\s*[:=]\s*['\"]?([^'\"\s,}]+)", re.IGNORECASE), r"\1=***"),
    # 주민등록번호 \d{6}-[1-4]\d{6}
    (re.compile(r"\b\d{6}-[1-4]\d{6}\b"), "RRN-***"),
    # 카드 번호 (4 group of 4 digits, hyphen or space)
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "CARD-***"),
    # 이메일 — local part 의 partial mask (도메인 보존, 디버깅 가능)
    (re.compile(r"\b([A-Za-z0-9._%+-]{1,3})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"), r"\1***\2"),
    # DB connection string (mysql/postgres://user:pw@host)
    (re.compile(r"(mysql|postgres(?:ql)?|mongodb|mariadb)://[^@\s]+:[^@\s]+@"), r"\1://***:***@"),
)


def redact_sensitive(
    text: str,
    patterns: Iterable[Tuple[Pattern[str], str]] = DEFAULT_REDACT_PATTERNS,
) -> str:
    """text 안 의 의 모든 sensitive 패턴 substitute.

    Parameters
    ----------
    text : str
        대상 string.
    patterns : Iterable
        (compiled regex, replacement) tuple list.

    Returns
    -------
    str
        redacted string.
    """

    if not text:
        return text
    out = text
    for pattern, replacement in patterns:
        out = pattern.sub(replacement, out)
    return out


class RedactingFilter(logging.Filter):
    """logging filter — record.msg + args + getMessage 결과 의 redact 적용.

    handler chain 의 formatter 호출 직전 의 의무 layer. JSON formatter 의
    extras dict 의 string value 의 redact 도 적용.
    """

    def __init__(
        self,
        patterns: Iterable[Tuple[Pattern[str], str]] = DEFAULT_REDACT_PATTERNS,
    ) -> None:
        super().__init__()
        self._patterns = tuple(patterns)

    def filter(self, record: logging.LogRecord) -> bool:
        # 한글 주석: msg + args 의 redact — getMessage() 호출 결과 의 정합 정합
        if isinstance(record.msg, str):
            record.msg = redact_sensitive(record.msg, self._patterns)
        if record.args:
            new_args = []
            for arg in record.args if isinstance(record.args, tuple) else (record.args,):
                if isinstance(arg, str):
                    new_args.append(redact_sensitive(arg, self._patterns))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args[0]

        # extras (caller 의 logger.info("...", extra={"...": ...}) field) redact
        for key, value in list(record.__dict__.items()):
            if key.startswith("_") or key in (
                "args", "msg", "name", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "process", "processName", "taskName",
            ):
                continue
            if isinstance(value, str):
                record.__dict__[key] = redact_sensitive(value, self._patterns)
        return True
