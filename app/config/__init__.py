# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk user-facing preference 모듈 — JSON persist 기반.

한글 주석 — 본 패키지 는 사용자 의 직접 토글 가능 한 preference (signature sound 등) 의
JSON persist 의무. ``app.core.config`` 의 환경 설정 (DB / signaling 등) 과 분리한다.
cycle 132 signature sound skeleton 의 신설 ([[project-signature-sound]] 정합).
"""

from app.config.user_preferences import (
    UserSoundPreferences,
    load_user_sound_preferences,
    save_user_sound_preferences,
)

__all__ = [
    "UserSoundPreferences",
    "load_user_sound_preferences",
    "save_user_sound_preferences",
]
