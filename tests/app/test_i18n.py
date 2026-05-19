# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 1 i18n entry skeleton 테스트 (cycle 131)."""
from __future__ import annotations
import pytest
from app.i18n import resolve_locale, SUPPORTED_LOCALES, DEFAULT_LOCALE
from server.auth.otp_templates import render_otp


class TestResolveLocale:
    def test_default_ko(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 한글 주석 — 환경변수 부재 default ko
        monkeypatch.delenv("LOCALE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        assert resolve_locale() == DEFAULT_LOCALE

    def test_env_en_us(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 한글 주석 — LANG=en_US.UTF-8 → en 정규화
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        monkeypatch.delenv("LOCALE", raising=False)
        assert resolve_locale() == "en"

    def test_unsupported_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 한글 주석 — fr_FR → fallback ko
        monkeypatch.setenv("LOCALE", "fr_FR.UTF-8")
        assert resolve_locale() == DEFAULT_LOCALE


class TestRenderOtp:
    @pytest.mark.parametrize("locale,purpose,fragment", [
        ("ko", "signup", "회원가입"),
        ("en", "signup", "Sign-up"),
        ("ja", "password_reset", "パスワード"),
    ])
    def test_locale_purpose_subject_fragment(self, locale: str, purpose: str, fragment: str) -> None:
        # 한글 주석 — 각 locale × purpose 의 subject fragment 검증
        subject, body = render_otp(locale, purpose, "123456")
        assert fragment in subject
        assert "123456" in body

    def test_unsupported_locale_fallback_ko(self) -> None:
        # 한글 주석 — unsupported locale → ko fallback
        subject, body = render_otp("fr", "signup", "654321")
        assert "회원가입" in subject
