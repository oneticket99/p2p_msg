# SPDX-License-Identifier: GPL-3.0-or-later
"""MemberPanel — 그룹 멤버 목록 + 뒤로 가기 헤더 래퍼 (cycle 169.819 신설).

기존 ``MemberListWidget`` (QListWidget) 는 헤더를 품을 수 없어, "멤버 보기" 진입
후 이전 화면(그룹 채팅)으로 돌아갈 back 버튼이 없었다. 본 래퍼는 상단에
"← 뒤로" 버튼 + "멤버" 타이틀 헤더를 두고 그 아래 ``MemberListWidget`` 를
배치해, 뒤로 가기 네비게이션 + 빈 목록 안내를 제공한다.

``set_members`` 는 내부 리스트로 위임하고, 뒤로 버튼은 ``back_requested`` 신호를
발행한다 (MainWindow 가 그룹 채팅 stack 으로 복귀).
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.member_list import MemberItem, MemberListWidget


class MemberPanel(QWidget):
    """멤버 목록 + 뒤로 가기 헤더 컨테이너.

    Signals
    -------
    back_requested : pyqtSignal()
        헤더의 "← 뒤로" 버튼 클릭 시 (이전 그룹 채팅 화면 복귀 요청).
    member_kicked : pyqtSignal(int)
        내부 MemberListWidget 의 추방 신호 passthrough.
    """

    back_requested = pyqtSignal()
    member_kicked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 헤더 — 뒤로 버튼 + 타이틀
        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)
        back_btn = QPushButton("← 뒤로", header)
        back_btn.setFixedWidth(72)
        back_btn.setStyleSheet(
            "QPushButton { color: #93c5fd; background: transparent; border: none;"
            " font-size: 14px; } QPushButton:hover { color: #bfdbfe; }"
        )
        back_btn.clicked.connect(self.back_requested.emit)
        title = QLabel("멤버", header)
        title.setStyleSheet("color: #f3f4f6; font-size: 15px; font-weight: 600; background: transparent;")
        header_layout.addWidget(back_btn)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        outer.addWidget(header)

        # 멤버 목록 + 빈 안내 라벨 (QStackedWidget 으로 토글)
        self._stack = QStackedWidget(self)
        self._list = MemberListWidget(parent=self._stack)
        self._list.member_kicked.connect(self.member_kicked.emit)
        self._empty_label = QLabel("아직 참여 멤버가 없습니다", self._stack)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #6b7280; font-size: 13px; background: transparent;")
        self._stack.addWidget(self._list)
        self._stack.addWidget(self._empty_label)
        outer.addWidget(self._stack, stretch=1)

    def set_members(
        self, members: List[MemberItem], *, viewer_role: str = "member"
    ) -> None:
        """멤버 목록 갱신 — 비면 안내 라벨, 있으면 리스트 표시."""
        self._list.set_members(members, viewer_role=viewer_role)
        # 한글 주석 — 빈 목록이면 안내 라벨 page, 아니면 list page
        self._stack.setCurrentWidget(self._empty_label if not members else self._list)

    def member_count(self) -> int:
        """현재 표시 중인 멤버 수 — 내부 MemberListWidget 위임.

        cycle 169.821 — MemberListWidget → MemberPanel 교체(cycle 169.819) 후
        ``_member_list.member_count()`` 호출부(invite refresh test 등) 정합 회복.
        """
        return self._list.member_count()

    def viewer_role(self) -> str:
        """현재 viewer 의 role — 내부 MemberListWidget 위임."""
        return self._list.viewer_role()
