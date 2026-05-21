# SPDX-License-Identifier: GPL-3.0-or-later
"""WelcomeDialog — TooTalk 첫 실행 진입 화면 (cycle 153 phase 2).

텔레그램 desktop intro 등가 layout — banner + logo + sub + CTA + locale switch.
정합 = FRONTEND.md §15 BI + telegram-ui-survey.md §1 + toonation-brand-integration-plan §4.2.

Flow:
    welcome → 시작하기 click → 종료 (parent main.py 안 다음 LoginDialog 진입)
    locale link click → 즉시 i18n switch + 본 dialog 재 렌더
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

# cycle 169.356 — labels.py 4 locale dict + PyQt6 QCoreApplication.translate dual chain
# labels.tr() 우선 lookup + 부재 시점 QCoreApplication.translate fallback
from app.i18n import labels as _i18n_labels


def _tr(src: str) -> str:
    # 한글 주석 — labels key slug 추출 chain (한글 src → key generation)
    import re as _re
    slug = _re.sub(r"[^가-힣A-Za-z0-9]+", "_", src)[:40].strip("_").lower()
    return _i18n_labels.tr(slug) if _i18n_labels.tr(slug) != slug else QCoreApplication.translate("MainWindow", src)

# 한글 주석 — branding asset path
_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "tootalk_symbol.png"
_MASCOT_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "toona_sakamoto.png"


class WelcomeDialog(QDialog):
    """TooTalk 첫 실행 환영 화면.

    텔레그램 desktop intro 등가 — banner (Deep Navy → Toonation Blue gradient) + 로고 full +
    sub copy + 시작하기 CTA + 4 locale switch link.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("TooTalk")
        self.setMinimumSize(560, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── banner — Deep Navy → Toonation Blue gradient + 로고 ──────────────
        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner.setMinimumHeight(300)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — symbol + Talk QHBoxLayout 합성 복원 (cycle 169.16 — composite PNG 폐기)
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.setSpacing(0)
        logo_row.setContentsMargins(0, 0, 0, 0)

        symbol_label = QLabel()
        symbol_label.setStyleSheet("background: transparent;")
        symbol_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if _LOGO_PATH.is_file():
            pixmap = QPixmap(str(_LOGO_PATH))
            scaled = pixmap.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            symbol_label.setPixmap(scaled)
        logo_row.addWidget(symbol_label)

        talk_label = QLabel("Talk")
        talk_label.setStyleSheet(
            "background: transparent;"
            " color: #ffffff;"
            " font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;"
            " font-size: 55px;"
            " font-weight: 700;"
            " letter-spacing: -1px;"
        )
        logo_row.addWidget(talk_label)
        banner_layout.addLayout(logo_row)

        outer.addWidget(banner)

        # ── content area ────────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(48, 48, 48, 48)
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — TooTalk title 텍스트 → mascot 이미지 (toona_sakamoto.png) 대체
        # 사용자 directive 2026-05-20 cycle 169.9
        mascot_label = QLabel()
        mascot_label.setStyleSheet("background: transparent;")
        mascot_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if _MASCOT_PATH.is_file():
            mascot_pixmap = QPixmap(str(_MASCOT_PATH))
            mascot_scaled = mascot_pixmap.scaledToHeight(160, Qt.TransformationMode.SmoothTransformation)
            mascot_label.setPixmap(mascot_scaled)
        content_layout.addWidget(mascot_label)

        # 한글 주석 — mascot 직하 "투턱" 텍스트 (사용자 directive 2026-05-20 cycle 169.10)
        mascot_name = QLabel("투턱")
        mascot_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mascot_name.setStyleSheet(
            "background: transparent;"
            " color: #ffffff;"
            " font-size: 24px;"
            " font-weight: 700;"
            " letter-spacing: -1px;"
        )
        content_layout.addWidget(mascot_name)

        sub1 = QLabel(_tr("친구와 직접 연결 P2P 메신저"))
        sub1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub1.setStyleSheet("color: #9ca3af; font-size: 14px;")
        content_layout.addWidget(sub1)

        sub2 = QLabel(_tr("원격 데스크탑 도움 + GPLv3 OSS"))
        sub2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub2.setStyleSheet("color: #9ca3af; font-size: 14px;")
        content_layout.addWidget(sub2)

        content_layout.addSpacing(40)

        # 한글 주석 — 시작하기 CTA — Toonation primary
        btn_start = QPushButton(_tr("시작하기"))
        btn_start.setProperty("variant", "primary")
        btn_start.setMinimumHeight(48)
        btn_start.setMinimumWidth(280)
        btn_start.clicked.connect(self.accept)  # type: ignore[arg-type]
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_start)
        btn_layout.addStretch(1)
        content_layout.addLayout(btn_layout)

        content_layout.addSpacing(16)

        # 한글 주석 — 4 locale switch row (text-only ghost button)
        locale_row = QHBoxLayout()
        locale_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        locale_row.setSpacing(20)
        for locale_label, locale_code in [
            ("한국어", "ko"),
            ("English", "en"),
            ("中文", "zh-CN"),
            ("日本語", "ja"),
        ]:
            link = QPushButton(locale_label)
            link.setProperty("variant", "ghost")
            link.setFlat(True)
            link.clicked.connect(lambda _checked=False, c=locale_code: self._on_locale_click(c))  # type: ignore[arg-type]
            locale_row.addWidget(link)
        content_layout.addLayout(locale_row)

        outer.addWidget(content)
        outer.addStretch(1)

    def _on_locale_click(self, locale: str) -> None:
        """locale switch — UserLocalePreferences persist + labels.set_locale + dialog accept."""
        # cycle 169.356 — labels global locale 갱신 chain 추가 (사용자 directive image #119/120)
        try:
            _i18n_labels.set_locale(locale)
            log.info("[i18n] labels.set_locale → %s", locale)
        except Exception as exc:
            log.debug("labels set_locale graceful skip — %r", exc)
        try:
            from app.config.user_preferences import (
                UserLocalePreferences,
                save_user_locale_preferences,
            )
            save_user_locale_preferences(UserLocalePreferences(locale=locale))
            log.info("locale switch persist — %s", locale)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("locale persist 실패 graceful — %r", exc)
        self.accept()
