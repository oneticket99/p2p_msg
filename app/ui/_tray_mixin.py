# SPDX-License-Identifier: GPL-3.0-or-later
"""TrayMixin — system tray icon + logout/quit + LoginDialog re-spawn chain (cycle 169.509 신설).

codex review 2.5 verdict 정합 — `app/ui/main_window.py` 4000줄 책임 분리 의 1차 진입.
본 mixin 안 6 method retain — MainWindow 의 multiple inheritance pattern.

분리 대상 method (cycle 169.498 origin):
- `_setup_tray_icon()` — QSystemTrayIcon + QMenu 3 entry + setQuitOnLastWindowClosed
- `_on_tray_activated(reason)` — LMB Trigger/DoubleClick restore
- `_on_tray_show()` — window restore
- `_on_tray_logout()` — logout + relogin dispatch
- `_on_tray_quit()` — QApplication.quit() + tray hide
- `_perform_logout_and_relogin()` — session 폐기 + LoginDialog modal + post_login_refresh

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_tray_icon` (Optional[QSystemTrayIcon])
- `_tray_quit_requested` (bool)
- `_session_token`, `_current_user_id`, `_auth_token`, `_friends_client`
- `_status_bar` (set_connection_state method)
- `_auth_client` (LoginDialog 안 의존성)
- `_post_login_refresh` (relogin 후 fetch chain)
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


class TrayMixin:
    """system tray + logout/quit chain mixin (cycle 169.509).

    MainWindow MRO 안 본 mixin 가 retain — `class MainWindow(TrayMixin, QMainWindow)`.
    """

    def _setup_tray_icon(self) -> None:
        """QSystemTrayIcon + QMenu (로그아웃 + TooTalk 종료) 신설.

        사용자 directive 2026-05-22 — close button = hide + tray retain.
        tray RMB → context menu drop-down. logout → LoginDialog re-spawn.
        """
        try:
            from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
            from PyQt6.QtGui import QIcon, QPixmap
            if not QSystemTrayIcon.isSystemTrayAvailable():
                log.warning("[tray] system tray 미가용 — skip")
                return
            # 한글 주석 — TooTalk symbol PNG icon (이미 bundle 안 retain)
            ROOT = Path(__file__).resolve().parent.parent
            icon_path = ROOT / "assets" / "branding" / "tootalk_symbol.png"
            if icon_path.exists():
                pix = QPixmap(str(icon_path))
                if not pix.isNull():
                    icon = QIcon(pix)
                else:
                    icon = self.windowIcon() or QIcon()
            else:
                icon = self.windowIcon() or QIcon()
            self._tray_icon = QSystemTrayIcon(icon, self)
            self._tray_icon.setToolTip("TooTalk")
            menu = QMenu(self)
            act_show = menu.addAction("TooTalk 열기")
            act_show.triggered.connect(self._on_tray_show)  # type: ignore[arg-type]
            menu.addSeparator()
            act_logout = menu.addAction("로그아웃")
            act_logout.triggered.connect(self._on_tray_logout)  # type: ignore[arg-type]
            menu.addSeparator()
            act_quit = menu.addAction("TooTalk 종료")
            act_quit.triggered.connect(self._on_tray_quit)  # type: ignore[arg-type]
            self._tray_icon.setContextMenu(menu)
            # 한글 주석 — LMB double-click = restore window (사용자 직관 정합)
            self._tray_icon.activated.connect(self._on_tray_activated)  # type: ignore[arg-type]
            self._tray_icon.show()
            # 한글 주석 — close → quit 차단 (tray retain). _on_tray_quit 만 quit trigger
            QApplication.instance().setQuitOnLastWindowClosed(False)
            log.info("[tray] icon ready — path=%s", icon_path)
        except Exception as exc:  # noqa: BLE001 - graceful
            log.warning("[tray] setup 실패 — %r", exc)

    def _on_tray_activated(self, reason) -> None:
        """tray icon LMB / double-click → window restore."""
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.Trigger):
            self._on_tray_show()

    def _on_tray_show(self) -> None:
        """tray menu "TooTalk 열기" + LMB activate → MainWindow restore."""
        try:
            self.showNormal()
            self.raise_()
            self.activateWindow()
        except Exception as exc:  # noqa: BLE001 - graceful
            log.debug("[tray] show 실패 — %r", exc)

    def _on_tray_logout(self) -> None:
        """tray menu "로그아웃" → session 폐기 + LoginDialog re-spawn."""
        log.info("[tray] logout 진입")
        self._perform_logout_and_relogin()

    def _on_tray_quit(self) -> None:
        """tray menu "TooTalk 종료" → app quit."""
        log.info("[tray] quit 진입")
        from PyQt6.QtWidgets import QApplication
        self._tray_quit_requested = True
        try:
            if self._tray_icon is not None:
                self._tray_icon.hide()
        except Exception:  # pragma: no cover
            pass
        QApplication.instance().quit()

    def _perform_logout_and_relogin(self) -> None:
        """세션 폐기 + LoginDialog modal re-spawn + 신규 session token swap.

        cycle 169.498 origin — tray logout + menu logout 공통 chain.
        """
        # 한글 주석 — 1) session 폐기
        self._session_token = None
        self._current_user_id = None
        self._auth_token = None
        # cycle 169.831 — 로그아웃 시 계정 메뉴 가시성 재토글 (회원가입/로그인 복귀)
        if hasattr(self, "apply_auth_menu_visibility"):
            self.apply_auth_menu_visibility()
        # friends_client token retain 만 폐기 (instance 보존 + 신규 login 시 swap)
        try:
            fc = getattr(self, "_friends_client", None)
            if fc is not None:
                # 한글 주석 — 내부 client + token 의 reset (다음 _ensure_client 시점 신규 instantiate)
                try:
                    import asyncio as _aio
                    _aio.ensure_future(fc.close())
                except Exception:
                    pass
                fc._token = ""  # type: ignore[attr-defined]
                fc._client = None  # type: ignore[attr-defined]
        except Exception:
            pass
        # 한글 주석 — 2) UI lock — chat_view + status bar feedback
        try:
            self._status_bar.set_connection_state("DISCONNECTED")
        except Exception:
            pass
        # 한글 주석 — 3) LoginDialog modal re-spawn
        # cycle 169.838 scope-out — 재인증(로그아웃 후) chain 은 in-app overlay 모달 directive
        # 예외다. (1) startup auth bootstrap(app/main.py)과 동일한 재인증 단계이고,
        # (2) login↔signup 전환을 위해 custom done() code(res==2/3)를 사용하는데
        # _exec_dialog_centered 는 accept=1/reject=0 만 반환해 전환 code 가 손실된다.
        # 따라서 별도 윈도우 .exec() 를 유지한다(FRONTEND.md 모달 정책 §예외 참조).
        try:
            from app.ui.login_dialog import LoginDialog
            from app.ui.signup_dialog import SignupDialog
            auth_client = self._auth_client
            if auth_client is None:
                log.warning("[logout] auth_client 부재 — login dialog skip")
                return
            authenticated = False
            current = "login"
            while not authenticated:
                if current == "login":
                    dlg = LoginDialog(auth_client=auth_client)
                    res = dlg.exec()
                    if res == 2:
                        current = "signup"
                        continue
                    if res != dlg.DialogCode.Accepted:
                        log.info("[logout] login 취소 — app quit")
                        self._on_tray_quit()
                        return
                    self._session_token = dlg.token
                    self._current_user_id = dlg.user_id
                    self._auth_token = dlg.token
                    authenticated = True
                else:  # signup
                    sdlg = SignupDialog(auth_client=auth_client)
                    sres = sdlg.exec()
                    if sres == 3:
                        current = "login"
                        continue
                    if sres != sdlg.DialogCode.Accepted:
                        log.info("[logout] signup 취소 — app quit")
                        self._on_tray_quit()
                        return
                    self._session_token = sdlg.token
                    self._current_user_id = sdlg.user_id
                    authenticated = True
            # 한글 주석 — 4) friends_client token swap (cycle 169.494 정합)
            try:
                fc = getattr(self, "_friends_client", None)
                if fc is not None and self._session_token:
                    fc._token = self._session_token  # type: ignore[attr-defined]
                    fc._client = None  # type: ignore[attr-defined]
            except Exception:
                pass
            # 한글 주석 — 5) status bar + post_login refresh
            try:
                self._status_bar.set_connection_state("CONNECTED")
            except Exception:
                pass
            try:
                self._post_login_refresh()
            except Exception as exc:
                log.debug("[logout] post_login_refresh 실패 — %r", exc)
            self.showNormal()
            self.raise_()
            self.activateWindow()
            log.info("[logout] re-login PASS user_id=%s", self._current_user_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("[logout] LoginDialog re-spawn 실패 — %r", exc)
