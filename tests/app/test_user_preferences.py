# SPDX-License-Identifier: GPL-3.0-or-later
"""user_preferences unit test — cycle 169.681 omit 제거 path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestUserSoundPreferences:
    def test_default_init(self) -> None:
        from app.config.user_preferences import (
            DEFAULT_OPTION, UserSoundPreferences,
        )

        p = UserSoundPreferences()
        assert p.option == DEFAULT_OPTION
        assert p.volume == 0.7
        assert p.muted is False

    def test_volume_clamped_high(self) -> None:
        # 한글 주석 — volume > 1.0 cap to 1.0
        from app.config.user_preferences import UserSoundPreferences

        p = UserSoundPreferences(volume=2.5)
        assert p.volume == 1.0

    def test_volume_clamped_low(self) -> None:
        from app.config.user_preferences import UserSoundPreferences

        p = UserSoundPreferences(volume=-0.5)
        assert p.volume == 0.0

    def test_invalid_option_fallback(self) -> None:
        from app.config.user_preferences import (
            DEFAULT_OPTION, UserSoundPreferences,
        )

        p = UserSoundPreferences(option="invalid-foo")
        assert p.option == DEFAULT_OPTION

    def test_to_dict_serializable(self) -> None:
        from app.config.user_preferences import UserSoundPreferences

        p = UserSoundPreferences(volume=0.5, muted=True)
        d = p.to_dict()
        assert d["volume"] == 0.5
        assert d["muted"] is True


class TestLoadSaveSoundPreferences:
    def test_load_missing_returns_default(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            DEFAULT_OPTION, load_user_sound_preferences,
        )

        p = load_user_sound_preferences(tmp_path / "missing.json")
        assert p.option == DEFAULT_OPTION

    def test_load_invalid_json_returns_default(self, tmp_path: Path) -> None:
        from app.config.user_preferences import load_user_sound_preferences

        bad = tmp_path / "bad.json"
        bad.write_text("not json {{")
        p = load_user_sound_preferences(bad)
        assert p.volume == 0.7

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            UserSoundPreferences, load_user_sound_preferences,
            save_user_sound_preferences,
        )

        path = tmp_path / "pref.json"
        original = UserSoundPreferences(volume=0.3, muted=True)
        assert save_user_sound_preferences(original, path) is True
        loaded = load_user_sound_preferences(path)
        assert loaded.volume == 0.3
        assert loaded.muted is True


class TestUserLocalePreferences:
    def test_default_locale_ko(self) -> None:
        from app.config.user_preferences import (
            DEFAULT_LOCALE, UserLocalePreferences,
        )

        p = UserLocalePreferences()
        assert p.locale == DEFAULT_LOCALE

    def test_unsupported_locale_fallback(self) -> None:
        from app.config.user_preferences import (
            DEFAULT_LOCALE, UserLocalePreferences,
        )

        p = UserLocalePreferences(locale="xx-YY")
        assert p.locale == DEFAULT_LOCALE

    def test_save_load_locale_round_trip(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            UserLocalePreferences, load_user_locale_preferences,
            save_user_locale_preferences,
        )

        path = tmp_path / "locale.json"
        original = UserLocalePreferences(locale="en")
        assert save_user_locale_preferences(original, path) is True
        loaded = load_user_locale_preferences(path)
        assert loaded.locale == "en"


class TestUserThemePreference:
    def test_load_missing_returns_default(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            DEFAULT_THEME, load_user_theme_preference,
        )

        t = load_user_theme_preference(tmp_path / "missing.json")
        assert t == DEFAULT_THEME

    def test_save_and_load_theme(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            load_user_theme_preference, save_user_theme_preference,
        )

        path = tmp_path / "theme.json"
        assert save_user_theme_preference("light", path) is True
        assert load_user_theme_preference(path) == "light"

    def test_save_invalid_theme_fallback(self, tmp_path: Path) -> None:
        # 한글 주석 — unsupported 의 dark fallback
        from app.config.user_preferences import (
            DEFAULT_THEME, load_user_theme_preference, save_user_theme_preference,
        )

        path = tmp_path / "theme.json"
        save_user_theme_preference("neon-pink", path)
        assert load_user_theme_preference(path) == DEFAULT_THEME

    def test_load_unsupported_value_fallback(self, tmp_path: Path) -> None:
        from app.config.user_preferences import (
            DEFAULT_THEME, load_user_theme_preference,
        )

        path = tmp_path / "theme.json"
        path.write_text(json.dumps({"theme": "neon"}))
        assert load_user_theme_preference(path) == DEFAULT_THEME
