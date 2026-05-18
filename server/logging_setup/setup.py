# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 117 — logging configure entry.

LOG_FORMAT env 분기 — text (개발) / json (production) + KSTFormatter +
RedactingFilter + 7 logger 분류 (server / app + sub-package).

설계 결정
---------
- configure_logging(level, format) 호출 idempotent — 기존 root handler clear.
- LOG_FORMAT=json 시 KSTJSONFormatter, 그 외 KSTFormatter (text).
- RedactingFilter = root logger 의 attached — 모든 child logger 자동 적용.
- noisy 외부 lib (aiohttp.access 등) 의 별개 level 설정 가능.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from .kst_formatter import KSTFormatter, KSTJSONFormatter
from .redact import RedactingFilter


def configure_logging(
    level: str = "INFO",
    log_format: str = "text",
    *,
    enable_redact: bool = True,
) -> None:
    """root logger 의 handler + formatter + filter 설정.

    Parameters
    ----------
    level : str
        log level (DEBUG / INFO / WARNING / ERROR / CRITICAL). 무효 = INFO 폴백.
    log_format : str
        ``text`` (개발) 또는 ``json`` (production).
    enable_redact : bool
        RedactingFilter 활성 (default True). False 시 raw log (테스트 전용).
    """

    root = logging.getLogger()
    # idempotent — 기존 handler clear (test fixture + 재기동 정합)
    for h in list(root.handlers):
        root.removeHandler(h)
    for f in list(root.filters):
        root.removeFilter(f)

    handler = logging.StreamHandler(stream=sys.stdout)
    fmt_lower = (log_format or "text").strip().lower()
    if fmt_lower == "json":
        handler.setFormatter(KSTJSONFormatter())
    else:
        handler.setFormatter(KSTFormatter())

    # 한글 주석: filter = handler 의 attached — child logger 의 propagate 의무 적용
    if enable_redact:
        redact_filter = RedactingFilter()
        handler.addFilter(redact_filter)
        # 한글 주석: root 의 filter 도 동시 등록 (root 직접 호출 시점 의 정합).
        # 단 root.filters 의 child propagate 의무 부재 — handler attach 의무 핵심.
        root.addFilter(redact_filter)

    root.addHandler(handler)

    lvl = logging.getLevelName(level.upper() if level else "INFO")
    if not isinstance(lvl, int):
        lvl = logging.INFO
    root.setLevel(lvl)

    # 한글 주석: noisy 외부 lib 의 cap — aiohttp.access default WARNING (request log
    # 의 nginx access 의 중복 회피). caller 영역 override 가능.
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
