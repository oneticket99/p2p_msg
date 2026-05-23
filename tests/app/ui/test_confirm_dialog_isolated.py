# SPDX-License-Identifier: GPL-3.0-or-later
"""ConfirmDialog isolated unit test — cycle 169.708 신설."""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestConfirmDialogConstruct:
    def test_question_mode_default(self, qapp) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("TooTalk", "Are you sure?", raw_text=True)
        assert d._mode == "question"
        assert d.windowTitle() == "TooTalk"
        d.close()

    def test_info_mode(self, qapp) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("Info", "msg", raw_text=True, mode="info")
        assert d._mode == "info"
        d.close()

    def test_warning_mode(self, qapp) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("Warning", "msg", raw_text=True, mode="warning")
        assert d._mode == "warning"
        d.close()

    def test_critical_mode(self, qapp) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("Critical", "msg", raw_text=True, mode="critical")
        assert d._mode == "critical"
        d.close()

    def test_unknown_mode_falls_back_to_question(self, qapp) -> None:
        # 한글 주석 — unknown mode → question default fallback
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("X", "Y", raw_text=True, mode="bogus")
        assert d._mode == "question"
        d.close()


class TestConfirmDialogFixedSize:
    def test_size_420x220(self, qapp) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        d = ConfirmDialog("X", "Y", raw_text=True)
        assert d.width() == 420
        assert d.height() == 220
        d.close()


class TestModeColorsTable:
    def test_4_modes_defined(self) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        assert "question" in ConfirmDialog._MODE_COLORS
        assert "info" in ConfirmDialog._MODE_COLORS
        assert "warning" in ConfirmDialog._MODE_COLORS
        assert "critical" in ConfirmDialog._MODE_COLORS

    def test_question_uses_toonation_blue(self) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        primary, hover = ConfirmDialog._MODE_COLORS["question"]
        # 한글 주석 — Toonation BI 색 — 0066FF
        assert primary == "#0066FF"

    def test_critical_uses_red(self) -> None:
        from app.ui.confirm_dialog import ConfirmDialog

        primary, _ = ConfirmDialog._MODE_COLORS["critical"]
        assert primary == "#EF4444"
