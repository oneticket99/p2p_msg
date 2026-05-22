# SPDX-License-Identifier: GPL-3.0-or-later
"""사용자 sound preference dataclass + JSON persist (cycle 132 skeleton).

한글 주석 — 사용자 directive 2026-05-18 (signature sound) 의 직접 토글 옵션:
  - option: 6 chiptune 안 하나 (default "ppyong" — 뿅)
  - volume: 0.0~1.0 cap
  - muted: 음소거 토글

JSON persist 경로 = ``~/.tootalk/sound_preferences.json`` (XDG 대안 부재 환경 폴백).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from app.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
from app.sound import DEFAULT_OPTION, SIGNATURE_OPTIONS

log = logging.getLogger(__name__)

# 한글 주석 — JSON persist 의 default 경로 (사용자 home 디렉토리 의 hidden dir)
DEFAULT_PREF_PATH = Path.home() / ".tootalk" / "sound_preferences.json"
# 한글 주석 — locale preference JSON persist 경로 (cycle 134 신설)
DEFAULT_LOCALE_PREF_PATH = Path.home() / ".tootalk" / "locale_preferences.json"
# 한글 주석 — theme preference JSON persist 경로 (cycle 155 신설)
DEFAULT_THEME_PREF_PATH = Path.home() / ".tootalk" / "theme_preferences.json"

# 한글 주석 — 3 mode (dark / light / auto) 만 허용
SUPPORTED_THEMES = ("dark", "light", "auto")
DEFAULT_THEME = "dark"  # cycle 169.471 — 야간 모드 default (사용자 directive)


@dataclass(slots=True)
class UserSoundPreferences:
    """사용자 signature sound 설정 dataclass — JSON persist 의무.

    Attributes
    ----------
    option : str
        6 chiptune 옵션 안 하나 — ``SIGNATURE_OPTIONS`` 의 key. 부재 시 default ppyong.
    volume : float
        볼륨 0.0~1.0 cap — UI 슬라이더 매핑.
    muted : bool
        음소거 토글 — True 시 play() 차단.
    """

    option: str = DEFAULT_OPTION
    volume: float = 0.7
    muted: bool = False

    def __post_init__(self) -> None:
        # 한글 주석 — 6 옵션 외 부재 의 option 자동 폴백 + volume 의 cap
        if self.option not in SIGNATURE_OPTIONS:
            log.warning(
                "[pref] option=%r 부재 — default %s 폴백",
                self.option,
                DEFAULT_OPTION,
            )
            self.option = DEFAULT_OPTION
        self.volume = max(0.0, min(1.0, float(self.volume)))
        self.muted = bool(self.muted)

    def to_dict(self) -> dict:
        # 한글 주석 — JSON serialize 용 dict 변환
        return asdict(self)


def load_user_sound_preferences(
    path: Optional[Path] = None,
) -> UserSoundPreferences:
    """JSON 파일 경유 사용자 sound preference 로딩 — 부재 시 default 반환.

    Parameters
    ----------
    path : Path | None
        명시적 JSON 경로. None 이면 ``DEFAULT_PREF_PATH`` 사용.
    """

    pref_path = path or DEFAULT_PREF_PATH
    if not pref_path.is_file():
        log.info("[pref] %s 부재 — default UserSoundPreferences 반환", pref_path)
        return UserSoundPreferences()
    try:
        raw = json.loads(pref_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("[pref] %s 로딩 실패 — %r → default 폴백", pref_path, exc)
        return UserSoundPreferences()
    # 한글 주석 — dict 안 알려진 key 만 추출 (forward-compat 의 unknown key 무시)
    return UserSoundPreferences(
        option=str(raw.get("option", DEFAULT_OPTION)),
        volume=float(raw.get("volume", 0.7)),
        muted=bool(raw.get("muted", False)),
    )


def save_user_sound_preferences(
    pref: UserSoundPreferences,
    path: Optional[Path] = None,
) -> bool:
    """사용자 sound preference JSON persist — 디렉토리 부재 시 자동 생성.

    Returns
    -------
    bool
        성공 시 True, IO 실패 시 False.
    """

    pref_path = path or DEFAULT_PREF_PATH
    try:
        pref_path.parent.mkdir(parents=True, exist_ok=True)
        pref_path.write_text(
            json.dumps(pref.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        log.warning("[pref] %s 저장 실패 — %r", pref_path, exc)
        return False


@dataclass(slots=True)
class UserLocalePreferences:
    """사용자 locale 설정 dataclass — JSON persist 의무 (cycle 134 신설).

    Attributes
    ----------
    locale : str
        5 locale (``ko``, ``en``, ``zh-CN``, ``zh-TW``, ``ja``) 안 하나.
        부재/unsupported 의 default 폴백 = ``ko``.
    """

    locale: str = DEFAULT_LOCALE

    def __post_init__(self) -> None:
        # 한글 주석 — 5 locale 외 부재 시 default ko 폴백
        if self.locale not in SUPPORTED_LOCALES:
            log.warning(
                "[pref] locale=%r unsupported — default %s 폴백",
                self.locale,
                DEFAULT_LOCALE,
            )
            self.locale = DEFAULT_LOCALE

    def to_dict(self) -> dict:
        # 한글 주석 — JSON serialize 용 dict 변환
        return asdict(self)


def load_user_locale_preferences(
    path: Optional[Path] = None,
) -> UserLocalePreferences:
    """JSON 파일 경유 locale preference 로딩 — 부재 시 default ko 반환.

    Parameters
    ----------
    path : Path | None
        명시적 JSON 경로. None 이면 ``DEFAULT_LOCALE_PREF_PATH`` 사용.
    """

    pref_path = path or DEFAULT_LOCALE_PREF_PATH
    if not pref_path.is_file():
        log.info(
            "[pref] %s 부재 — default UserLocalePreferences (ko) 반환",
            pref_path,
        )
        return UserLocalePreferences()
    try:
        raw = json.loads(pref_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning(
            "[pref] %s 로딩 실패 — %r → default 폴백",
            pref_path,
            exc,
        )
        return UserLocalePreferences()
    # 한글 주석 — dict 안 알려진 key 만 추출 (forward-compat 의 unknown key 무시)
    return UserLocalePreferences(
        locale=str(raw.get("locale", DEFAULT_LOCALE)),
    )


def save_user_locale_preferences(
    pref: UserLocalePreferences,
    path: Optional[Path] = None,
) -> bool:
    """locale preference JSON persist — 디렉토리 부재 시 자동 생성.

    Returns
    -------
    bool
        성공 시 True, IO 실패 시 False.
    """

    pref_path = path or DEFAULT_LOCALE_PREF_PATH
    try:
        pref_path.parent.mkdir(parents=True, exist_ok=True)
        pref_path.write_text(
            json.dumps(pref.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        log.warning("[pref] %s 저장 실패 — %r", pref_path, exc)
        return False


def load_user_theme_preference(path: Optional[Path] = None) -> str:
    """JSON 경유 theme preference 로딩 — 부재 시 default 'auto' 반환 (cycle 155 신설).

    Returns
    -------
    str
        'dark' / 'light' / 'auto' 안 하나.
    """
    pref_path = path or DEFAULT_THEME_PREF_PATH
    if not pref_path.is_file():
        return DEFAULT_THEME
    try:
        raw = json.loads(pref_path.read_text(encoding="utf-8"))
        mode = str(raw.get("theme", DEFAULT_THEME))
        if mode not in SUPPORTED_THEMES:
            log.warning("[pref] theme=%r unsupported — %s 폴백", mode, DEFAULT_THEME)
            return DEFAULT_THEME
        return mode
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("[pref] theme load 실패 — %r → %s 폴백", exc, DEFAULT_THEME)
        return DEFAULT_THEME


def save_user_theme_preference(theme: str, path: Optional[Path] = None) -> bool:
    """theme preference JSON persist (cycle 155 신설).

    Parameters
    ----------
    theme : str
        'dark' / 'light' / 'auto' 안 하나. 외 부재 시 default 폴백.
    """
    if theme not in SUPPORTED_THEMES:
        log.warning("[pref] theme=%r unsupported — %s 폴백 저장", theme, DEFAULT_THEME)
        theme = DEFAULT_THEME
    pref_path = path or DEFAULT_THEME_PREF_PATH
    try:
        pref_path.parent.mkdir(parents=True, exist_ok=True)
        pref_path.write_text(
            json.dumps({"theme": theme}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        log.warning("[pref] theme 저장 실패 — %r", exc)
        return False
