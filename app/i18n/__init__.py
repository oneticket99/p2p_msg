# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk i18n base — PyQt6 QTranslator + 5 locale skeleton (Phase 5 cycle 131)."""
from __future__ import annotations
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

SUPPORTED_LOCALES = ("ko", "en", "zh-CN", "zh-TW", "ja")
DEFAULT_LOCALE = "ko"


def resolve_locale() -> str:
    """환경변수 LANG / LOCALE 의 supported locale 정규화 — fallback ko."""
    raw = (os.environ.get("LOCALE") or os.environ.get("LANG") or "").lower()
    for loc in SUPPORTED_LOCALES:
        if raw.startswith(loc.lower()):
            return loc
    return DEFAULT_LOCALE


def install_qt_translator(app, locale: str | None = None) -> bool:
    """한글 주석 — Phase 5 진입 본격 binding. 현재 skeleton 의 graceful False."""
    try:
        from PyQt6.QtCore import QTranslator
    except ImportError:
        return False
    loc = locale or resolve_locale()
    translator = QTranslator()
    ts_path = Path(__file__).parent / "translations" / f"tootalk_{loc}.qm"
    if not ts_path.is_file():
        log.warning("[i18n] qm 파일 부재 — %s (Phase 5 본격 cycle 생성)", ts_path)
        return False
    if translator.load(str(ts_path)):
        app.installTranslator(translator)
        return True
    return False
