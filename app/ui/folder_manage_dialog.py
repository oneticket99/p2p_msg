# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderManageDialog — 폴더 management modal (cycle 169.74 신설).

사용자 directive 회수 — telegram desktop 안 편집 button click → 폴더 관리 dialog.
folder list + 새 폴더 만들기 + 추천 폴더 + 폴더 태그 표시 + 탭 view 선택.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class FolderManageDialog(QDialog):
    """폴더 관리 modal — telegram desktop align."""

    folder_create_requested = pyqtSignal()
    folder_delete_requested = pyqtSignal(str)  # folder_id
    tab_view_changed = pyqtSignal(str)  # "left" / "top"

    def __init__(
        self,
        user_folders: Optional[List[dict]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 폴더")
        self.setModal(True)
        # cycle 169.201 — frameless modal 의무 (사용자 directive cycle 169.121 pattern align)
        from PyQt6.QtCore import Qt
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        # cycle 169.292 — MyProfileDialog 등가 strict
        # cycle 169.349 — 사용자 directive image #117 — 폭 20% 감소 (420 → 336)
        self.setFixedSize(336, 600)
        self._user_folders = user_folders or []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # header — 폴더 title + X
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet("background-color: #1F2937;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 8, 12, 8)
        title = QLabel("폴더")
        title.setStyleSheet("color: #e5e7eb; font-size: 16px; font-weight: 700;")
        h_layout.addWidget(title)
        h_layout.addStretch(1)
        # cycle 169.324 — 공통 close button factory (telegram align)
        from app.ui._close_button import make_close_button
        close_btn = make_close_button(self.reject, self)
        h_layout.addWidget(close_btn)
        outer.addWidget(header)

        # scroll content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #131C30; }")
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(16)

        # folder icon hero
        hero = QLabel()
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero.setPixmap(load_pixmap("folder", size=72, color="#22D3EE"))
        c_layout.addWidget(hero)

        intro = QLabel("대화방을 모은 폴더를 여럿 만들고 신속하게 대화를 전환하세요.")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9ca3af; font-size: 13px;")
        c_layout.addWidget(intro)

        c_layout.addSpacing(8)

        # 내 폴더 section
        my_label = QLabel("내 폴더")
        my_label.setStyleSheet("color: #22D3EE; font-size: 12px; font-weight: 700;")
        c_layout.addWidget(my_label)

        for folder in self._user_folders:
            row = self._build_folder_row(folder)
            c_layout.addWidget(row)

        # 새 폴더 만들기 button
        new_btn = QPushButton("  + 새 폴더 만들기")
        new_btn.setFixedHeight(40)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton {"
            " color: #0066FF; background: transparent; border: none;"
            " text-align: left; padding-left: 12px; font-size: 14px; font-weight: 600;"
            "}"
            " QPushButton:hover { background-color: rgba(0,102,255,0.08); }"
        )
        new_btn.clicked.connect(self.folder_create_requested.emit)  # type: ignore[arg-type]
        c_layout.addWidget(new_btn)

        c_layout.addSpacing(16)

        # 탭 뷰 section
        tab_label = QLabel("탭 뷰")
        tab_label.setStyleSheet("color: #22D3EE; font-size: 12px; font-weight: 700;")
        c_layout.addWidget(tab_label)

        self._tab_group = QButtonGroup(self)
        left_radio = QRadioButton("좌측 탭")
        left_radio.setChecked(True)
        left_radio.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        top_radio = QRadioButton("상단 탭")
        top_radio.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        self._tab_group.addButton(left_radio, 0)
        self._tab_group.addButton(top_radio, 1)
        c_layout.addWidget(left_radio)
        c_layout.addWidget(top_radio)
        left_radio.toggled.connect(lambda checked: checked and self.tab_view_changed.emit("left"))  # type: ignore[arg-type]
        top_radio.toggled.connect(lambda checked: checked and self.tab_view_changed.emit("top"))  # type: ignore[arg-type]

        c_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

    def _build_folder_row(self, folder: dict) -> QFrame:
        """단일 folder row — icon + name + 대화 N개 + delete button."""
        row = QFrame()
        row.setFixedHeight(56)
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(12, 8, 12, 8)
        icon = QLabel()
        icon.setPixmap(load_pixmap("folder", size=24, color="#0066FF"))
        icon.setFixedWidth(32)
        r_layout.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(folder.get("name", ""))
        name.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: 600;")
        col.addWidget(name)
        count = QLabel(f"대화 {folder.get('chat_count', 0)}개")
        count.setStyleSheet("color: #9ca3af; font-size: 12px;")
        col.addWidget(count)
        r_layout.addLayout(col, stretch=1)
        del_btn = QPushButton()
        del_btn.setIcon(load_icon("more", size=20, color="#9ca3af"))
        del_btn.setIconSize(QSize(20, 20))
        del_btn.setFixedSize(32, 32)
        del_btn.setFlat(True)
        fid = folder.get("folder_id", "")
        del_btn.clicked.connect(lambda _c=False, f=fid: self.folder_delete_requested.emit(f))  # type: ignore[arg-type]
        r_layout.addWidget(del_btn)
        return row
