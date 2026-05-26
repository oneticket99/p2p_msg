# SPDX-License-Identifier: GPL-3.0-or-later
"""Avatar fallback helper — nickname 앞글자 painter (cycle 169.248 신설).

사용자 directive (image #7 / #8 critique):
- avatar 이미지 설정 부재 시점 nickname 앞 1~2 글자 노출 (한글 2자 / 영문 2자 대문자)
- 단일 글자 nickname = 그대로
- 배경 = Toonation BI #0066FF (drawer + dialog + chat_list 통일)

usage:
    pixmap = make_initial_pixmap("guest", size=48)
    label.setPixmap(pixmap)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPixmap, QFont, QBrush, QColor

from app.ui.avatar_palette import palette_solid


def get_initials(name: str) -> str:
    """nickname → 앞 1~2 글자 (한글 2자 / 영문 2자 대문자 / 단일 글자 retain).

    Parameters
    ----------
    name : str
        nickname / username.

    Returns
    -------
    str
        한글 2자 또는 영문 2자 대문자. 단일 글자 retain. 부재 시 "?".
    """
    if not name:
        return "?"
    stripped = name.strip()
    if not stripped:
        return "?"
    first = stripped[0]
    # 한글 검사 (U+AC00 ~ U+D7A3 Hangul Syllables)
    is_korean = "가" <= first <= "힣"
    if len(stripped) == 1:
        return stripped.upper() if not is_korean else stripped
    if is_korean:
        return stripped[:2]
    return stripped[:2].upper()


def make_initial_pixmap(
    name: str,
    size: int = 48,
    bg_color: str | None = None,
    fg_color: str = "#ffffff",
) -> QPixmap:
    """nickname 앞글자 circle pixmap 생성.

    Parameters
    ----------
    name : str
        nickname.
    size : int
        pixmap 한 변 길이 (정원 diameter).
    bg_color : str | None
        circle 배경색. None default = avatar_palette.palette_solid(name) 의 7 telegram palette deterministic hash (사용자 directive cycle 169.249).
    fg_color : str
        text 색. default 흰색.

    Returns
    -------
    QPixmap
        size x size 의 transparent bg + circle filled + initials text 의 pixmap.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # circle bg — deterministic palette (사용자 directive cycle 169.249)
    actual_bg = bg_color if bg_color is not None else palette_solid(name)
    painter.setBrush(QBrush(QColor(actual_bg)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size, size)

    # initials text center
    initials = get_initials(name)
    font = QFont()
    # 한글 2글자 시점 font ~size * 0.40, 영문 2글자 시점 ~size * 0.42
    font.setPixelSize(int(size * 0.38) if len(initials) >= 2 else int(size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(fg_color))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()

    return pixmap


def make_avatar_pixmap(
    name: str,
    avatar_ref: str | None = None,
    size: int = 48,
) -> QPixmap:
    """표시용 avatar pixmap — avatar_ref 있으면 원형 이미지, 없으면 이니셜 fallback (M6 T-16).

    표시 전파 6곳의 단일 진입점. avatar_ref(서버 content-addressed)가 캐시 hit 면 원형
    이미지를, 아니면(부재·miss) ``make_initial_pixmap`` 이니셜을 즉시 돌려준다. 캐시 miss
    시점에는 내부적으로 1회 async fetch 가 trigger 되며, 완료 시 ``avatar_cache().avatar_ready``
    signal 로 위젯이 재렌더한다(progressive enhancement). 따라서 호출부는 동기로 안전하다.

    Parameters
    ----------
    name : str
        이니셜 fallback 용 표시명(avatar_ref 부재/미캐시 시).
    avatar_ref : str | None
        서버 avatar 참조 ``"avatars/<sha256>.<ext>"``. None/빈값 = 이니셜 fallback.
    size : int
        pixmap 한 변 길이(정원 diameter).

    Returns
    -------
    QPixmap
        size x size 원형 pixmap (이미지 또는 이니셜).
    """
    # 한글 주석 — 캐시 위임(순환 import 회피 위해 함수 로컬 import)
    from app.ui._avatar_cache import avatar_cache

    return avatar_cache().pixmap(name, avatar_ref, size)
