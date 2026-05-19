# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Phase 5 cycle 133 — .ts 5 locale 의 XML schema + 20 message 검증 5 test."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# 한글 주석 — 5 locale + 20 source message 의 정본 기준
TS_DIR = Path(__file__).resolve().parents[2] / "app" / "i18n" / "translations"
LOCALES = ("ko", "en", "zh-CN", "zh-TW", "ja")
EXPECTED_SOURCES = (
    "로그인",
    "회원가입",
    "비밀번호",
    "확인",
    "취소",
    "보내기",
    "원격 제어 요청",
    "친구 추가",
    "설정",
    "메시지",
    "파일 전송",
    "이미지",
    "이모지",
    "차단",
    "신고",
    "검색",
    "전체 메시지",
    "온라인",
    "오프라인",
    "연결 중",
)
# 한글 주석 — 영문 base translation 의 핵심 fragment (en 만 별도 sanity)
EXPECTED_EN_FRAGMENTS = {
    "로그인": "Login",
    "회원가입": "Sign up",
    "비밀번호": "Password",
    "보내기": "Send",
    "원격 제어 요청": "Request remote control",
    "오프라인": "Offline",
}


class TestTsFiles:
    @pytest.mark.parametrize("locale", LOCALES)
    def test_ts_file_exists_and_parses(self, locale: str) -> None:
        # 한글 주석 — 각 locale .ts 의 존재 + XML parse PASS
        ts_path = TS_DIR / f"tootalk_{locale}.ts"
        assert ts_path.is_file(), f"ts 파일 부재 — {ts_path}"
        tree = ET.parse(ts_path)
        root = tree.getroot()
        assert root.tag == "TS"
        assert root.get("version") == "2.1"

    @pytest.mark.parametrize("locale", LOCALES)
    def test_ts_has_20_message_entries(self, locale: str) -> None:
        # 한글 주석 — 각 locale .ts 의 message 20 entry 정확 매칭
        ts_path = TS_DIR / f"tootalk_{locale}.ts"
        root = ET.parse(ts_path).getroot()
        messages = root.findall(".//message")
        assert len(messages) == 20, f"{locale} message {len(messages)} 건 (기대 20)"

    @pytest.mark.parametrize("locale", LOCALES)
    def test_ts_sources_match_expected(self, locale: str) -> None:
        # 한글 주석 — 20 source 의 한글 원문 동일 (모든 locale 의 source = ko base)
        ts_path = TS_DIR / f"tootalk_{locale}.ts"
        root = ET.parse(ts_path).getroot()
        sources = [m.findtext("source") for m in root.findall(".//message")]
        assert sources == list(EXPECTED_SOURCES), (
            f"{locale} source list mismatch — got={sources}"
        )

    @pytest.mark.parametrize("locale", LOCALES)
    def test_ts_translations_non_empty(self, locale: str) -> None:
        # 한글 주석 — translation 의 빈 값 차단 (skeleton 이지만 모든 entry 채움)
        ts_path = TS_DIR / f"tootalk_{locale}.ts"
        root = ET.parse(ts_path).getroot()
        for message in root.findall(".//message"):
            src = message.findtext("source") or ""
            trans = message.findtext("translation") or ""
            assert trans.strip(), f"{locale}:{src} translation 부재"

    def test_en_translation_fragments(self) -> None:
        # 한글 주석 — en locale 의 핵심 영문 매핑 sanity
        ts_path = TS_DIR / "tootalk_en.ts"
        root = ET.parse(ts_path).getroot()
        mapping = {
            m.findtext("source"): m.findtext("translation")
            for m in root.findall(".//message")
        }
        for src, expected in EXPECTED_EN_FRAGMENTS.items():
            assert mapping.get(src) == expected, (
                f"en[{src}] = {mapping.get(src)!r} (기대 {expected!r})"
            )
