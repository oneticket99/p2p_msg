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
