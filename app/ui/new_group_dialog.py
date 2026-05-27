# SPDX-License-Identifier: GPL-3.0-or-later
"""NewGroupDialog — 그룹 만들기 2 step wizard (cycle 169.333 rewrite).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — DrawerMixin 이 instantiate(그룹 생성 wizard) +
group_created signal(name, member_ids) 회신. 서버 room(kind=group) 승격 + invite 는 caller 책임.

사용자 directive image #97/98/99/100/101 — telegram align 2 단계 chain:
- Step 1: 그룹명 + 카메라 (photo) + 취소 + 다음
- Step 2: 참가자 추가 (검색 + 친구 list scrollable + chip + 만들기)
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.ui._icons import load_icon
from app.i18n.labels import tr as _tr


class NewGroupDialog(QDialog):
    """그룹 만들기 wizard — telegram align 2 step."""

    group_created = pyqtSignal(str, list)  # (group_name, member_ids)

    def __init__(self, friends: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # telegram align outer wrap + 420x600 strict + 2 step QStackedWidget
        super().__init__(parent)
        self.setWindowTitle(_tr("tootalk_그룹_만들기"))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        self._friends = friends or []
        self._selected_ids: list[int] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("newGroupWrap")
        wrap.setStyleSheet(
            "QFrame#newGroupWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # common header (title + close)
        self._header_row = QHBoxLayout()
        self._header_row.setContentsMargins(20, 16, 20, 0)
        self._title = QLabel("그룹 만들기")
        self._title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        self._header_row.addWidget(self._title)
        self._header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        self._header_row.addWidget(close_btn)
        body.addLayout(self._header_row)

        # 2 step QStackedWidget
        self._stack = QStackedWidget()
        body.addWidget(self._stack, stretch=1)

        self._build_step1()
        self._build_step2()
        self._stack.setCurrentIndex(0)

    def _build_step1(self) -> None:
        # Step 1: 카메라 circle + 그룹명 input + 취소/다음 button row
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 24, 20, 16)
        layout.setSpacing(16)

        # cycle 169.852 — avatar circle = AvatarPickerButton(파일/카메라/클립보드
        # 드롭다운, 이모지 제외). 선택 이미지는 _on_create 시 sender 경유 _drawer_mixin 업로드.
        row = QHBoxLayout()
        from app.ui._avatar_picker_button import AvatarPickerButton
        self._avatar_picker = AvatarPickerButton(name="", size=72)
        row.addWidget(self._avatar_picker)
        # name input (underline only)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("그룹명")
        self._name_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: transparent;"
            " border: none; border-bottom: 1px solid #374151; padding: 10px 4px;"
            " font-size: 16px; }"
            "QLineEdit:focus { border-bottom: 1px solid #0066FF; }"
        )
        row.addWidget(self._name_edit, stretch=1)
        layout.addLayout(row)
        layout.addStretch(1)

        # bottom button row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("취소")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel_btn)
        next_btn = QPushButton("다음")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        next_btn.clicked.connect(self._on_next)  # type: ignore[arg-type]
        btn_row.addWidget(next_btn)
        layout.addLayout(btn_row)

        self._stack.addWidget(page)

    def _build_step2(self) -> None:
        # Step 2: 참가자 추가 — 검색 + chip + 친구 list + 취소/만들기
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # title + count row
        title_row = QHBoxLayout()
        self._participants_title = QLabel("참가자 추가")
        self._participants_title.setStyleSheet("color: #f3f4f6; font-size: 16px; font-weight: 600;")
        title_row.addWidget(self._participants_title)
        self._count_label = QLabel("0 / 200000")
        self._count_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        title_row.addWidget(self._count_label)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        # cycle 169.352 — 사용자 directive image #118 — 이모지 차단 + SVG icon 대체
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("검색")
        search_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px 8px 8px 32px; }"
        )
        search_edit.textChanged.connect(self._on_search)  # type: ignore[arg-type]
        # SVG search icon LeadingPosition prepend
        from PyQt6.QtGui import QAction
        search_action = QAction(self)
        search_action.setIcon(load_icon("search", size=16, color="#9ca3af"))
        search_edit.addAction(search_action, QLineEdit.ActionPosition.LeadingPosition)
        layout.addWidget(search_edit)

        # selected chip area
        self._chip_frame = QFrame()
        self._chip_frame.setStyleSheet("background: transparent;")
        self._chip_layout = QHBoxLayout(self._chip_frame)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(6)
        self._chip_layout.addStretch(1)
        self._chip_frame.setVisible(False)
        layout.addWidget(self._chip_frame)

        # 친구 list
        self._friend_list = QListWidget()
        self._friend_list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 10px; }"
            "QListWidget::item:hover { background-color: #2c3a52; }"
            "QListWidget::item:selected { background-color: rgba(0, 102, 255, 0.2); }"
        )
        self._friend_list.itemClicked.connect(self._on_friend_click)  # type: ignore[arg-type]
        self._populate_friends()
        layout.addWidget(self._friend_list, stretch=1)

        # bottom button row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("취소")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel_btn)
        create_btn = QPushButton("만들기")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        create_btn.clicked.connect(self._on_create)  # type: ignore[arg-type]
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)

        self._stack.addWidget(page)

    def _populate_friends(self) -> None:
        # 친구 list 주입
        self._friend_list.clear()
        for f in self._friends:
            uid = f.get("target_id") or f.get("user_id") or 0
            name = f.get("name", "?")
            last_seen = f.get("last_seen", "최근에 접속함")
            item = QListWidgetItem(f"{name}\n{last_seen}")
            item.setData(Qt.ItemDataRole.UserRole, uid)
            self._friend_list.addItem(item)
        if not self._friends:
            empty = QListWidgetItem("등록된 친구 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._friend_list.addItem(empty)

    def _on_search(self, text: str) -> None:
        # 검색 filter
        text = text.lower().strip()
        for i in range(self._friend_list.count()):
            item = self._friend_list.item(i)
            if item is None:
                continue
            visible = (text == "") or (text in item.text().lower())
            item.setHidden(not visible)

    def _on_friend_click(self, item: QListWidgetItem) -> None:
        # 친구 select toggle + chip 갱신 + count update
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid is None:
            return
        if uid in self._selected_ids:
            self._selected_ids.remove(uid)
        else:
            self._selected_ids.append(uid)
        self._refresh_chips()
        self._count_label.setText(f"{len(self._selected_ids)} / 200000")

    def _refresh_chips(self) -> None:
        # selected ids chip 재 render
        while self._chip_layout.count() > 1:
            it = self._chip_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        name_map = {f.get("target_id") or f.get("user_id"): f.get("name", "?") for f in self._friends}
        for uid in self._selected_ids:
            name = name_map.get(uid, "?")
            chip = QLabel(f"  {name[:8]}  ")
            chip.setStyleSheet(
                "QLabel { color: #ffffff; background-color: #0066FF;"
                " border-radius: 10px; padding: 4px 8px; font-size: 12px; }"
            )
            self._chip_layout.insertWidget(self._chip_layout.count() - 1, chip)
        self._chip_frame.setVisible(bool(self._selected_ids))

    def _on_next(self) -> None:
        # step 1 → step 2
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self._stack.setCurrentIndex(1)
        self._title.setText("참가자 추가")

    def _on_create(self) -> None:
        # group_created emit (parent main_window 의 chat entry add chain)
        name = self._name_edit.text().strip()
        if name:
            self.group_created.emit(name, list(self._selected_ids))
        self.accept()
