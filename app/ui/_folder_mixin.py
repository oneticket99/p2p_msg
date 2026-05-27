# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderMixin — folder CRUD chain (cycle 169.523 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
folder 선택/생성/편집/삭제 → FolderEditDialog + ChatPickerDialog + FolderClient REST 결선.

codex 2.5 HIGH 진입 9차 — main_window.py 책임 분리.
잔존 method group 中 isolated scope (160 line).

분리 대상 method (cycle 169.75~411 origin):
- `_on_folder_selected(folder_id)` — folder click → chat_list filter or edit popup
- `_on_folder_create_requested()` — 새 폴더 만들기 FolderEditDialog
- `_open_chat_picker(edit_dialog, mode)` — ChatPickerDialog popup
- `_on_folder_saved(folder_data)` — folder data persist + REST POST/PATCH chain
- `_on_folder_persist_finished(ok, code, msg, data)` — REST callback
- `_on_folder_edit_requested(folder_id)` — folder edit FolderEditDialog
- `_on_folder_delete_requested(folder_id)` — folder DELETE chain

본 mixin 안 의존 attribute:
- `_user_folders`, `_active_folder_dialog`, `_folder_workers`
- `_chat_list_panel`, `_sidebar_rail`, `_auth_client`, `_auth_token`
- `_exec_dialog_centered` helper (main_window retain)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class FolderMixin:
    """folder CRUD chain mixin (cycle 169.523)."""

    def _on_folder_selected(self, folder_id: str) -> None:
        """folder click → chat_list_panel filter or edit popup (cycle 169.75)."""
        log.info("[main_window] folder_selected — folder_id=%s", folder_id)
        if folder_id == "edit":
            from app.ui.folder_manage_dialog import FolderManageDialog
            user_folders = getattr(self, "_user_folders", [])
            dialog = FolderManageDialog(user_folders=user_folders, parent=self)
            dialog.folder_create_requested.connect(self._on_folder_create_requested)  # type: ignore[arg-type]
            dialog.folder_delete_requested.connect(self._on_folder_delete_requested)  # type: ignore[arg-type]
            dialog.folder_edit_requested.connect(self._on_folder_edit_requested)  # type: ignore[arg-type]
            # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
            self._exec_dialog_centered(dialog)
            return
        if hasattr(self, "_chat_list_panel"):
            self._chat_list_panel.set_active_folder(folder_id)

    @pyqtSlot()
    def _on_folder_create_requested(self) -> None:
        """새 폴더 만들기 → FolderEditDialog popup (cycle 169.75)."""
        from app.ui.folder_edit_dialog import FolderEditDialog
        dialog = FolderEditDialog(parent=self)
        dialog.folder_saved.connect(self._on_folder_saved)  # type: ignore[arg-type]
        dialog.chat_picker_requested.connect(  # type: ignore[arg-type]
            lambda mode: self._open_chat_picker(dialog, mode)
        )
        self._exec_dialog_centered(dialog)

    def _open_chat_picker(self, edit_dialog, mode: str) -> None:
        """FolderEditDialog 안 대화방 추가 click → ChatPickerDialog."""
        from app.ui.chat_picker_dialog import ChatPickerDialog
        entries = list(getattr(self._chat_list_panel, "_entries", []))
        picker = ChatPickerDialog(chat_entries=entries, mode=mode, parent=edit_dialog)

        def _on_selected(chats):
            if mode == "include":
                edit_dialog.add_included_chats(chats)
            else:
                edit_dialog.add_excluded_chats(chats)
        picker.chats_selected.connect(_on_selected)  # type: ignore[arg-type]
        self._exec_dialog_centered(picker)

    @pyqtSlot(dict)
    def _on_folder_saved(self, folder_data: dict) -> None:
        """FolderEditDialog 만들기 PASS → user_folders append/replace + REST 영속화 + sidebar refresh.

        cycle 169.388 — edit mode (_is_edit flag retain 시점 기존 folder replace + UPDATE chain).
        """
        if not hasattr(self, "_user_folders"):
            self._user_folders = []
        is_edit = folder_data.pop("_is_edit", False)
        if is_edit:
            target_fid = str(folder_data.get("folder_id", ""))
            self._user_folders = [
                folder_data if str(f.get("folder_id", "")) == target_fid else f
                for f in self._user_folders
            ]
            if not any(str(f.get("folder_id", "")) == target_fid for f in self._user_folders):
                self._user_folders.append(folder_data)
        else:
            self._user_folders.append(folder_data)
        log.warning(
            "[folder_saved] name=%s included=%d excluded=%d included_data=%s",
            folder_data.get("name"),
            len(folder_data.get("included_chats", [])),
            len(folder_data.get("excluded_chats", [])),
            folder_data.get("included_chats", [])[:3],
        )
        # cycle 169.373 — sidebar_rail folder entry 동적 갱신
        if hasattr(self, "_sidebar_rail") and hasattr(self._sidebar_rail, "set_folder_entries"):
            try:
                self._sidebar_rail.set_folder_entries(self._user_folders)
            except Exception as exc:
                log.debug("sidebar_rail set_folder_entries fail — %r", exc)
        # cycle 169.378 — chat_list_panel folder metadata sync
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None and hasattr(clp, "set_user_folders"):
            try:
                clp.set_user_folders(self._user_folders)
            except Exception as exc:
                log.debug("chat_list_panel set_user_folders fail — %r", exc)
        # cycle 169.373 — active FolderManageDialog close chain
        active_folder_dialog = getattr(self, "_active_folder_dialog", None)
        if active_folder_dialog is not None:
            try:
                active_folder_dialog.reject()
            except Exception:
                pass
            self._active_folder_dialog = None
        # cycle 169.77 — FolderCreateWorker REST 영속화 chain
        base_url = getattr(self._auth_client, "_base_url", "") if self._auth_client else ""
        token = getattr(self, "_auth_token", None)
        if not base_url or not token:
            log.warning("[folder] base_url/token 부재 — REST 영속화 skip")
            return
        # cycle 169.411 — edit mode PATCH endpoint chain
        if is_edit:
            from app.net.folder_client import FolderUpdateWorker
            target_fid = str(folder_data.get("folder_id", ""))
            worker = FolderUpdateWorker(base_url, token, target_fid, folder_data, parent=self)
        else:
            from app.net.folder_client import FolderCreateWorker
            worker = FolderCreateWorker(base_url, token, folder_data, parent=self)
        worker.finished_with_result.connect(self._on_folder_persist_finished)  # type: ignore[arg-type]
        # cycle 169.79 — worker list append (dangling 차단)
        if not hasattr(self, "_folder_workers"):
            self._folder_workers = []
        self._folder_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._folder_workers.remove(w))  # type: ignore[arg-type]
        worker.start()

    @pyqtSlot(bool, str, str, dict)
    def _on_folder_persist_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """FolderCreateWorker finished — log + folder_id 갱신."""
        if ok:
            log.info("[folder] REST 영속화 PASS — id=%s", data.get("id"))
        else:
            log.warning("[folder] REST 영속화 실패 — code=%s msg=%s", error_code, error_message)

    @pyqtSlot(str)
    def _on_folder_edit_requested(self, folder_id: str) -> None:
        """folder edit click → FolderEditDialog open with existing data (cycle 169.381)."""
        user_folders = getattr(self, "_user_folders", [])
        existing = next((f for f in user_folders if str(f.get("folder_id", "")) == folder_id), None)
        if existing is None:
            log.warning("[folder_edit] folder_id=%s 부재", folder_id)
            return
        from app.ui.folder_edit_dialog import FolderEditDialog
        dialog = FolderEditDialog(existing=existing, parent=self)
        dialog.folder_saved.connect(self._on_folder_saved)  # type: ignore[arg-type]
        dialog.chat_picker_requested.connect(
            lambda mode: self._open_chat_picker(dialog, mode)
        )  # type: ignore[arg-type]
        self._exec_dialog_centered(dialog)

    @pyqtSlot(str)
    def _on_folder_delete_requested(self, folder_id: str) -> None:
        """folder delete request + REST DELETE chain (cycle 169.77)."""
        user_folders = getattr(self, "_user_folders", [])
        self._user_folders = [f for f in user_folders if f.get("folder_id") != folder_id]
        log.info("[main_window] folder deleted — folder_id=%s", folder_id)
        base_url = getattr(self._auth_client, "_base_url", "") if self._auth_client else ""
        token = getattr(self, "_auth_token", None)
        if not base_url or not token:
            return
        from app.net.folder_client import FolderDeleteWorker
        worker = FolderDeleteWorker(base_url, token, folder_id, parent=self)
        worker.finished_with_result.connect(  # type: ignore[arg-type]
            lambda ok, *_: log.info("[folder] DELETE finished ok=%s", ok)
        )
        # cycle 169.79 — worker list append
        if not hasattr(self, "_folder_workers"):
            self._folder_workers = []
        self._folder_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._folder_workers.remove(w))  # type: ignore[arg-type]
        worker.start()
