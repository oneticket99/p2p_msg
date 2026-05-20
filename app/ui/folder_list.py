# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderList — telegram desktop 좌측 folder column (cycle 169.69 신설).

image 73 align — 모든 대화방 + 모니터링 + 업무협조 + 이슈알림 + 파티 + 사내동호회 + 안읽음 + 편집.
폴더 entry + unread badge + active highlight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon


@dataclass(frozen=True)
class FolderItem:
    """folder 단일 entry."""

    folder_id: str
    label: str
    icon_name: str  # SVG asset name
    unread: int = 0


DEFAULT_FOLDERS: List[FolderItem] = [
    FolderItem("all", "모든\n대화방", "friends", 13),
    FolderItem("monitor", "모니터링", "notification", 7),
    FolderItem("work", "업무협조", "folder", 0),
    FolderItem("issue", "이슈알림", "info", 0),
    FolderItem("party", "파티", "emoji", 0),
    FolderItem("internal", "사내동호회", "account", 0),
    FolderItem("unread", "안읽음", "search", 13),
    FolderItem("edit", "편집", "settings", 0),
]


class FolderList(QFrame):
    """좌측 folder column — 8 default folder + unread badge."""

    folder_selected = pyqtSignal(str)  # folder_id emit

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("folderList")
        self.setFixedWidth(96)
        self.setStyleSheet(
            "QFrame#folderList { background-color: #0F172A; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}

        for i, folder in enumerate(DEFAULT_FOLDERS):
            btn = self._build_folder_button(folder)
            self._group.addButton(btn, i)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self._buttons[folder.folder_id] = btn

        # 첫 folder active default
        if self._buttons:
            self._buttons["all"].setChecked(True)

        layout.addStretch(1)

    def _build_folder_button(self, folder: FolderItem) -> QToolButton:
        """단일 folder button — icon + label + unread badge."""
        btn = QToolButton()
        btn.setObjectName("folderButton")
        btn.setCheckable(True)
        btn.setFixedSize(80, 64)
        btn.setIcon(load_icon(folder.icon_name, size=20, color="#9ca3af"))
        btn.setIconSize(QSize(20, 20))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setText(folder.label)
        if folder.unread > 0:
            badge = str(folder.unread) if folder.unread < 100 else "99+"
            btn.setText(f"{folder.label}\n({badge})")
        btn.clicked.connect(  # type: ignore[arg-type]
            lambda _checked, fid=folder.folder_id: self.folder_selected.emit(fid)
        )
        btn.setStyleSheet(
            "QToolButton#folderButton {"
            " background-color: transparent;"
            " border: none;"
            " border-radius: 6px;"
            " color: #9ca3af;"
            " font-size: 10px;"
            "}"
            "QToolButton#folderButton:hover {"
            " background-color: rgba(0, 102, 255, 0.08);"
            "}"
            "QToolButton#folderButton:checked {"
            " background-color: rgba(0, 102, 255, 0.18);"
            " color: #67E8F9;"
            "}"
        )
        return btn

    def set_active(self, folder_id: str) -> None:
        """programmatic folder switch."""
        if folder_id in self._buttons:
            self._buttons[folder_id].setChecked(True)
