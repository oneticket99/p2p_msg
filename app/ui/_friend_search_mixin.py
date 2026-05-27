# SPDX-License-Identifier: GPL-3.0-or-later
"""FriendSearchMixin — 친구 검색 + 요청 + pending list + badge chain (cycle 169.511 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
AddFriendDialog/PendingRequestsDialog + FriendsClient(search/request/list_pending) 결선 + badge 갱신.

codex 2.5 HIGH 진입 2차 — `app/ui/main_window.py` 책임 분리 의 2차.
TrayMixin (cycle 169.509) 등가 패턴.

분리 대상 method (cycle 169.489~500 origin):
- `_on_open_add_friend()` — AddFriendDialog 모달 spawn
- `_on_friend_search_requested(keyword)` — FriendsClient.search_users async
- `_on_friend_requested(user_id, nickname)` — REST POST + Conflict 분기
- `_on_open_pending_requests()` — PendingRequestsDialog 모달 + list_pending
- `_on_pending_resolved(user_id, accepted)` — accept/reject 결과 + badge refresh
- `_refresh_pending_badge()` — sidebar count badge fetch chain

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_session_token`, `_friends_client`, `_status_bar`, `_sidebar_rail`
- `_add_friend_dlg_ref` (Optional)
- `_post_login_refresh()` (resolved 후 fetch chain)
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

# cycle 169.834 — user-facing 문구 i18n 바인딩 (5언어 labels)
from app.i18n import labels as _i18n_labels

if TYPE_CHECKING:
    from app.ui.add_friend_dialog import AddFriendDialog

log = logging.getLogger(__name__)


class FriendSearchMixin:
    """친구 검색 + 요청 + pending chain mixin (cycle 169.511)."""

    def _on_open_add_friend(self) -> None:
        """"친구 추가" 메뉴 슬롯 — AddFriendDialog 의 모달 실행."""
        from app.ui.add_friend_dialog import AddFriendDialog

        if self._session_token is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", _i18n_labels.tr("msg_login_required_add_friend")
            )
            return

        dlg = AddFriendDialog(parent=self)
        # cycle 169.489 — search_requested wire fix
        self._add_friend_dlg_ref = dlg
        dlg.search_requested.connect(self._on_friend_search_requested)
        dlg.friend_requested.connect(self._on_friend_requested)
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(dlg)
        self._add_friend_dlg_ref = None

    def _on_friend_search_requested(self, keyword: str) -> None:
        """AddFriendDialog search_requested 슬롯 — FriendsClient.search_users + set_search_results.

        cycle 169.489 origin — 검색 wire 부재 회수. friends_client 부재 graceful skip.
        """
        from app.ui.add_friend_dialog import SearchResult

        log.info("[main_window] friend_search_requested keyword=%r", keyword)
        dlg = getattr(self, "_add_friend_dlg_ref", None)
        if dlg is None:
            log.warning("[friend_search] dlg ref 부재 — skip")
            return
        fc = getattr(self, "_friends_client", None)
        if fc is None or self._session_token is None:
            log.warning("[friend_search] friends_client/session_token 부재 — skip")
            dlg.set_search_results([])
            return

        async def _do_search() -> None:
            try:
                results = await fc.search_users(keyword=keyword, limit=20)
                ui_results = [
                    SearchResult(
                        user_id=int(r.id),
                        username=str(r.username),
                        display_name=str(getattr(r, "display_name", "")),
                        nickname=str(getattr(r, "nickname", "")),
                        email_verified=bool(r.email_verified),
                    )
                    for r in results
                ]
                dlg.set_search_results(ui_results)
                log.info("[friend_search] count=%d", len(ui_results))
            except Exception as exc:  # noqa: BLE001
                log.warning("[friend_search] fail — %r", exc)
                dlg.set_search_results([])

        try:
            asyncio.ensure_future(_do_search())
        except Exception as exc:  # noqa: BLE001
            log.warning("[friend_search] spawn fail — %r", exc)

    def _on_friend_requested(self, user_id: int, nickname: str) -> None:
        """AddFriendDialog 의 friend_requested 시그널 수신 — REST POST + Conflict 분기 (cycle 169.496)."""
        log.info("[main_window] friend_requested user_id=%d nickname=%r", user_id, nickname)
        fc = getattr(self, "_friends_client", None)
        if fc is None or self._session_token is None:
            log.warning("[friend_request] friends_client/session_token 부재 — skip")
            self._status_bar.showMessage(
                _i18n_labels.tr("msg_friend_request_no_auth"), 3000
            )
            return

        async def _do_request() -> None:
            dlg = getattr(self, "_add_friend_dlg_ref", None)
            from app.ui.confirm_dialog import ConfirmDialog
            from app.net.friends_client import (
                FriendsConflictError,
                FriendsBadRequestError,
                FriendsNotFoundError,
                FriendsAuthError,
            )
            try:
                friend_id = await fc.request_friend(user_id, nickname or None)
                log.info("[friend_request] PASS friend_row_id=%d", friend_id)
                self._status_bar.showMessage(
                    _i18n_labels.tr("msg_friend_request_sent_status").format(
                        user_id=user_id
                    ),
                    3000,
                )
                if dlg is not None:
                    dlg.accept()
                ConfirmDialog.show_info(
                    self, "친구 추가", _i18n_labels.tr("msg_friend_request_sent")
                )
            except FriendsConflictError:
                log.info("[friend_request] 이미 친구 또는 pending 상태")
                if dlg is not None:
                    dlg.accept()
                # 사용자 directive 2026-05-22 — 이미 요청된 상대 안내
                ConfirmDialog.show_info(
                    self,
                    "친구 추가",
                    "이미 요청된 상대입니다.\n상대방이 수락하면 채팅리스트에 자동 추가됩니다.",
                )
            except FriendsBadRequestError as exc:
                log.warning("[friend_request] bad request — %r", exc)
                ConfirmDialog.show_warning(self, "친구 추가", f"요청 형식 오류: {exc}")
            except FriendsNotFoundError:
                ConfirmDialog.show_warning(self, "친구 추가", "사용자 미존재")
            except FriendsAuthError:
                ConfirmDialog.show_warning(self, "친구 추가", "인증 만료 — 다시 로그인")
            except Exception as exc:  # noqa: BLE001
                log.warning("[friend_request] fail — %r", exc)
                ConfirmDialog.show_warning(
                    self, "친구 추가", f"요청 실패: {exc.__class__.__name__}"
                )

        try:
            asyncio.ensure_future(_do_request())
        except Exception as exc:  # noqa: BLE001
            log.warning("[friend_request] spawn fail — %r", exc)

    def _on_open_pending_requests(self) -> None:
        """"받은 친구 요청" 메뉴 슬롯 — PendingRequestsDialog 모달 + list_pending async.

        cycle 169.499 origin — 친구 요청 수락 chain 본격 binding.
        """
        if self._session_token is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", _i18n_labels.tr("msg_login_required_pending")
            )
            return
        from app.ui.pending_requests_dialog import PendingRequestsDialog

        dlg = PendingRequestsDialog(friends_client=self._friends_client, parent=self)
        dlg.request_resolved.connect(self._on_pending_resolved)  # type: ignore[arg-type]
        fc = self._friends_client
        if fc is not None:
            async def _populate() -> None:
                try:
                    items = await fc.list_pending()
                    dlg.populate(items)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[pending] list_pending fail — %r", exc)
                    dlg.populate([])
            try:
                asyncio.ensure_future(_populate())
            except Exception as exc:  # noqa: BLE001
                log.warning("[pending] spawn fail — %r", exc)
        else:
            dlg.populate([])
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(dlg)

    def _on_pending_resolved(self, user_id: int, accepted: bool) -> None:
        """accept/reject 결과 처리 — friend list refresh + badge 갱신."""
        log.info("[pending] resolved user_id=%d accepted=%s", user_id, accepted)
        if accepted:
            try:
                self._post_login_refresh()
            except Exception as exc:
                log.debug("[pending] post-resolve refresh 실패 — %r", exc)
        try:
            asyncio.ensure_future(self._refresh_pending_badge())
        except Exception:
            pass

    async def _refresh_pending_badge(self) -> None:
        """sidebar 햄버거 menu pending count badge 갱신 (cycle 169.500 origin)."""
        fc = getattr(self, "_friends_client", None)
        if fc is None or self._session_token is None:
            return
        try:
            items = await fc.list_pending()
            count = len(items) if items else 0
            if hasattr(self, "_sidebar_rail") and hasattr(self._sidebar_rail, "set_pending_count"):
                self._sidebar_rail.set_pending_count(count)
            log.info("[pending_badge] count=%d", count)
        except Exception as exc:  # noqa: BLE001
            log.debug("[pending_badge] fetch fail — %r", exc)
