# SPDX-License-Identifier: GPL-3.0-or-later
"""UI dialog batch 7 isolated — cycle 169.735 신설.

ThemePicker + FolderEditDialog + MyAccountDialog construct + state.
"""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestThemePicker:
    def test_construct_auto_default(self, qapp) -> None:
        from app.ui.theme_picker import ThemePicker

        tp = ThemePicker()
        # 한글 주석 — auto default active
        assert tp._buttons["auto"].isChecked() is True
        assert tp._buttons["dark"].isChecked() is False
        tp.close()

    def test_3_modes(self, qapp) -> None:
        from app.ui.theme_picker import ThemePicker

        tp = ThemePicker()
        assert set(tp._buttons.keys()) == {"dark", "light", "auto"}
        tp.close()

    def test_exclusive_group(self, qapp) -> None:
        from app.ui.theme_picker import ThemePicker

        tp = ThemePicker()
        assert tp._group.exclusive() is True
        tp.close()


class TestFolderEditDialog:
    def test_construct_new_mode(self, qapp) -> None:
        from app.ui.folder_edit_dialog import FolderEditDialog

        d = FolderEditDialog()
        # 한글 주석 — folder_id 부재 → 새 폴더 title
        assert "새 폴더" in d.windowTitle()
        assert d.width() == 336
        assert d.height() == 600
        d.close()

    def test_construct_edit_mode(self, qapp) -> None:
        from app.ui.folder_edit_dialog import FolderEditDialog

        existing = {"folder_id": "fav", "name": "Favorites",
                    "included_chats": [1, 2], "excluded_chats": []}
        d = FolderEditDialog(existing=existing)
        assert "폴더 수정" in d.windowTitle()
        assert d._included_chats == [1, 2]
        d.close()

    def test_color_name_retained(self, qapp) -> None:
        from app.ui.folder_edit_dialog import FolderEditDialog

        d = FolderEditDialog(existing={"folder_id": "x", "color_name": "blue"})
        assert d._selected_color == "blue"
        d.close()


class TestMyAccountDialog:
    def test_construct(self, qapp) -> None:
        from app.ui.my_account_dialog import MyAccountDialog

        d = MyAccountDialog(
            email="x@x.com", username="alice", phone="010-1234",
            bio="hi", birthdate="2000-01-01", display_name="Alice",
        )
        assert "내 계정" in d.windowTitle()
        assert d.width() == 420
        assert d.height() == 600
        d.close()

    def test_construct_empty(self, qapp) -> None:
        from app.ui.my_account_dialog import MyAccountDialog

        d = MyAccountDialog()
        assert d is not None
        d.close()
