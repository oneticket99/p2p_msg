# SPDX-License-Identifier: GPL-3.0-or-later
"""apply_locale_runtime + i18n install unit — cycle 169.711 신설."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("PyQt6")


class TestApplyLocaleRuntime:
    def test_unsupported_locale_returns_false(self) -> None:
        from app.ui.settings_locale import apply_locale_runtime

        app_mock = MagicMock()
        result = apply_locale_runtime(app_mock, "xx-INVALID")
        assert result is False

    def test_supported_locale_dispatches(self) -> None:
        from app.ui import settings_locale

        with patch.object(
            settings_locale, "install_qt_translator", return_value=True,
        ) as fake_install:
            app_mock = MagicMock()
            result = settings_locale.apply_locale_runtime(app_mock, "en")
            assert result is True
            fake_install.assert_called_once()


class TestSupportedLocales:
    def test_5_locales_defined(self) -> None:
        from app.i18n import SUPPORTED_LOCALES

        assert "ko" in SUPPORTED_LOCALES
        assert "en" in SUPPORTED_LOCALES
        assert "zh-CN" in SUPPORTED_LOCALES
        assert "zh-TW" in SUPPORTED_LOCALES
        assert "ja" in SUPPORTED_LOCALES

    def test_default_locale_ko(self) -> None:
        from app.i18n import DEFAULT_LOCALE

        assert DEFAULT_LOCALE == "ko"


class TestInstallQtTranslator:
    def test_invalid_locale_returns_false(self) -> None:
        # 한글 주석 — unsupported locale → install fail
        from app.i18n import install_qt_translator

        app_mock = MagicMock()
        result = install_qt_translator(app_mock, locale="bogus")
        assert result is False
