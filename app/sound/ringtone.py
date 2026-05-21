# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 통화 사운드 player — cycle 169.91 신설.

사용자 directive 2026-05-20 — "통화 시에는 통화 연결음 사운드를 만들어야해".

지원:
    ringback  — outgoing 호출 시 loop 재생 (상대 응답 대기)
    ringtone  — incoming 통화 수신 시 loop 재생 (사용자 수락/거절 대기)
    connect   — 통화 connect 시점 1회 재생
    end       — 통화 종료 시점 1회 재생

PyQt6.QtMultimedia QSoundEffect 부재 graceful skip (CI Linux runner 부재 대응).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# 한글 주석 — Qt import optional — PyQt6 부재 시 graceful
try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtMultimedia import QSoundEffect
    _QT_AVAILABLE = True
except ImportError:
    QUrl = None  # type: ignore
    QSoundEffect = None  # type: ignore
    _QT_AVAILABLE = False


# cycle 169.309 — 사용자 directive wav v3 binding (messenger_voice_call_sounds_v3)
# description 부재 (07/08/09) → 제외. connect/end key retain 但 None (graceful skip).
CALL_SOUNDS = {
    "ringback": "01_outgoing_call_melodic_fast_loop_12s.wav",
    "ringtone": "05_incoming_call_ringtone_extra_fast_loop_15s.wav",
    # 한글 주석 — 03_outgoing_call_cute_melodic_fast_loop_12s.wav = 귀여운 variant (사용자 선택 옵션)
    "ringback_cute": "03_outgoing_call_cute_melodic_fast_loop_12s.wav",
    # cycle 169.336 — 사용자 directive 07/08/09 wav binding
    "connect": "07_call_connected_chime.wav",
    "end": "08_call_ended_soft.wav",
    "failed": "09_call_failed_or_busy.wav",
}


class CallSoundPlayer:
    """통화 사운드 단일 player — loop / one-shot 동시 지원.

    Attributes
    ----------
    volume : float
        0.0~1.0 — 통화음 권장 0.5~0.7 (signature sound 대비 음량 낮춤).
    muted : bool
        사용자 mute toggle — True 시 play 호출 시점 silent skip.
    """

    def __init__(self, volume: float = 0.6, muted: bool = False) -> None:
        self.volume = max(0.0, min(1.0, volume))
        self.muted = muted
        self._effects: dict[str, object] = {}
        self._current_loop: Optional[str] = None
        if _QT_AVAILABLE:
            self._init_effects()

    def _resolve_wav_dir(self) -> Path:
        """WAV directory 해석 — app/sound/wav/ + PyInstaller _MEIPASS 폴백."""
        import sys
        # PyInstaller frozen — sys._MEIPASS root
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / "app" / "sound" / "wav"
            if candidate.exists():
                return candidate
        # 개발 환경 — 저장소 루트 + app/sound/wav
        return Path(__file__).resolve().parent / "wav"

    def _init_effects(self) -> None:
        """4 QSoundEffect instance 사전 load — play() 시점 latency 최소화."""
        wav_dir = self._resolve_wav_dir()
        for key, fname in CALL_SOUNDS.items():
            path = wav_dir / fname
            if not path.exists():
                log.warning("[CallSoundPlayer] WAV 부재 — %s (key=%s) → skip", path, key)
                continue
            try:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self.volume)
                self._effects[key] = effect
            except Exception as exc:
                log.warning("[CallSoundPlayer] %s init fail — %r", key, exc)

    def play_loop(self, key: str) -> None:
        """ringback / ringtone loop 재생 — 이전 loop 자동 stop."""
        if self.muted or not _QT_AVAILABLE:
            return
        self.stop_loop()
        effect = self._effects.get(key)
        if effect is None:
            return
        try:
            # cycle 169.335 — PyQt6 의 setLoopCount(int) expected — Loop.Infinite enum value 의 int convert
            try:
                infinite_value = int(QSoundEffect.Loop.Infinite.value)  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                infinite_value = -2  # 한글 주석 — Qt6 QSoundEffect Infinite 의 magic int
            effect.setLoopCount(infinite_value)
            effect.setVolume(self.volume)
            effect.play()
            self._current_loop = key
            log.info("[CallSoundPlayer] loop start — %s", key)
        except Exception as exc:
            log.warning("[CallSoundPlayer] loop play fail — %s — %r", key, exc)

    def play_once(self, key: str) -> None:
        """connect / end 1회 재생."""
        if self.muted or not _QT_AVAILABLE:
            return
        effect = self._effects.get(key)
        if effect is None:
            return
        try:
            effect.setLoopCount(1)
            effect.setVolume(self.volume)
            effect.play()
            log.info("[CallSoundPlayer] one-shot — %s", key)
        except Exception as exc:
            log.warning("[CallSoundPlayer] play_once fail — %s — %r", key, exc)

    def stop_loop(self) -> None:
        """현재 loop 재생 중단 — 통화 connect / end 시점 호출 의무."""
        if self._current_loop is None or not _QT_AVAILABLE:
            return
        effect = self._effects.get(self._current_loop)
        if effect is not None:
            try:
                effect.stop()
                log.info("[CallSoundPlayer] loop stop — %s", self._current_loop)
            except Exception as exc:
                log.warning("[CallSoundPlayer] stop fail — %r", exc)
        self._current_loop = None

    def set_muted(self, muted: bool) -> None:
        """사용자 mute toggle — True 시 현재 loop 즉시 stop."""
        self.muted = muted
        if muted:
            self.stop_loop()

    def set_volume(self, volume: float) -> None:
        """volume 갱신 — 현재 loop 도 즉시 반영."""
        self.volume = max(0.0, min(1.0, volume))
        for effect in self._effects.values():
            try:
                effect.setVolume(self.volume)  # type: ignore[attr-defined]
            except Exception:
                pass
