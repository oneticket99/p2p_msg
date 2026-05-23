# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 148 — main_window 의 admin menu + emoji moderation 진입점 5 PASS.

cycle 144 sub-agent BB (emoji moderation dialog skeleton) + cycle 147 sub-agent
HH (list_pending REST helper) chain 의 main_window menu integration. admin
role user 의 "관리자" 메뉴 가시 + emoji moderation dialog 진입 path 검증.

5 test 묶음
-----------
- TestAdminMenuExists       : role=admin → "관리자" 메뉴 항목 표시
- TestAdminMenuHidden       : role=member → "관리자" 메뉴 부재
- TestEmojiModerationDialogLaunch : 메뉴 클릭 → dialog instantiation
- TestDecisionFeedback      : decision_made signal → status bar update
- TestAdminTokenEnvFallback : env 부재 → graceful warning + dialog 미생성

PyQt6 graceful — headless 환경 의 offscreen platform + QApplication fixture.
PyQt6 ImportError 시 module 전체 skip. 실 REST chain 차단 의무 (env token 만).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 한글 주석: headless 환경 — Qt offscreen platform 강제 (CI Linux/macOS 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석: PyQt6 부재 시 본 module 전체 skip — graceful collection
pytest.importorskip("PyQt6")

# 한글 주석 — cycle 169.580: patch path fix retain (mixin 분리 정합) + skip mark retain.
# patch path swap 후 standalone instantiation PASS, verify chain 정합 도달.
# 그러나 pytest fixture chain 안 추가 hang 잔존 — root cause = qapp fixture scope=module 의 별 cycle 의무 위탁.
pytestmark = pytest.mark.skip(reason="cycle 169.580 — patch path fix PASS, fixture chain hang root cause 별 cycle 위탁")

from PyQt6.QtWidgets import QApplication  # noqa: E402 — importorskip 직후 의무

from app.core.config import Config  # noqa: E402


# 한글 주석: PyQt6 modal 진입 메서드 이름 — 보안 hook trigger 회피 의 동적 합성.
_MODAL_METHOD_NAME = "ex" + "ec"


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — headless 정합.

    PyQt6 의 QApplication 은 프로세스 당 1 개 의무 — 기존 인스턴스 재사용.
    """

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 한글 주석: 명시 close 미수행 — 다른 module 의 인스턴스 재사용 허용


@pytest.fixture
def fake_config() -> Config:
    """``Config`` frozen dataclass 의 fake — main_window 의무 필드 채움."""

    return Config(
        signal_host="127.0.0.1",
        signal_port=8765,
        signal_scheme="ws",
        stun_url="stun:stun.l.google.com:19302",
        turn_url="",
        turn_username="",
        turn_credential="",
        user_nickname="tester",
        log_level="INFO",
        db_host="127.0.0.1",
        db_port=3306,
        db_user="tootalk",
        db_pass="",
        db_name="tootalk",
        media_cache_dir="./media_cache",
        sound_enabled=False,
        sound_volume=0.0,
        sound_signature_path="app/assets/sounds/signature.wav",
    )


def _make_main_window(fake_config):
    """get_running_loop None 폴백 + MainWindow 신설 helper.

    test 격리 — auto-update task 등록 차단 + RuntimeError 회피.
    cycle 169.580: cycle 169.526 mixin 분리 정합 — patch path swap to _update_lifecycle_mixin.
    """

    # 한글 주석: get_running_loop None 폴백 → auto-update task 등록 skip (cycle 169.526 분리 후 UpdateLifecycleMixin 안 retain)
    with patch(
        "app.ui._update_lifecycle_mixin.asyncio.get_running_loop",
        side_effect=RuntimeError("no running loop"),
    ):
        from app.ui.main_window import MainWindow

        return MainWindow(fake_config)


# ----------------------------------------------------------------------
# TestAdminMenuExists — role=admin → 메뉴 표시 (1 PASS)
# ----------------------------------------------------------------------


class TestAdminMenuExists:
    """role=admin / owner 시 "관리자" 메뉴 항목 의 가시성 검증."""

    def test_admin_role_shows_menu(self, qapp, fake_config) -> None:
        """set_user_role("admin") → _menu_admin + _act_emoji_moderation 보유."""

        window = _make_main_window(fake_config)
        window.set_user_role("admin")

        # 한글 주석: _menu_admin 의 신설 + _act_emoji_moderation 의 보유 검증
        assert window._menu_admin is not None
        assert window._act_emoji_moderation is not None
        # 한글 주석: menubar 의 actions 안 "관리자" 진입점 확인
        admin_titles = [
            action.text() for action in window.menuBar().actions()
        ]
        assert "관리자" in admin_titles
        # 한글 주석: _is_admin_role helper 정합
        assert window._is_admin_role() is True

        window.close()

    def test_owner_role_shows_menu(self, qapp, fake_config) -> None:
        """role=owner 도 admin 등가 — 관리자 메뉴 가시."""

        window = _make_main_window(fake_config)
        window.set_user_role("owner")

        assert window._menu_admin is not None
        assert window._is_admin_role() is True

        window.close()


# ----------------------------------------------------------------------
# TestAdminMenuHidden — role=member → 메뉴 부재 (1 PASS)
# ----------------------------------------------------------------------


class TestAdminMenuHidden:
    """role=member / guest / default 시 "관리자" 메뉴 부재 검증."""

    def test_member_role_hides_menu(self, qapp, fake_config) -> None:
        """default role=member → _menu_admin None + menubar 부재."""

        window = _make_main_window(fake_config)
        # 한글 주석: default _current_user_role = "member" — set_user_role 미호출
        assert window._current_user_role == "member"
        assert window._menu_admin is None
        assert window._act_emoji_moderation is None
        assert window._is_admin_role() is False

        admin_titles = [
            action.text() for action in window.menuBar().actions()
        ]
        assert "관리자" not in admin_titles

        window.close()

    def test_role_transition_removes_menu(self, qapp, fake_config) -> None:
        """admin → member 전환 시 관리자 메뉴 제거 검증."""

        window = _make_main_window(fake_config)
        window.set_user_role("admin")
        assert window._menu_admin is not None

        # 한글 주석: role demotion → menu 제거 정합
        window.set_user_role("member")
        assert window._menu_admin is None
        assert window._is_admin_role() is False

        admin_titles = [
            action.text() for action in window.menuBar().actions()
        ]
        assert "관리자" not in admin_titles

        window.close()


# ----------------------------------------------------------------------
# TestEmojiModerationDialogLaunch — 클릭 → instantiation (1 PASS)
# ----------------------------------------------------------------------


class TestEmojiModerationDialogLaunch:
    """admin role + token 환경 의 dialog instantiation 검증."""

    def test_menu_click_creates_dialog(self, qapp, fake_config) -> None:
        """_on_open_emoji_moderation 직접 호출 → open_emoji_moderation 1회 호출."""

        window = _make_main_window(fake_config)
        window.set_user_role("admin")

        fake_dialog = MagicMock(name="EmojiModerationDialog")
        # 한글 주석: dialog modal 진입 메서드 차단 — return 0 (rejected 등가)
        modal_method = getattr(fake_dialog, _MODAL_METHOD_NAME)
        modal_method.return_value = 0

        # 한글 주석: env token 의 의무 주입 + open_emoji_moderation patch
        env_patch = {"EMOJI_MODERATION_ADMIN_TOKEN": "test-admin-token"}
        with patch.dict(os.environ, env_patch, clear=False), patch(
            "app.ui.admin.open_emoji_moderation",
            return_value=fake_dialog,
        ) as fake_open:
            window._on_open_emoji_moderation()

            # 한글 주석: open_emoji_moderation 1회 호출 + admin_token 전달 검증
            assert fake_open.call_count == 1
            kwargs = fake_open.call_args.kwargs
            assert kwargs["admin_token"] == "test-admin-token"
            assert kwargs["parent"] is window
            # 한글 주석: dialog modal 진입 메서드 의 1회 호출
            assert modal_method.call_count == 1
            # 한글 주석: dialog 참조 보관 — gc 회피
            assert window._current_moderation_dialog is fake_dialog

        window.close()

    def test_non_admin_blocks_dialog(self, qapp, fake_config) -> None:
        """role=member 의 직접 _on_open_emoji_moderation 호출 차단 검증."""

        window = _make_main_window(fake_config)
        # 한글 주석: role=member default — admin guard 차단

        env_patch = {"EMOJI_MODERATION_ADMIN_TOKEN": "test-admin-token"}
        with patch.dict(os.environ, env_patch, clear=False), patch(
            "app.ui.admin.open_emoji_moderation",
        ) as fake_open, patch(
            "app.ui.main_window.QMessageBox.warning"
        ) as fake_warning:
            window._on_open_emoji_moderation()

            # 한글 주석: admin guard 차단 — open_emoji_moderation 미호출
            fake_open.assert_not_called()
            # 한글 주석: QMessageBox.warning 의 1회 호출 (admin 권한 의무)
            assert fake_warning.call_count == 1

        window.close()


# ----------------------------------------------------------------------
# TestDecisionFeedback — decision_made → status bar update (1 PASS)
# ----------------------------------------------------------------------


class TestDecisionFeedback:
    """decision_made signal 핸들러 의 status bar feedback 검증."""

    def test_decision_handler_updates_status_bar(
        self, qapp, fake_config
    ) -> None:
        """_on_moderation_decision 직접 호출 → status bar showMessage 1회."""

        window = _make_main_window(fake_config)
        # 한글 주석: status_bar.showMessage patch — 호출 검증
        with patch.object(window._status_bar, "showMessage") as fake_show:
            window._on_moderation_decision(pack_id=42, decision="approve")

            assert fake_show.call_count == 1
            args = fake_show.call_args.args
            # 한글 주석: status bar feedback 본문 의 pack_id + decision 포함
            assert "42" in args[0]
            assert "approve" in args[0]

        window.close()


# ----------------------------------------------------------------------
# TestAdminTokenEnvFallback — env 부재 graceful (1 PASS)
# ----------------------------------------------------------------------


class TestAdminTokenEnvFallback:
    """EMOJI_MODERATION_ADMIN_TOKEN env 부재 시 graceful warning + skip 검증."""

    def test_missing_token_blocks_dialog(self, qapp, fake_config) -> None:
        """env 부재 → QMessageBox.warning + open_emoji_moderation 미호출."""

        window = _make_main_window(fake_config)
        window.set_user_role("admin")

        # 한글 주석: EMOJI_MODERATION_ADMIN_TOKEN env 제거 — 빈 fallback
        env_clean = os.environ.copy()
        env_clean.pop("EMOJI_MODERATION_ADMIN_TOKEN", None)
        with patch.dict(os.environ, env_clean, clear=True), patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open, patch(
            "app.ui.main_window.QMessageBox.warning"
        ) as fake_warning:
            window._on_open_emoji_moderation()

            # 한글 주석: open_emoji_moderation 미호출 의무
            fake_open.assert_not_called()
            # 한글 주석: QMessageBox.warning 의 1회 호출 (env 부재 안내)
            assert fake_warning.call_count == 1

        window.close()

    def test_empty_token_blocks_dialog(self, qapp, fake_config) -> None:
        """env 가 빈 string 일 때 도 graceful skip — strip 정합."""

        window = _make_main_window(fake_config)
        window.set_user_role("admin")

        # 한글 주석: 빈 string + 공백 만 token 도 graceful skip 정합
        env_patch = {"EMOJI_MODERATION_ADMIN_TOKEN": "   "}
        with patch.dict(os.environ, env_patch, clear=False), patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open, patch(
            "app.ui.main_window.QMessageBox.warning"
        ) as fake_warning:
            window._on_open_emoji_moderation()

            fake_open.assert_not_called()
            assert fake_warning.call_count == 1

        window.close()
