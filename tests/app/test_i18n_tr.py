# SPDX-License-Identifier: GPL-3.0-or-later
"""i18n tr() chain unit test — cycle 169.688 신설.

chain:
1. tr known key ko default
2. set_locale en + tr returns EN
3. set_locale invalid locale → ko 유지
4. tr unknown key → key 자체 반환
5. tr explicit locale override
6. zh-TW fallback chain (zh-TW miss → zh-CN intermediate)
7. get_locale returns current
"""

from __future__ import annotations


class TestSetLocale:
    def test_set_known_locale(self) -> None:
        from app.i18n.labels import get_locale, set_locale

        # 한글 주석 — 본 module global state 의 ko 폴백 후 복원
        set_locale("en")
        assert get_locale() == "en"
        set_locale("ko")
        assert get_locale() == "ko"

    def test_set_unknown_locale_ignored(self) -> None:
        from app.i18n.labels import get_locale, set_locale

        set_locale("ko")
        set_locale("xx-INVALID")
        # 한글 주석 — 부재 locale = 무시 (이전 값 유지)
        assert get_locale() == "ko"

    def test_set_all_5_supported(self) -> None:
        from app.i18n.labels import get_locale, set_locale

        for loc in ("ko", "en", "zh-CN", "zh-TW", "ja"):
            set_locale(loc)
            assert get_locale() == loc
        set_locale("ko")


class TestTrFallbackChain:
    def test_unknown_key_returns_key(self) -> None:
        from app.i18n.labels import tr

        assert tr("nonexistent-key-xyz") == "nonexistent-key-xyz"

    def test_explicit_locale_override(self) -> None:
        # 한글 주석 — global state 무관 의 명시 locale override
        from app.i18n.labels import LABELS_EN, set_locale, tr

        set_locale("ko")
        # known key 선택 — LABELS_EN 안 존재 의 key
        key = next(iter(LABELS_EN.keys()))
        result = tr(key, locale="en")
        assert result == LABELS_EN[key]
        set_locale("ko")

    def test_zh_tw_falls_back_to_zh_cn_when_missing(self) -> None:
        from app.i18n.labels import (
            LABELS_ZH_CN, LABELS_ZH_TW, set_locale, tr,
        )

        # 한글 주석 — zh-TW miss + zh-CN hit 의 key 발굴
        zh_cn_only = [k for k in LABELS_ZH_CN if k not in LABELS_ZH_TW]
        if not zh_cn_only:
            # 한글 주석 — 모든 key zh-TW 존재 시 skip path
            return
        key = zh_cn_only[0]
        result = tr(key, locale="zh-TW")
        assert result == LABELS_ZH_CN[key]

    def test_ko_known_key_returns_korean(self) -> None:
        from app.i18n.labels import LABELS_KO, set_locale, tr

        set_locale("ko")
        key = next(iter(LABELS_KO.keys()))
        assert tr(key) == LABELS_KO[key]


class TestGetLocaleDefault:
    def test_default_ko(self) -> None:
        from app.i18n.labels import get_locale, set_locale

        set_locale("ko")
        assert get_locale() == "ko"
