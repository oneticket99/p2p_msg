# SPDX-License-Identifier: GPL-3.0-or-later
"""MainWindow 21 mixin MRO regression guard (cycle 169.534 신설).

codex 2.8 reviewer finding 의무 회수 — neutral assert chain.

본 test = main_window 책임 분리 phase 본격 종료 후 (cycle 169.530, 4026 → 600 line, 85.1%)
21 mixin + 9 init helper 의 의무 MRO resolution 의무 stable 의무 guard.

규칙:
- MainWindow class signature 안 21 mixin 다중 상속 정합 의무 (cycle 169.529 final)
- cross-mixin 22 method ALL resolved at runtime (codex 2.8 reviewer 검증)
- 9 __init__ helper method ALL present (cycle 169.530 split)

본 test 의 break = 신규 mixin 추가 시점 의무 MRO 순서 break detect.
"""

from __future__ import annotations


def test_main_window_mro_21_mixin_present() -> None:
    """MainWindow MRO 안 21 mixin 정합 — codex 2.8 reviewer 회수."""
    from app.ui.main_window import MainWindow

    mro_names = {c.__name__ for c in MainWindow.__mro__}
    expected_mixins = {
        "TrayMixin", "FriendSearchMixin", "BotChatMixin", "DrawerMixin",
        "ChatHelperMixin", "MenuBarMixin", "SignalingMixin",
        "RoomGroupChatMixin", "RestPostMixin", "FolderMixin",
        "ChatHeaderMixin", "UpdateLifecycleMixin", "AuthChainMixin",
        "ChatNavigationMixin", "FriendProfileMixin", "ChatSendMixin",
        "DialogCenterMixin", "MenuActionsMixin", "InviteMixin",
        "LifecycleEventsMixin", "FriendStatusMixin",
    }
    missing = expected_mixins - mro_names
    assert not missing, f"missing mixin in MRO: {missing}"


def test_main_window_22_cross_mixin_methods_resolved() -> None:
    """22 cross-mixin call site ALL resolved at runtime (codex 2.8 verify)."""
    from app.ui.main_window import MainWindow

    methods = set(dir(MainWindow))
    expected = {
        # ChatHelper → RestPost
        "_mark_room_read",
        # ChatSend → ChatHelper / RestPost / BotChat
        "_kind_room_local", "_post_and_resolve", "_send_bot_message",
        "_send_saved_message_rest",
        # ChatNav → FriendStatus / ChatHelper / BotChat
        "_fetch_user_status", "_fetch_dm_history", "_fetch_bot_history",
        "_load_local_history",
        # Lifecycle → UpdateLifecycle
        "_cancel_update_task",
        # FriendSearch → AuthChain / ChatHelper / FriendSearch
        "_post_login_refresh", "_fetch_unread_counts",
        "_refresh_pending_badge", "_refresh_chat_list_panel",
        # BotChat → ChatSend
        "_append_dm_message",
        # RoomGroup → DialogCenter
        "_exec_dialog_centered",
        # Tray → main_window startup
        "_perform_logout_and_relogin", "_setup_tray_icon",
        # MenuBar / UpdateLifecycle
        "_start_update_check_task", "_build_menu_bar",
        # cycle 169.845 M5 — legacy GroupChatView 경로(_on_room_entered +
        # _dispatch_message_chain) 회수로 cross-mixin 기대 목록에서 제거.
        # 멤버 보기 in-app 모달 진입점 유지.
        "_on_open_members_panel",
    }
    missing = expected - methods
    assert not missing, f"unresolved cross-mixin method: {missing}"


def test_main_window_9_init_helper_present() -> None:
    """__init__ 9 helper method split 정합 (cycle 169.530)."""
    from app.ui.main_window import MainWindow

    methods = set(dir(MainWindow))
    expected_helpers = {
        "_init_state", "_init_window_properties", "_init_splitter",
        "_init_sidebar_rail", "_init_chat_list_panel", "_init_right_panel",
        "_init_input_bar", "_finalize_splitter",
        "_init_status_and_startup_chain",
    }
    missing = expected_helpers - methods
    assert not missing, f"missing __init__ helper: {missing}"


def test_main_window_mro_terminates_qmainwindow() -> None:
    """MRO 마지막 = QMainWindow → QWidget → QObject → object chain 정합."""
    from app.ui.main_window import MainWindow

    mro_names = [c.__name__ for c in MainWindow.__mro__]
    # 한글 주석 — MainWindow 가 21 mixin + QMainWindow 다중 상속 의무
    assert mro_names[0] == "MainWindow"
    assert "QMainWindow" in mro_names
    assert mro_names[-1] == "object"
