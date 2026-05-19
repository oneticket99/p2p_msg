# SPDX-License-Identifier: GPL-3.0-or-later
"""ProfileView — 친구 / self 프로필 view (cycle 153 phase 4 신설).

텔레그램 desktop 프로필 등가 — avatar + name + status + bio + 4 button + 공통 방 + 미디어 tab.
정합 = telegram-ui-survey.md §10 + toonation-brand-integration-plan §4.4.

signal:
    message_clicked(int) — 메시지 button click + user_id emit
    call_clicked(int) — 통화 button (cycle 200+ entry)
    mute_clicked(int) — 음소거 토글
    block_clicked(int) — 차단 button
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ProfileData:
    """프로필 view model."""

    user_id: int
    email: str
    username: str
    bio: str = ""
    avatar_emoji: str = "👤"
    is_online: bool = False
    last_seen: str = ""
    is_self: bool = False


class ProfileView(QWidget):
    """avatar + name + bio + 4 action button + tabbed 미디어 view."""

    message_clicked = pyqtSignal(int)
    call_clicked = pyqtSignal(int)
    mute_clicked = pyqtSignal(int)
    block_clicked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("profileView")
        self._user_id: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 한글 주석 — header section (avatar + name + status)
        header = QFrame()
        header.setObjectName("profileHeader")
        header.setStyleSheet(
            "QFrame#profileHeader {"
            " background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F172A, stop:1 #1F2937);"
            "}"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 32, 24, 24)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._avatar_label = QLabel("👤")
        self._avatar_label.setFixedSize(96, 96)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setStyleSheet(
            "background-color: #1F2937;"
            " border: 3px solid #0066FF;"
            " border-radius: 48px;"
            " font-size: 48px;"
            " color: #67E8F9;"
        )
        header_layout.addWidget(self._avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_label = QLabel("user@example.com")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setStyleSheet("color: #e5e7eb; font-size: 20px; font-weight: 700;")
        header_layout.addWidget(self._name_label)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #67E8F9; font-size: 13px;")
        header_layout.addWidget(self._status_label)

        layout.addWidget(header)

        # 한글 주석 — 4 action button row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 16, 16, 16)
        btn_row.setSpacing(12)
        for icon_label, signal_attr in [
            ("💬 메시지", "message_clicked"),
            ("📞 통화", "call_clicked"),
            ("🔇 음소거", "mute_clicked"),
            ("🚫 차단", "block_clicked"),
        ]:
            btn = QPushButton(icon_label)
            btn.setProperty("variant", "secondary")
            btn.setMinimumHeight(40)
            sig = getattr(self, signal_attr)
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _c=False, s=sig: s.emit(self._user_id or 0)
            )
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        # 한글 주석 — info section (email + username + bio)
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(24, 16, 24, 16)
        info_layout.setSpacing(12)

        self._email_label = QLabel("")
        self._email_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        info_layout.addWidget(self._email_label)

        self._username_label = QLabel("")
        self._username_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        info_layout.addWidget(self._username_label)

        self._bio_label = QLabel("")
        self._bio_label.setWordWrap(True)
        self._bio_label.setStyleSheet("color: #e5e7eb; font-size: 14px; padding-top: 8px;")
        info_layout.addWidget(self._bio_label)

        layout.addWidget(info_frame)

        # 한글 주석 — tabbed 미디어 view (공통 방 + 미디어 + 파일 + sticker)
        self._tabs = QTabWidget()
        self._tabs.addTab(QLabel(""), "공통 방 (0)")
        self._tabs.addTab(QLabel(""), "미디어")
        self._tabs.addTab(QLabel(""), "파일")
        self._tabs.addTab(QLabel(""), "sticker")
        layout.addWidget(self._tabs, stretch=1)

    def set_profile(self, profile: ProfileData) -> None:
        """프로필 data 설정 + view 갱신."""
        self._user_id = profile.user_id
        self._avatar_label.setText(profile.avatar_emoji)
        self._name_label.setText(profile.username or profile.email)
        status = "🟢 online" if profile.is_online else (profile.last_seen or "")
        self._status_label.setText(status)
        self._email_label.setText(f"✉ {profile.email}")
        self._username_label.setText(f"@ {profile.username}")
        self._bio_label.setText(profile.bio)
