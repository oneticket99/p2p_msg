# SPDX-License-Identifier: GPL-3.0-or-later
"""ThemePicker — dark/light/auto 3 모드 토글 widget (cycle 153 phase 4 신설).

Toonation BI theme 의 사용자 switch + 즉시 적용.
정합 = app/ui/theme.py + toonation-brand-integration-plan §4.4.

signal:
    theme_changed(str) — selected mode ("dark" / "light" / "auto") emit
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

log = logging.getLogger(__name__)


class ThemePicker(QWidget):
    """dark / light / auto 3 button 토글 + theme_changed signal."""

    theme_changed = pyqtSignal(str)

    MODES = [
        ("dark", "🌙 다크"),
        ("light", "☀️ 라이트"),
        ("auto", "🔄 자동"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for i, (mode_key, label) in enumerate(self.MODES):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(36)
            btn.setProperty("variant", "secondary")
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _c=False, m=mode_key: self._on_clicked(m)
            )
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons[mode_key] = btn

        # 한글 주석 — auto default active
        self._buttons["auto"].setChecked(True)

    def _on_clicked(self, mode: str) -> None:
        """button click → theme reload + signal emit + UserLocalePreferences persist."""
        self.theme_changed.emit(mode)
        # 한글 주석 — 즉시 theme reload (graceful 부재 시 log debug)
        try:
            from PyQt6.QtWidgets import QApplication
            from app.ui.theme import load_theme
            app = QApplication.instance()
            if app is not None:
                load_theme(app, theme=mode)  # type: ignore[arg-type]
                log.info("theme switch — mode=%s", mode)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("theme reload graceful 실패 — %r", exc)
        # cycle 154.3 — persist theme preference (사용자 재실행 시점 복원 chain)
        try:
            from app.config.user_preferences import save_user_theme_preference
            save_user_theme_preference(mode)  # type: ignore[attr-defined]
        except (ImportError, AttributeError) as exc:  # pragma: no cover - graceful
            log.debug("theme persist 부재 graceful — %r", exc)

    def set_active_mode(self, mode: str) -> None:
        """외부 단 active mode 설정 — programmatic switch."""
        if mode in self._buttons:
            self._buttons[mode].setChecked(True)

    def active_mode(self) -> str:
        """현 active mode 반환."""
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return "auto"
