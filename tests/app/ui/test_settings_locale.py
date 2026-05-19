# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.settings_locale`` 단위 테스트 (cycle 134).

Phase 5 Item 1 i18n actual binding — 5 locale dropdown + apply_locale_runtime
+ UserLocalePreferences round-trip 검증. PyQt6 부재 환경 의 graceful 분기 검증.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config.user_preferences import (
    UserLocalePreferences,
    load_user_locale_preferences,
    save_user_locale_preferences,
)
from app.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
from app.ui.settings_locale import (
    LOCALE_LABELS,
    LocaleSettingsDialog,
    apply_locale_runtime,
)


class TestLocaleSettingsDialogInit:
    """LocaleSettingsDialog 초기화 검증 (PyQt6 부재 graceful)."""

    def test_default_ko_init(self) -> None:
        # 한글 주석 — PyQt6 부재 환경 default ko 의 graceful 인스턴스
        with patch("app.ui.settings_locale._PYQT_AVAILABLE", False):
            dlg = LocaleSettingsDialog(current_locale=DEFAULT_LOCALE)
            assert dlg.current_locale == "ko"
            assert dlg.selected_locale == "ko"

    def test_custom_locale_init(self) -> None:
        # 한글 주석 — PyQt6 부재 환경 custom locale 의 graceful 인스턴스
        with patch("app.ui.settings_locale._PYQT_AVAILABLE", False):
            dlg = LocaleSettingsDialog(current_locale="ja")
            assert dlg.current_locale == "ja"
            assert dlg.selected_locale == "ja"


class TestApplyLocaleRuntime:
    """apply_locale_runtime — install_qt_translator wrap 검증."""

    def test_pyqt_absent_graceful_false(self) -> None:
        # 한글 주석 — PyQt6 부재 graceful False 폴백
        with patch("app.ui.settings_locale._PYQT_AVAILABLE", False):
            result = apply_locale_runtime(MagicMock(), "ko")
            assert result is False

    def test_install_qt_translator_success(self) -> None:
        # 한글 주석 — install_qt_translator mock True 의 통과
        with patch("app.ui.settings_locale._PYQT_AVAILABLE", True):
            with patch(
                "app.ui.settings_locale.install_qt_translator",
                return_value=True,
            ) as mock_install:
                result = apply_locale_runtime(MagicMock(), "en")
                assert result is True
                mock_install.assert_called_once()

    def test_unsupported_locale_skip(self) -> None:
        # 한글 주석 — 5 locale 외 의 unsupported locale 의 graceful False
        with patch("app.ui.settings_locale._PYQT_AVAILABLE", True):
            result = apply_locale_runtime(MagicMock(), "fr")
            assert result is False


class TestUserLocalePreferences:
    """UserLocalePreferences dataclass + JSON persist round-trip."""

    def test_default_locale_ko(self) -> None:
        # 한글 주석 — default 인스턴스 의 locale ko
        pref = UserLocalePreferences()
        assert pref.locale == "ko"

    def test_unsupported_locale_fallback(self) -> None:
        # 한글 주석 — unsupported locale 의 default ko 자동 폴백
        pref = UserLocalePreferences(locale="fr")
        assert pref.locale == "ko"

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        # 한글 주석 — JSON persist round-trip 검증 (en 저장 → en 로딩)
        pref_path = tmp_path / "locale.json"
        pref = UserLocalePreferences(locale="en")
        ok = save_user_locale_preferences(pref, path=pref_path)
        assert ok is True
        loaded = load_user_locale_preferences(path=pref_path)
        assert loaded.locale == "en"


class TestLocaleLabels:
    """5 locale label 매핑 검증."""

    def test_all_locales_labeled(self) -> None:
        # 한글 주석 — 5 locale 전수 의 label 매핑 존재
        for loc in SUPPORTED_LOCALES:
            assert loc in LOCALE_LABELS

    def test_ko_label_korean(self) -> None:
        # 한글 주석 — ko label 의 "한국어"
        assert LOCALE_LABELS["ko"] == "한국어"
