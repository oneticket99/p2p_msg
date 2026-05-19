# SPDX-License-Identifier: GPL-3.0-or-later
"""SVG icon loader — QSvgRenderer + QPixmap + QIcon 변환 (cycle 169.51 신설)."""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def load_icon(name: str, size: int = 24, color: str = "#9ca3af") -> QIcon:
    """SVG load + color tint + QIcon 반환.

    Parameters
    ----------
    name : str
        icon file basename (확장자 부재).
    size : int
        pixel 크기 (square).
    color : str
        SVG fill currentColor 치환 색상 (hex).
    """
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()
    raw = svg_path.read_text(encoding="utf-8")
    # 한글 주석 — currentColor 치환 (SVG 안 fill="currentColor" 정합)
    tinted = raw.replace("currentColor", color)
    renderer = QSvgRenderer(tinted.encode("utf-8"))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


def load_pixmap(name: str, size: int = 24, color: str = "#9ca3af") -> QPixmap:
    """SVG load + color tint + QPixmap 반환 (QLabel.setPixmap 직접용)."""
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QPixmap()
    raw = svg_path.read_text(encoding="utf-8")
    tinted = raw.replace("currentColor", color)
    renderer = QSvgRenderer(tinted.encode("utf-8"))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return pix
