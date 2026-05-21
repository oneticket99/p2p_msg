# SPDX-License-Identifier: GPL-3.0-or-later
"""GroupInfoDialog — 그룹 정보 보기 (cycle 169.334 image #103 telegram align).

레이아웃:
- 상단 close X (우측 상단)
- 그룹 avatar (큰 원형) + 그룹명 + 참가자 N 명
- 4 action button row (음소거 / 관리 / 나가기 / 더 보기)
- 참가자 list (icon + 참가자 N 명 + 추가 button) + 멤버 row scroll
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.ui._icons import load_pixmap
from app.ui._avatar_helper import get_initials
from app.ui.avatar_palette import palette_solid


class GroupInfoDialog(QDialog):
    """그룹 정보 dialog — 참가자 list + 4 action button."""

    mute_clicked = pyqtSignal()
    manage_clicked = pyqtSignal()
    leave_clicked = pyqtSignal()
    member_added = pyqtSignal(int)  # user_id

    def __init__(
        self,
        group_name: str,
        members: Optional[list[dict]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 그룹 정보")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        self._group_name = group_name
        self._members = list(members or [])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("groupInfoWrap")
        wrap.setStyleSheet(
            "QFrame#groupInfoWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 한글 주석 — 상단 close row
        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 0)
        top.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        top.addWidget(close_btn)
        body.addLayout(top)

        # 한글 주석 — avatar + name + count
        head = QVBoxLayout()
        head.setContentsMargins(20, 0, 20, 12)
        head.setSpacing(8)
        head.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        avatar_label = QLabel()
        avatar_label.setFixedSize(96, 96)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setPixmap(self._make_avatar(group_name, 96))
        head.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        name_label = QLabel(group_name)
        name_label.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        head.addWidget(name_label)
        count_label = QLabel(f"참가자 {len(self._members)}명")
        count_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        count_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        head.addWidget(count_label)
        body.addLayout(head)

        # 한글 주석 — 4 action button row (음소거 / 관리 / 나가기 / 더 보기)
        actions = QHBoxLayout()
        actions.setContentsMargins(16, 0, 16, 16)
        actions.setSpacing(8)
        for icon_name, label, signal_name in [
            ("notification", "음소거", "mute_clicked"),
            ("settings", "관리", "manage_clicked"),
            ("phone", "나가기", "leave_clicked"),
            ("more", "더 보기", None),
        ]:
            actions.addWidget(self._build_action(icon_name, label, signal_name), stretch=1)
        body.addLayout(actions)

        # 한글 주석 — separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1f2937;")
        body.addWidget(sep)

        # 한글 주석 — 참가자 row
        members_head = QHBoxLayout()
        members_head.setContentsMargins(20, 12, 20, 6)
        people_icon = QLabel()
        people_icon.setPixmap(load_pixmap("friends", size=20, color="#9ca3af"))
        members_head.addWidget(people_icon)
        members_label = QLabel(f"참가자 {len(self._members)}명")
        members_label.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        members_head.addWidget(members_label)
        members_head.addStretch(1)
        add_btn = QPushButton()
        add_btn.setFixedSize(28, 28)
        add_btn.setIcon(load_pixmap("friends", size=18, color="#0066FF"))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 0; }"
            "QPushButton:hover { background-color: rgba(0, 102, 255, 0.1); border-radius: 14px; }"
        )
        add_btn.clicked.connect(lambda: self.member_added.emit(0))  # type: ignore[arg-type]
        members_head.addWidget(add_btn)
        body.addLayout(members_head)

        # 한글 주석 — member list
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: transparent; border: 0; }"
            "QListWidget::item { padding: 8px 16px; }"
            "QListWidget::item:hover { background-color: #1F2937; }"
        )
        self._populate_members()
        body.addWidget(self._list, stretch=1)

    def _make_avatar(self, name: str, size: int) -> QPixmap:
        # 한글 주석 — chat_list entry 등가 (palette_solid bg + initials)
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(palette_solid(name)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        initials = get_initials(name)
        painter.setPen(QPen(QColor("#ffffff")))
        f = QFont()
        f.setPixelSize(int(size * 0.4))
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pix

    def _build_action(self, icon_name: str, label: str, signal_name: Optional[str]) -> QWidget:
        # 한글 주석 — 4 action button (icon + label vertical)
        w = QFrame()
        w.setStyleSheet("QFrame { background-color: #1F2937; border-radius: 8px; }")
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel()
        icon.setPixmap(load_pixmap(icon_name, size=20, color="#e5e7eb"))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(icon)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #e5e7eb; font-size: 12px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl)
        if signal_name is not None:
            w.mousePressEvent = lambda _e: getattr(self, signal_name).emit()  # type: ignore[assignment]
        return w

    def _populate_members(self) -> None:
        # 한글 주석 — member list 주입 (avatar + name + status + 소유자 chip)
        for m in self._members:
            name = m.get("name", "?")
            status = m.get("status", "최근에 접속함")
            role = m.get("role", "")
            text = f"{name}\n{status}"
            if role == "owner":
                text += "  · 소유자"
            item = QListWidgetItem(text)
            self._list.addItem(item)
        if not self._members:
            empty = QListWidgetItem("멤버 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)
