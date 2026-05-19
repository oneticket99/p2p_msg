# SPDX-License-Identifier: GPL-3.0-or-later
"""EmojiPicker — 9 category tab + 검색 + custom pack (cycle 153 phase 5 신설).

텔레그램 desktop emoji picker 등가 — 표준 emoji + sticker pack + custom emoji.
정합 = telegram-ui-survey.md §12 + project_emoji_pack_share + cycle 144 moderation queue.

signal:
    emoji_selected(str) — emoji codepoint emit
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


# 한글 주석 — 9 category emoji set (Unicode BMP + supplementary plane 만)
EMOJI_CATEGORIES = [
    ("최근", "⏱", ["😀", "😂", "🤣", "❤️", "👍", "🎉", "🔥", "✨"]),
    ("표정", "😀", [
        "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆",
        "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗",
        "🙂", "🤗", "🤔", "🤐", "🤨", "😐", "😑", "😶",
        "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪",
    ]),
    ("동물", "🐶", [
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼",
        "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔",
        "🐧", "🐦", "🐤", "🦅", "🦉", "🦄", "🐝", "🐛",
    ]),
    ("음식", "🍔", [
        "🍔", "🍟", "🍕", "🌭", "🥪", "🌮", "🥗", "🍝",
        "🍜", "🍣", "🍱", "🍤", "🍞", "🧀", "🥩", "🍗",
        "🍎", "🍌", "🍓", "🍇", "🍊", "🍋", "🍉", "🍑",
    ]),
    ("활동", "⚽", [
        "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🎱",
        "🏓", "🏸", "🥊", "🥋", "🎯", "🎮", "🎲", "🎸",
    ]),
    ("여행", "🚗", [
        "🚗", "🚕", "🚙", "🚌", "🚎", "🏎", "🚓", "🚑",
        "🛻", "🚚", "🚛", "🚜", "🛵", "🏍", "🚲", "🛴",
        "✈️", "🚀", "⛵", "🚢", "🚆", "🚄", "🚂", "🚁",
    ]),
    ("사물", "💡", [
        "💡", "🔦", "🕯", "📱", "💻", "⌨️", "🖱", "🖨",
        "📷", "📹", "🎥", "📺", "📻", "🎙", "📞", "☎️",
        "⌛", "⏰", "⏱", "⏲", "📅", "📆", "📇", "📋",
    ]),
    ("심볼", "❤️", [
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍",
        "💔", "❣️", "💕", "💞", "💓", "💗", "💖", "💘",
        "✅", "❌", "⭕", "❗", "❓", "✨", "🔥", "🎉",
    ]),
    ("국기", "🚩", [
        "🚩", "🏳️", "🏴", "🏁", "🇰🇷", "🇺🇸", "🇯🇵", "🇨🇳",
        "🇬🇧", "🇫🇷", "🇩🇪", "🇮🇹", "🇪🇸", "🇧🇷", "🇷🇺", "🇮🇳",
    ]),
]


class EmojiCategoryView(QScrollArea):
    """단일 category emoji grid — 8 column scrollable."""

    emoji_clicked = pyqtSignal(str)

    def __init__(self, emojis: list[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(4)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        for i, emoji in enumerate(emojis):
            btn = QPushButton(emoji)
            btn.setFixedSize(36, 36)
            btn.setProperty("variant", "ghost")
            btn.setStyleSheet(
                "QPushButton {"
                " font-size: 22px;"
                " background-color: transparent;"
                " border: none;"
                " border-radius: 4px;"
                "}"
                "QPushButton:hover { background-color: rgba(0, 102, 255, 0.15); }"
            )
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _c=False, e=emoji: self.emoji_clicked.emit(e)
            )
            grid.addWidget(btn, i // 8, i % 8)

        self.setWidget(content)


class EmojiPicker(QWidget):
    """9 category tabbed emoji picker — 검색 bar + custom pack 통합."""

    emoji_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("emojiPicker")
        self.setFixedSize(400, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 한글 주석 — 검색 bar top
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 8, 8, 4)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 emoji 검색")
        self._search_edit.setMinimumHeight(32)
        self._search_edit.textChanged.connect(self._on_search_changed)  # type: ignore[arg-type]
        search_layout.addWidget(self._search_edit)
        layout.addWidget(search_frame)

        # 한글 주석 — category tab (north position icon-only)
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._category_views: list[EmojiCategoryView] = []
        for label, icon, emojis in EMOJI_CATEGORIES:
            view = EmojiCategoryView(emojis)
            view.emoji_clicked.connect(self._on_emoji_clicked)  # type: ignore[arg-type]
            self._tabs.addTab(view, icon)
            self._category_views.append(view)

        layout.addWidget(self._tabs, stretch=1)

        # 한글 주석 — custom pack section (cycle 154+ binding — emoji_pack_share)
        custom_frame = QFrame()
        custom_frame.setStyleSheet("background-color: #0a0f1c; border-top: 1px solid #1f2937;")
        custom_layout = QHBoxLayout(custom_frame)
        custom_layout.setContentsMargins(8, 6, 8, 6)
        custom_label = QLabel("🎨 custom pack (cycle 154+)")
        custom_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        custom_layout.addWidget(custom_label)
        custom_layout.addStretch(1)
        add_btn = QPushButton("+ pack 등록")
        add_btn.setProperty("variant", "ghost")
        add_btn.setFlat(True)
        custom_layout.addWidget(add_btn)
        layout.addWidget(custom_frame)

    def _on_emoji_clicked(self, emoji: str) -> None:
        """emoji button click → signal emit + recent 누적 (cycle 154+ persist)."""
        self.emoji_selected.emit(emoji)
        log.debug("emoji selected — %s", emoji)

    def _on_search_changed(self, text: str) -> None:
        """검색 filter — 모든 category 안 emoji match (cycle 154 본격)."""
        # 한글 주석 — 본 cycle 153.5 안 = placeholder. cycle 154 안 정식 filter 적용
        log.debug("emoji search — %r", text)
