# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk signature sound — PyQt6 QSoundEffect 기반 6 옵션 chiptune (cycle 132 skeleton).

사용자 directive 2026-05-18 — 메시지 수신 시 "뿅" signature sound.
PyQt6 QSoundEffect + WAV 200~400ms chiptune + 사용자 음소거 / volume / custom 옵션.
WAV 본격 생성은 Phase 2 후속 cycle 의 의무 — 본 cycle 은 skeleton + placeholder 의 한정.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# 한글 주석 — 6 옵션 chiptune WAV (200~400ms 단음 + 8-bit retro 풍)
SIGNATURE_OPTIONS = {
    "ppyong": "tootalk_ppyong.wav",       # default — 뿅 (사용자 directive 2026-05-18)
    "blip": "tootalk_blip.wav",            # 깔끔한 단음
    "ding": "tootalk_ding.wav",            # 종소리
    "chime": "tootalk_chime.wav",          # 차임벨 2음
    "pop": "tootalk_pop.wav",              # 풍선 터지는 소리
    "soft": "tootalk_soft.wav",            # 부드러운 알림
}
# 한글 주석 — default 옵션 = "뿅" (cognitive blind spot 보완 directive 정합)
DEFAULT_OPTION = "ppyong"


class SignatureSound:
    """signature sound player — QSoundEffect graceful + volume + 음소거.

    PyQt6.QtMultimedia 부재 시 graceful skip (CI Linux runner 의 PyQt6 부재 가능).
    WAV 파일 부재 시 graceful skip (placeholder 단계 + Phase 2 본격 생성 의무 안내).
    """

    def __init__(
        self,
        option: str = DEFAULT_OPTION,
        volume: float = 0.7,
        muted: bool = False,
    ) -> None:
        # 한글 주석 — option 부재 시 default ppyong 로 fallback + volume 0.0~1.0 cap
        self.option = option if option in SIGNATURE_OPTIONS else DEFAULT_OPTION
        self.volume = max(0.0, min(1.0, volume))
        self.muted = muted
        self._effect: Optional[object] = None
        self._init_qt_effect()

    def _resolve_wav_path(self) -> Optional[Path]:
        # 한글 주석 — WAV 경로 해석 + 부재 시 default ppyong 으로 폴백 (cycle 140)
        wav_dir = Path(__file__).parent / "wav"
        primary = wav_dir / SIGNATURE_OPTIONS[self.option]
        if primary.is_file():
            return primary
        # 한글 주석 — 선택한 옵션 의 WAV 부재 시 default ppyong 으로 자동 폴백
        fallback = wav_dir / SIGNATURE_OPTIONS[DEFAULT_OPTION]
        if fallback.is_file():
            log.warning(
                "[sound] WAV 부재 — %s — default(%s) 폴백",
                primary,
                DEFAULT_OPTION,
            )
            return fallback
        log.warning(
            "[sound] WAV + default 동시 부재 — %s (tools/generate_signature_sounds.py 실행 의무)",
            primary,
        )
        return None

    def _init_qt_effect(self) -> None:
        # 한글 주석 — PyQt6.QtMultimedia ImportError graceful + WAV 부재 graceful
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtMultimedia import QSoundEffect

            wav_path = self._resolve_wav_path()
            if wav_path is None:
                self._effect = None
                return
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(wav_path)))
            effect.setVolume(self.volume)
            self._effect = effect
        except ImportError:
            log.warning("[sound] PyQt6.QtMultimedia 부재 — graceful skip")
            self._effect = None

    def play(self) -> bool:
        # 한글 주석 — muted / effect None / WAV 부재 시 graceful False 반환
        if self.muted or self._effect is None:
            return False
        try:
            self._effect.play()  # type: ignore[attr-defined]
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("[sound] play 실패 — %r", exc)
            return False

    def set_volume(self, volume: float) -> None:
        # 한글 주석 — 0.0~1.0 cap + QSoundEffect 의 setVolume 갱신
        self.volume = max(0.0, min(1.0, volume))
        if self._effect is not None:
            try:
                self._effect.setVolume(self.volume)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                log.warning("[sound] setVolume 실패 — %r", exc)

    def set_muted(self, muted: bool) -> None:
        # 한글 주석 — 음소거 토글 — effect 재초기화 차단 (state 만 갱신)
        self.muted = bool(muted)

    def set_option(self, option: str) -> None:
        # 한글 주석 — 6 옵션 외 부재 시 default fallback + effect 재초기화
        new_opt = option if option in SIGNATURE_OPTIONS else DEFAULT_OPTION
        if new_opt == self.option:
            return
        self.option = new_opt
        self._init_qt_effect()


def list_options() -> list[str]:
    """한글 주석 — 사용자 설정 UI 의 dropdown 의무 — 6 옵션 key 반환."""

    return list(SIGNATURE_OPTIONS.keys())
