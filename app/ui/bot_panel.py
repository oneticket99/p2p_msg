# SPDX-License-Identifier: GPL-3.0-or-later
"""BotPanel — bot tab 본격 panel skeleton (cycle 153 phase 4 신설).

텔레그램 desktop bot interaction 등가 — inline mode + command list + 봇 디렉토리.
정합 = telegram-ui-survey.md §13 + project_bot_framework + cycle 150~160 entry prereq.

signal:
    bot_selected(str) — bot username emit
    command_invoked(str, str) — (bot_username, command) emit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class BotEntry:
    """bot 단일 entry — 디렉토리 + interaction model."""

    username: str
    display_name: str
    description: str = ""
    emoji: str = "🤖"
    is_official: bool = False
    inline_enabled: bool = False
    commands: list[str] = ()  # type: ignore[assignment]


class BotPanel(QWidget):
    """bot tab 본격 panel — 디렉토리 + 상세 + command list + inline mode."""

    bot_selected = pyqtSignal(str)
    command_invoked = pyqtSignal(str, str)

    DEFAULT_BOTS = [
        BotEntry(
            username="toonation_cs",
            display_name="투네이션 고객센터",
            description="LLM 인터랙티브 Q&A bot — cycle 150~ default",
            emoji="🎫",
            is_official=True,
            commands=["/start", "/help", "/contact", "/faq"],
        ),
        BotEntry(
            username="stream_helper",
            display_name="방송 도우미",
            description="OBS + YouTube + Twitch + CHZZK + Kick — Nightbot 등가",
            emoji="🎬",
            is_official=True,
            commands=["/start", "/help", "/uptime", "/scene", "/alert"],
        ),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("botPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 한글 주석 — 좌측 bot list (240px)
        left_frame = QFrame()
        left_frame.setMinimumWidth(240)
        left_frame.setMaximumWidth(320)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("🤖 봇 디렉토리")
        title.setStyleSheet("color: #e5e7eb; font-size: 15px; font-weight: 600;")
        left_layout.addWidget(title)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 bot 검색")
        self._search_edit.setMinimumHeight(32)
        self._search_edit.textChanged.connect(self._on_search_changed)  # type: ignore[arg-type]
        left_layout.addWidget(self._search_edit)

        self._bot_list = QListWidget()
        self._bot_list.itemClicked.connect(self._on_bot_clicked)  # type: ignore[arg-type]
        left_layout.addWidget(self._bot_list, stretch=1)

        register_btn = QPushButton("+ 봇 등록 (BotFather 등가)")
        register_btn.setProperty("variant", "primary")
        register_btn.setMinimumHeight(40)
        left_layout.addWidget(register_btn)

        layout.addWidget(left_frame)

        # 한글 주석 — 우측 detail panel (flex)
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(16)

        self._detail_avatar = QLabel("🤖")
        self._detail_avatar.setFixedSize(64, 64)
        self._detail_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_avatar.setStyleSheet(
            "background-color: #1F2937;"
            " border: 2px solid #0066FF;"
            " border-radius: 32px;"
            " font-size: 32px;"
        )
        right_layout.addWidget(self._detail_avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        self._detail_name = QLabel("bot 선택 부재")
        self._detail_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_name.setStyleSheet("color: #e5e7eb; font-size: 18px; font-weight: 700;")
        right_layout.addWidget(self._detail_name)

        self._detail_username = QLabel("")
        self._detail_username.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_username.setStyleSheet("color: #67E8F9; font-size: 13px;")
        right_layout.addWidget(self._detail_username)

        self._detail_description = QLabel("")
        self._detail_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_description.setWordWrap(True)
        self._detail_description.setStyleSheet("color: #9ca3af; font-size: 13px;")
        right_layout.addWidget(self._detail_description)

        # 한글 주석 — tabbed (command + inline + log)
        self._tabs = QTabWidget()
        self._command_list = QListWidget()
        self._command_list.itemDoubleClicked.connect(self._on_command_invoked)  # type: ignore[arg-type]
        self._tabs.addTab(self._command_list, "/ commands")
        self._tabs.addTab(QLabel("@ inline mode — cycle 154+ entry"), "@ inline")
        self._tabs.addTab(QLabel("interaction log — cycle 154+ entry"), "log")
        right_layout.addWidget(self._tabs, stretch=1)

        layout.addWidget(right_frame, stretch=1)

        self._entries: list[BotEntry] = list(self.DEFAULT_BOTS)
        self._current_bot: Optional[BotEntry] = None
        self._render()

    def _on_search_changed(self, text: str) -> None:
        filter_text = text.strip().lower()
        self._render(filter_text)

    def _on_bot_clicked(self, item: QListWidgetItem) -> None:
        username = item.data(Qt.ItemDataRole.UserRole)
        entry = next((b for b in self._entries if b.username == username), None)
        if entry:
            self._current_bot = entry
            self._update_detail(entry)
            self.bot_selected.emit(entry.username)

    def _on_command_invoked(self, item: QListWidgetItem) -> None:
        if self._current_bot:
            self.command_invoked.emit(self._current_bot.username, item.text())

    def _update_detail(self, entry: BotEntry) -> None:
        self._detail_avatar.setText(entry.emoji)
        self._detail_name.setText(entry.display_name)
        badge = " ✓ 공식" if entry.is_official else ""
        self._detail_username.setText(f"@{entry.username}{badge}")
        self._detail_description.setText(entry.description)
        self._command_list.clear()
        for cmd in entry.commands:
            self._command_list.addItem(QListWidgetItem(cmd))

    def _render(self, filter_text: str = "") -> None:
        self._bot_list.clear()
        for entry in self._entries:
            if filter_text and filter_text not in entry.display_name.lower():
                if filter_text not in entry.username.lower():
                    continue
            badge = " ✓" if entry.is_official else ""
            item = QListWidgetItem(f"{entry.emoji} {entry.display_name}{badge}\n    @{entry.username}")
            item.setData(Qt.ItemDataRole.UserRole, entry.username)
            self._bot_list.addItem(item)
