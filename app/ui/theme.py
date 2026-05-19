# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Toonation BI 통합 theme loader — cycle 153 phase 1 entry.

ground truth = FRONTEND.md §15 + DESIGN.md §11. QSS load + dark/light auto-detect.

사용:
    from app.ui.theme import load_theme
    load_theme(qt_app, theme="auto")  # palette lightness 자동 감지

theme 옵션:
    "dark"  — base-dark.qss 강제
    "light" — base-light.qss 강제 (cycle 154+ 신설 예정)
    "auto"  — palette().windowText().lightness() < 128 → dark
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

log = logging.getLogger(__name__)

# 한글 주석 — 본 모듈 의 base path = app/assets/themes/
_THEME_DIR = Path(__file__).resolve().parent.parent / "assets" / "themes"

ThemeMode = Literal["dark", "light", "auto"]


def detect_mode(app: QApplication) -> str:
    """현 palette 기반 dark/light 자동 감지.

    palette().windowText().lightness() < 128 → dark.
    """
    # 한글 주석 — windowText 색상 의 lightness 의 0~255 범위
    text_lightness = app.palette().color(QPalette.ColorRole.WindowText).lightness()
    return "dark" if text_lightness >= 128 else "light"


def load_theme(app: QApplication, theme: ThemeMode = "auto") -> bool:
    """Toonation BI base theme load.

    Parameters
    ----------
    app : QApplication
        대상 application instance.
    theme : str
        'dark' / 'light' / 'auto' (palette lightness 자동 감지).

    Returns
    -------
    bool
        QSS load 성공 여부. file 부재 시 False + log warn.
    """
    # 한글 주석 — auto 모드 = palette 기반 dark/light 결정
    resolved = detect_mode(app) if theme == "auto" else theme

    qss_path = _THEME_DIR / f"base-{resolved}.qss"
    if not qss_path.is_file():
        log.warning("theme QSS 부재 — %s (graceful skip)", qss_path)
        return False

    try:
        qss = qss_path.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("theme QSS read 실패 — %s (%s)", qss_path, exc)
        return False

    app.setStyleSheet(qss)
    log.info("Toonation BI theme load PASS — mode=%s path=%s", resolved, qss_path)
    return True
