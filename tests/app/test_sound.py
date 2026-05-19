# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.sound`` 의 단위 테스트 — cycle 132 signature sound skeleton 회귀.

DESIGN.md §10.1 정합 — 단위 테스트는 Qt 비의존 + WAV 부재 graceful 검증.
사용자 directive 2026-05-18 (signature sound) 의 6 옵션 + 음소거 + volume cap 정합.
"""

from __future__ import annotations

import pytest


class TestSignatureSoundInit:
    """SignatureSound 초기화 검증 — 3 case."""

    def test_default_option_ppyong(self) -> None:
        # 한글 주석 — option 인자 미지정 시 default ppyong 정합
        from app.sound import DEFAULT_OPTION, SignatureSound

        sig = SignatureSound()
        assert sig.option == DEFAULT_OPTION
        assert sig.option == "ppyong"

    def test_invalid_option_falls_back_to_default(self) -> None:
        # 한글 주석 — 6 옵션 외 부재 의 option 인자 = default ppyong 폴백
        from app.sound import DEFAULT_OPTION, SignatureSound

        sig = SignatureSound(option="nonexistent_option_xyz")
        assert sig.option == DEFAULT_OPTION

    def test_custom_option_blip(self) -> None:
        # 한글 주석 — 6 옵션 안 blip 명시 시 정상 적용
        from app.sound import SignatureSound

        sig = SignatureSound(option="blip")
        assert sig.option == "blip"


class TestSignatureSoundVolume:
    """SignatureSound 의 volume cap + muted state — 2 case."""

    def test_volume_cap_0_to_1(self) -> None:
        # 한글 주석 — volume 0.0 미만 / 1.0 초과 입력 의 clamp 검증
        from app.sound import SignatureSound

        sig_low = SignatureSound(volume=-0.5)
        assert sig_low.volume == 0.0

        sig_high = SignatureSound(volume=2.5)
        assert sig_high.volume == 1.0

        sig_mid = SignatureSound(volume=0.42)
        assert sig_mid.volume == pytest.approx(0.42)

        # 한글 주석 — set_volume 갱신 의 cap 동일 검증
        sig_mid.set_volume(99.0)
        assert sig_mid.volume == 1.0
        sig_mid.set_volume(-99.0)
        assert sig_mid.volume == 0.0

    def test_muted_state_default_false_toggle(self) -> None:
        # 한글 주석 — muted 기본 False + set_muted 토글 검증
        from app.sound import SignatureSound

        sig = SignatureSound()
        assert sig.muted is False
        sig.set_muted(True)
        assert sig.muted is True
        sig.set_muted(False)
        assert sig.muted is False


class TestSignatureSoundPlay:
    """SignatureSound.play() 의 graceful False — 2 case."""

    def test_muted_returns_false(self) -> None:
        # 한글 주석 — muted=True 시 play 의 effect 호출 차단 + False 반환
        from app.sound import SignatureSound

        sig = SignatureSound(muted=True)
        assert sig.play() is False

    def test_effect_none_returns_false(self) -> None:
        # 한글 주석 — PyQt6.QtMultimedia 부재 또는 WAV 부재 시 effect None + play False
        # WAV placeholder 단계 — cycle 132 skeleton 의 effect 부재 graceful 검증
        from app.sound import SignatureSound

        sig = SignatureSound()
        # 한글 주석 — 본 cycle 의 WAV 부재 = _effect None 으로 보장 (placeholder 만)
        # PyQt6 import 성공 + WAV 부재 + ImportError 의 3 경로 모두 False 의 보장
        if sig._effect is None:
            assert sig.play() is False
        else:
            # 한글 주석 — 환경 의 WAV 존재 가능성 — set_muted 강제 차단 후 검증
            sig.set_muted(True)
            assert sig.play() is False


def test_list_options_returns_six() -> None:
    # 한글 주석 — 사용자 설정 UI dropdown 의무 — 6 옵션 key list 반환
    from app.sound import SIGNATURE_OPTIONS, list_options

    options = list_options()
    assert len(options) == 6
    assert set(options) == set(SIGNATURE_OPTIONS.keys())
    assert "ppyong" in options
