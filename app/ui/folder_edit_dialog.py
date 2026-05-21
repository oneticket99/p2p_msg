# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderEditDialog — 새 폴더 만들기 modal (cycle 169.75 신설).

사용자 directive 회수 — telegram desktop image 82 align.
폴더명 + 포함 대화방 + 제외 대화방 + 색상 7 swatch + 초대 링크 chain.
"""

from __future__ import annotations

import uuid
from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon


FOLDER_COLORS = [
    ("red", "#ef4444"),
    ("orange", "#f97316"),
    ("purple", "#a855f7"),
    ("green", "#22c55e"),
    ("blue", "#3b82f6"),
    ("indigo", "#6366f1"),
    ("pink", "#ec4899"),
]


class FolderEditDialog(QDialog):
    """새 폴더 만들기 modal — telegram desktop image 82 align."""

    folder_saved = pyqtSignal(dict)
    chat_picker_requested = pyqtSignal(str)  # "include" / "exclude"
    invite_link_requested = pyqtSignal()

    def __init__(
        self,
        existing: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 새 폴더")
        self.setModal(True)
        # cycle 169.201 — frameless modal 의무 (사용자 directive cycle 169.121 pattern align)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        # cycle 169.292 — MyProfileDialog 등가 strict
        # cycle 169.349 — 사용자 directive image #117 — 폭 20% 감소 (420 → 336)
        self.setFixedSize(336, 600)
        self._existing = existing or {}
        self._included_chats: list = list(self._existing.get("included_chats", []))
        self._excluded_chats: list = list(self._existing.get("excluded_chats", []))
        self._selected_color: str = self._existing.get("color_name", "")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #131C30; }")
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(14)

        title = QLabel("새 폴더")
        title.setStyleSheet("color: #e5e7eb; font-size: 18px; font-weight: 700;")
        c_layout.addWidget(title)

        # 폴더명 input
        name_label = QLabel("폴더명")
        name_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        c_layout.addWidget(name_label)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("폴더명 입력…")
        self._name_edit.setText(self._existing.get("name", ""))
        self._name_edit.setMinimumHeight(36)
        c_layout.addWidget(self._name_edit)

        c_layout.addSpacing(8)

        # 포함할 대화방
        inc_label = QLabel("포함할 대화방")
        inc_label.setStyleSheet("color: #22D3EE; font-size: 13px; font-weight: 700;")
        c_layout.addWidget(inc_label)
        self._include_btn = self._build_picker_button("+  대화방 추가", "include")
        c_layout.addWidget(self._include_btn)
        inc_hint = QLabel("폴더에 표시할 대화방 혹은 대화방 유형을 정하세요.")
        inc_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        inc_hint.setWordWrap(True)
        c_layout.addWidget(inc_hint)

        c_layout.addSpacing(8)

        # 제외할 대화방
        exc_label = QLabel("제외할 대화방")
        exc_label.setStyleSheet("color: #22D3EE; font-size: 13px; font-weight: 700;")
        c_layout.addWidget(exc_label)
        self._exclude_btn = self._build_picker_button("−  제외할 대화방 추가", "exclude")
        c_layout.addWidget(self._exclude_btn)
        exc_hint = QLabel("폴더에 표시하지 않을 대화방 혹은 유형을 정하세요.")
        exc_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        exc_hint.setWordWrap(True)
        c_layout.addWidget(exc_hint)

        c_layout.addSpacing(8)

        # 색상 선택
        color_label = QLabel("대화 목록의 폴더 색상")
        color_label.setStyleSheet("color: #22D3EE; font-size: 13px; font-weight: 700;")
        c_layout.addWidget(color_label)

        color_row = QHBoxLayout()
        color_row.setSpacing(8)
        self._color_group = QButtonGroup(self)
        self._color_group.setExclusive(True)
        for i, (name, hex_color) in enumerate(FOLDER_COLORS):
            cbtn = QToolButton()
            cbtn.setFixedSize(32, 32)
            cbtn.setCheckable(True)
            cbtn.setStyleSheet(
                f"QToolButton {{"
                f" background-color: {hex_color};"
                f" border: 2px solid transparent;"
                f" border-radius: 16px;"
                f"}}"
                f" QToolButton:checked {{ border-color: #ffffff; }}"
            )
            cbtn.clicked.connect(  # type: ignore[arg-type]
                lambda _c=False, n=name: setattr(self, "_selected_color", n)
            )
            self._color_group.addButton(cbtn, i)
            color_row.addWidget(cbtn)
        color_row.addStretch(1)
        c_layout.addLayout(color_row)

        c_layout.addSpacing(8)

        # 폴더 공유 — 초대 링크
        share_label = QLabel("폴더 공유")
        share_label.setStyleSheet("color: #22D3EE; font-size: 13px; font-weight: 700;")
        c_layout.addWidget(share_label)
        link_btn = QPushButton("🔗  초대 링크 생성")
        link_btn.setStyleSheet(
            "QPushButton {"
            " color: #0066FF; background: transparent; border: none;"
            " text-align: left; padding: 8px 0; font-size: 13px; font-weight: 600;"
            "}"
            " QPushButton:hover { color: #67E8F9; }"
        )
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(self.invite_link_requested.emit)  # type: ignore[arg-type]
        c_layout.addWidget(link_btn)
        link_hint = QLabel("이 폴더의 일부 그룹 및 채널 접근을 다른 사용자와 공유합니다.")
        link_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        link_hint.setWordWrap(True)
        c_layout.addWidget(link_hint)

        c_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # 버튼 row — 취소 / 만들기
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(20, 8, 20, 16)
        btn_row.addStretch(1)
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("color: #9ca3af; background: transparent; border: none; font-size: 14px;")
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("만들기")
        save_btn.setStyleSheet(
            "QPushButton {"
            " color: #0066FF; background: transparent; border: none;"
            " font-size: 14px; font-weight: 700; padding: 8px 16px;"
            "}"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)  # type: ignore[arg-type]
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

    def _build_picker_button(self, label: str, mode: str) -> QPushButton:
        """포함/제외 picker button."""
        btn = QPushButton(label)
        btn.setStyleSheet(
            "QPushButton {"
            " color: #0066FF; background: transparent; border: none;"
            " text-align: left; padding: 8px 0; font-size: 13px; font-weight: 600;"
            "}"
            " QPushButton:hover { color: #67E8F9; }"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _c=False, m=mode: self.chat_picker_requested.emit(m))  # type: ignore[arg-type]
        return btn

    def add_included_chats(self, chats: list) -> None:
        """ChatPickerDialog 응답 — 포함 대화방 추가."""
        self._included_chats.extend(chats)
        n = len(self._included_chats)
        self._include_btn.setText(f"+  대화방 추가 ({n}개)")

    def add_excluded_chats(self, chats: list) -> None:
        """ChatPickerDialog 응답 — 제외 대화방 추가."""
        self._excluded_chats.extend(chats)
        n = len(self._excluded_chats)
        self._exclude_btn.setText(f"−  제외할 대화방 추가 ({n}개)")

    def _on_save(self) -> None:
        """만들기 click — validation + folder_saved emit."""
        name = self._name_edit.text().strip()
        if not name:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "TooTalk", "폴더명 입력 의무")
            return
        folder_data = {
            "folder_id": self._existing.get("folder_id") or uuid.uuid4().hex[:8],
            "name": name,
            "color_name": self._selected_color,
            "included_chats": self._included_chats,
            "excluded_chats": self._excluded_chats,
            "chat_count": len(self._included_chats),
        }
        self.folder_saved.emit(folder_data)
        self.accept()
