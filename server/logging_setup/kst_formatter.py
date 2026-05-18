# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 116 — KST timezone Formatter (text + JSON).

[[feedback-timezone-kst]] 정합 — 모든 timestamp = Asia/Seoul. UTC 절대 금지.
request_id contextvar (cycle 113) 의 auto-inject + JSON structured output.

설계 결정
---------
- KSTFormatter (text) — `[YYYY-mm-dd H:i:s KST] LEVEL logger: message`.
- KSTJSONFormatter — 단일 line JSON {ts, level, name, message, request_id,
  + extra fields}. nginx main_kst log format + json-file driver + Phase 5+
  ELK / Loki 의 ingestion 정합.
- request_id contextvar lookup — middleware 외 호출 (background task 등)
  의 None graceful.
- traceback formatting — JSON 시 `exc_info` field 의 stack list 분리.

본 module 범위 외
----------------
- 로그 rotation — docker json-file driver 의 외부 처리 (Item 1 정합).
- 외부 시스템 forwarding (Loki / Splunk) — 별개 cycle.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


_KST_OFFSET = timedelta(hours=9)
_KST = timezone(_KST_OFFSET, name="KST")

# 기본 text format — 정본 §E 정합
_TEXT_FMT = "[%(asctime)s.%(msecs)03d KST] %(levelname)s %(name)s [%(request_id)s]: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _kst_now() -> datetime:
    """현재 KST datetime — timezone-aware."""

    return datetime.now(tz=_KST)


def _get_request_id_safe() -> str:
    """contextvar lookup — middleware 외 None 시 `-` 반환 (formatter 안전성)."""

    try:
        from server.middleware.request_id import get_request_id

        rid = get_request_id()
        return rid if rid else "-"
    except Exception:
        return "-"


class KSTFormatter(logging.Formatter):
    """text formatter — KST timestamp + request_id field auto-inject.

    `LogRecord.asctime` 의 KST 변환 + `LogRecord.request_id` 의 contextvar
    lookup. caller 영역 추가 attribute 부착 불필요.
    """

    def __init__(self, fmt: Optional[str] = None) -> None:
        super().__init__(fmt or _TEXT_FMT, datefmt=_DATEFMT)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        # 한글 주석: record.created 의 epoch float → KST datetime 변환
        dt = datetime.fromtimestamp(record.created, tz=_KST)
        return dt.strftime(datefmt or _DATEFMT)

    def format(self, record: logging.LogRecord) -> str:
        # 한글 주석: request_id contextvar auto-inject
        if not hasattr(record, "request_id"):
            record.request_id = _get_request_id_safe()
        return super().format(record)


class KSTJSONFormatter(logging.Formatter):
    """JSON structured formatter — production LOG_FORMAT=json 시 활성.

    출력 schema (단일 line JSON):
        {
            "ts": "2026-05-22T18:30:00.123+09:00",
            "level": "INFO",
            "name": "server.main",
            "message": "...",
            "request_id": "uuid-hex-32",
            "extra": {...optional caller fields...},
            "exc_info": "...traceback if exception..."
        }
    """

    _RESERVED_FIELDS = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
            "request_id",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, tz=_KST)
        if not hasattr(record, "request_id"):
            record.request_id = _get_request_id_safe()

        payload: dict[str, Any] = {
            "ts": dt.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "request_id": record.request_id,
        }

        # 한글 주석: caller 가 logger.info("...", extra={"key": value}) 로 부착한
        # extra field 의 의 자동 흡수 — reserved 제외
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in self._RESERVED_FIELDS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                extras[key] = value
            except (TypeError, ValueError):
                extras[key] = repr(value)
        if extras:
            payload["extra"] = extras

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)
