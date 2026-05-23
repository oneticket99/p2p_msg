# SPDX-License-Identifier: GPL-3.0-or-later
"""CallSoundPlayer unit test — cycle 169.683 omit retain.

QSoundEffect 의존 부재 graceful + volume clamp + mute toggle.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    # 한글 주석 — QSoundEffect 의무 QApplication
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestCallSoundPlayerInit:
    def test_default_volume(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer()
        assert p.volume == 0.6
        assert p.muted is False
        assert p._current_loop is None

    def test_volume_clamped_high(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer(volume=2.5)
        assert p.volume == 1.0

    def test_volume_clamped_low(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer(volume=-0.3)
        assert p.volume == 0.0

    def test_muted_flag_preserved(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer(muted=True)
        assert p.muted is True


class TestCallSoundPlayerGuards:
    def test_muted_play_loop_noop(self, qapp) -> None:
        # 한글 주석 — muted=True → play_loop 즉시 return
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer(muted=True)
        p.play_loop("ringback")
        assert p._current_loop is None

    def test_muted_play_once_noop(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer(muted=True)
        # 한글 주석 — exception 차단 verify
        p.play_once("connect")

    def test_unknown_key_silent_skip(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer()
        # 한글 주석 — _effects dict 에 존재 부재 key → silent skip
        p.play_loop("nonexistent-key")
        assert p._current_loop is None

    def test_stop_loop_without_active(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer()
        # 한글 주석 — _current_loop=None 인 상태 의 stop_loop graceful
        p.stop_loop()
        assert p._current_loop is None


class TestResolveWavDir:
    def test_resolves_to_existing_path(self, qapp) -> None:
        from app.sound.ringtone import CallSoundPlayer

        p = CallSoundPlayer()
        wav_dir = p._resolve_wav_dir()
        # 한글 주석 — 개발 환경 = app/sound/wav 디렉토리 존재 의무
        assert wav_dir.name == "wav"
