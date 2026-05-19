# SPDX-License-Identifier: GPL-3.0-or-later
"""사용자 locale 선택 settings UI — 5 locale dropdown + 즉시 적용 (cycle 134).

Phase 5 Item 1 i18n actual binding 의 의무 — cycle 132 skeleton + cycle 133
.ts 5 locale 의 사용자 선택 UI. PyQt6 부재 환경 (CI Linux runner) 의
graceful fallback 패턴 = ``_PYQT_AVAILABLE`` 분기.

설계 결정
---------
- ``LocaleSettingsDialog`` = PyQt6 ``QDialog`` 의무 단 PyQt6 부재 환경 의
  graceful skip — ``__init__`` 의 빠른 return + log warning.
- ``apply_locale_runtime`` = ``install_qt_translator`` wrap + PyQt6 부재
  graceful False — pure logic 함수 의 GUI 부재 환경 테스트 가능.
- locale persist = ``UserLocalePreferences`` → ``save_user_locale_preferences``
  의 callback 의무 (본 dialog 의 dependency injection 패턴).
"""

from __future__ import annotations

import logging
from typing import Optional

from app.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, install_qt_translator

log = logging.getLogger(__name__)

try:
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
    )
    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover - PyQt6 미설치 환경 폴백
    QComboBox = None  # type: ignore[assignment, misc]
    QDialog = object  # type: ignore[assignment, misc]
    QHBoxLayout = None  # type: ignore[assignment, misc]
    QLabel = None  # type: ignore[assignment, misc]
    QPushButton = None  # type: ignore[assignment, misc]
    QVBoxLayout = None  # type: ignore[assignment, misc]
    _PYQT_AVAILABLE = False


# 한글 주석 — locale 코드 → 사용자 표시 label 매핑 (5 locale)
LOCALE_LABELS = {
    "ko": "한국어",
    "en": "English",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "ja": "日本語",
}


class LocaleSettingsDialog(QDialog):  # type: ignore[misc, valid-type]
    """5 locale dropdown + 즉시 적용 + persist callback dialog.

    Parameters
    ----------
    current_locale : str
        현재 활성 locale (UserLocalePreferences 의 로딩값). default ko.
    parent : QWidget | None
        Qt 부모 위젯.

    Attributes
    ----------
    selected_locale : str
        OK 클릭 시 dropdown 의 선택값. reject 시 ``current_locale`` 유지.
    """

    LOCALE_LABELS = LOCALE_LABELS  # 한글 주석 — class-level alias (테스트 편의)

    def __init__(
        self,
        current_locale: str = DEFAULT_LOCALE,
        parent=None,
    ) -> None:
        if not _PYQT_AVAILABLE:
            log.warning("[locale-settings] PyQt6 부재 — graceful skip")
            # PyQt6 부재 환경 의 graceful — QDialog 부모 __init__ 호출 차단
            self.current_locale = current_locale
            self.selected_locale = current_locale
            return
        super().__init__(parent)
        self.current_locale = current_locale
        self.selected_locale = current_locale
        self._setup_ui()

    def _setup_ui(self) -> None:
        # 한글 주석 — locale dropdown + 확인/취소 버튼 layout 구성
        self.setWindowTitle("언어 설정 / Language / 语言 / 言語")
        self.setMinimumWidth(320)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("언어 선택 / Language / 语言 / 言語"))
        self.combo = QComboBox()
        for loc in SUPPORTED_LOCALES:
            self.combo.addItem(LOCALE_LABELS.get(loc, loc), loc)
        # 한글 주석 — 현재 locale 의 dropdown index 매핑 (부재 시 0 폴백)
        if self.current_locale in SUPPORTED_LOCALES:
            idx = SUPPORTED_LOCALES.index(self.current_locale)
        else:
            idx = 0
        self.combo.setCurrentIndex(idx)
        layout.addWidget(self.combo)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("확인")
        btn_cancel = QPushButton("취소")
        btn_ok.clicked.connect(self._on_ok)  # type: ignore[arg-type]
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_ok(self) -> None:
        # 한글 주석 — selected locale capture + accept
        self.selected_locale = self.combo.currentData()
        self.accept()


def apply_locale_runtime(app, locale: str) -> bool:
    """runtime locale switch — ``install_qt_translator`` wrap.

    Parameters
    ----------
    app : QApplication
        대상 QApplication 인스턴스.
    locale : str
        5 locale 안 하나 (``SUPPORTED_LOCALES``). 부재 시 install fail.

    Returns
    -------
    bool
        PyQt6 부재 = False, qm 파일 부재 = False, 성공 = True.
    """

    if not _PYQT_AVAILABLE:
        log.warning("[locale-settings] PyQt6 부재 — apply_locale_runtime skip")
        return False
    if locale not in SUPPORTED_LOCALES:
        log.warning(
            "[locale-settings] locale=%r unsupported — apply skip",
            locale,
        )
        return False
    return install_qt_translator(app, locale=locale)
