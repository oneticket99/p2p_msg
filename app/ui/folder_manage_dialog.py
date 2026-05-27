# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderManageDialog — 폴더 management modal (cycle 169.74 신설).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — FolderMixin/ChatNavigationMixin 이 instantiate +
folder_create/edit/delete_requested signal 로 결과 회신. FolderEditDialog 진입 트리거(생성/편집 위임).

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
    folder_edit_requested = pyqtSignal(str)  # cycle 169.381 — folder edit click (사용자 critique image #139)
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
        # cycle 169.380 — sidebar tab icon color 동일 #9ca3af (사용자 directive image #135)
        hero.setPixmap(load_pixmap("folder", size=72, color="#9ca3af"))
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

        # cycle 169.380 — 새 폴더 만들기 button = Toonation BI filled (사용자 directive image #138)
        new_btn = QPushButton("+ 새 폴더 만들기")
        new_btn.setFixedHeight(44)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton {"
            " color: #ffffff; background-color: #0066FF; border: 0;"
            " border-radius: 8px; font-size: 14px; font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #0052cc; }"
            "QPushButton:pressed { background-color: #003fa6; }"
        )
        new_btn.clicked.connect(self.folder_create_requested.emit)  # type: ignore[arg-type]
        c_layout.addWidget(new_btn)

        # cycle 169.380 — 탭 뷰 section 제거 (사용자 directive image #137)
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
        # cycle 169.380 — folder row icon color = folder.color_name (생성 시점 selected_color 반영) 사용자 critique image #136
        folder_color = folder.get("color_name") or "#9ca3af"
        icon.setPixmap(load_pixmap("folder", size=24, color=folder_color))
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
        # cycle 169.381 — more icon → edit icon SVG 교체 + folder_edit_requested chain (사용자 critique image #139/140)
        edit_btn = QPushButton()
        edit_btn.setIcon(load_icon("edit", size=20, color="#9ca3af"))
        edit_btn.setIconSize(QSize(20, 20))
        edit_btn.setFixedSize(32, 32)
        edit_btn.setFlat(True)
        edit_btn.setToolTip("폴더 수정")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fid = folder.get("folder_id", "")
        edit_btn.clicked.connect(lambda _c=False, f=fid: self.folder_edit_requested.emit(f))  # type: ignore[arg-type]
        r_layout.addWidget(edit_btn)
        return row
