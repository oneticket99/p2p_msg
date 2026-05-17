# SPDX-License-Identifier: GPL-3.0-or-later
"""시그니처 사운드 재생 — PyQt6 ``QSoundEffect`` 경량 wrapper.

사용자 directive (2026-05-17) — Telegram/KakaoTalk 의 메시지 수신 "뿅"
신호음 등가 기능. ``project_signature_sound.md`` 영구 메모리 정합.

설계 결정
---------
- ``QSoundEffect`` 선택 = WAV 짧은 파일 (< 1 MB) 의 low-latency one-shot
  재생 적합. ``QMediaPlayer`` 대비 dependency 가 적고 ``QApplication``
  부재 환경에서도 import 자체는 가능 (단 실 재생은 Qt event loop 의무).
- ``Config.sound_enabled`` False = 즉시 단 미재생. 매 재생 호출 직전
  검사로 토글 즉시 반영.
- ``Config.sound_volume`` 0.0~1.0 범위 — ``Config`` 단계에서 이미 clamp
  되었으나 본 wrapper 도 이중 clamp 으로 방어.
- WAV 경로 = 저장소 루트 기준 상대경로 — ``Path.cwd()`` 결합.
  배포 빌드 (PyInstaller) 환경 = ``sys._MEIPASS`` 경로 별도 처리 의무
  (Phase 3 빌드 cycle 의무).

Thread safety
-------------
PyQt6 의 ``QSoundEffect`` = GUI thread 전용. asyncio 의 다른 thread 의
호출 = ``QTimer.singleShot`` 또는 ``QMetaObject.invokeMethod`` 경유 의무.
본 wrapper 의 ``play()`` 는 GUI thread 의 직접 호출만 안전.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

# Qt import 는 선택 — 테스트 환경에서 PyQt6 부재 시 wrapper logic 만 검증
try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtMultimedia import QSoundEffect
    _QT_AVAILABLE = True
except ImportError:  # pragma: no cover - PyQt6 미설치 환경 폴백
    QUrl = None  # type: ignore[assignment, misc]
    QSoundEffect = None  # type: ignore[assignment, misc]
    _QT_AVAILABLE = False

from app.core.config import Config

log = logging.getLogger(__name__)


def _clamp_volume(volume: float) -> float:
    """0.0~1.0 범위로 clamp — 이중 방어."""

    if volume < 0.0:
        return 0.0
    if volume > 1.0:
        return 1.0
    return volume


def resolve_sound_path(config: Config, repo_root: Optional[Path] = None) -> Path:
    """``config.sound_signature_path`` 의 절대 경로 해석.

    Parameters
    ----------
    config : Config
        ``sound_signature_path`` 필드 보유 (상대 경로).
    repo_root : Path | None
        저장소 루트. None 이면 ``Path.cwd()`` 사용.

    Returns
    -------
    Path
        절대 경로. 파일 존재 여부는 확인하지 않음 — caller 의무.
    """

    root = repo_root if repo_root is not None else Path.cwd()
    rel = Path(config.sound_signature_path)
    if rel.is_absolute():
        return rel
    return (root / rel).resolve()


class SoundPlayer:
    """시그니처 사운드 재생 wrapper.

    ``Config`` 객체를 받아 PyQt6 ``QSoundEffect`` 인스턴스를 lazy-init
    하고 ``play_signature()`` 메서드로 재생을 트리거한다. 음소거/볼륨
    변경은 ``set_enabled()`` / ``set_volume()`` 으로 즉시 반영된다.

    PyQt6 부재 환경 (CI test 의 의무 의무) = ``play_signature()`` no-op,
    ``is_qt_available()`` False 반환.
    """

    def __init__(self, config: Config, repo_root: Optional[Path] = None) -> None:
        self._enabled: bool = config.sound_enabled
        self._volume: float = _clamp_volume(config.sound_volume)
        self._sound_path: Path = resolve_sound_path(config, repo_root=repo_root)
        self._effect: Optional["QSoundEffect"] = None

        if _QT_AVAILABLE and self._sound_path.exists():
            self._init_effect()
        elif not self._sound_path.exists():
            log.warning(
                "시그니처 사운드 파일 부재 — path=%s (미재생 폴백)",
                self._sound_path,
            )

    def _init_effect(self) -> None:
        """``QSoundEffect`` 인스턴스 초기화. PyQt6 + 파일 존재 시만 호출."""

        assert _QT_AVAILABLE, "Qt 부재 환경 의 _init_effect 호출 = 내부 오류"
        self._effect = QSoundEffect()
        self._effect.setSource(QUrl.fromLocalFile(str(self._sound_path)))
        self._effect.setVolume(self._volume)
        self._effect.setLoopCount(1)

    def play_signature(self) -> bool:
        """시그니처 사운드 재생 트리거.

        Returns
        -------
        bool
            실 재생 시도 = True, 음소거/Qt부재/파일부재 = False.
        """

        if not self._enabled:
            log.debug("시그니처 사운드 음소거 상태 — 재생 skip")
            return False
        if not _QT_AVAILABLE:
            log.debug("PyQt6 부재 — 재생 skip")
            return False
        if self._effect is None:
            log.debug("QSoundEffect 미초기화 — 재생 skip")
            return False
        self._effect.play()
        return True

    def set_enabled(self, enabled: bool) -> None:
        """음소거 토글 — 다음 ``play_signature()`` 부터 반영."""

        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        """볼륨 변경 — 0.0~1.0 clamp + ``QSoundEffect`` 동기."""

        self._volume = _clamp_volume(volume)
        if self._effect is not None:
            self._effect.setVolume(self._volume)

    @property
    def enabled(self) -> bool:
        """현재 음소거 상태 — ``True`` = 재생 활성."""

        return self._enabled

    @property
    def volume(self) -> float:
        """현재 볼륨 (0.0~1.0)."""

        return self._volume

    @property
    def sound_path(self) -> Path:
        """시그니처 사운드 파일 절대 경로 (read-only)."""

        return self._sound_path

    @staticmethod
    def is_qt_available() -> bool:
        """PyQt6 ``QSoundEffect`` import 가능 여부."""

        return _QT_AVAILABLE
