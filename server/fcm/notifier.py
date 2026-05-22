# SPDX-License-Identifier: GPL-3.0-or-later
"""FCM Notifier — push notification dispatch chain (cycle 169.446 skeleton)."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Protocol

log = logging.getLogger(__name__)

_SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")


class Notifier(Protocol):
    """push notifier interface — async send."""

    async def send(
        self, token: str, *, title: str, body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        """단일 token 의 push send. 성공 = True / 실패 = False."""
        ...


class StubNotifier:
    """Firebase service account 부재 시점 graceful noop + log."""

    async def send(
        self, token: str, *, title: str, body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        log.info(
            "[fcm.stub] noop send — token=%s... title=%s body_len=%d data=%s",
            token[:16], title, len(body), data,
        )
        return False


class FCMNotifier:
    """Firebase Admin SDK actual binding (cycle 169.448 send chain 완성).

    chain:
    1. firebase_admin.initialize_app(credentials.Certificate(path)) — singleton
    2. messaging.Message(token=..., notification=..., data=...)
    3. messaging.send(msg) → message_id return
    4. UnregisteredError → caller deactivate_token chain (caller responsibility)
    """

    def __init__(self, service_account_path: str) -> None:
        self._sa_path = service_account_path
        self._initialized = False
        self._available = False
        try:
            import firebase_admin  # type: ignore[import]
            from firebase_admin import credentials  # type: ignore[import]
            try:
                firebase_admin.get_app()
                self._initialized = True
            except ValueError:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                self._initialized = True
                log.info("[fcm] firebase_admin initialize_app PASS — sa=%s", service_account_path)
            self._available = True
        except ImportError:
            log.warning("[fcm] firebase-admin SDK 부재 — stub fallback")
        except Exception as exc:
            log.warning("[fcm] init 실패 — %r", exc)

    async def send(
        self, token: str, *, title: str, body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        if not self._available or not self._initialized:
            return False
        try:
            from firebase_admin import messaging  # type: ignore[import]
            msg = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
            )
            # 한글 주석 — messaging.send = 동기 호출 (firebase-admin SDK)
            import asyncio
            loop = asyncio.get_event_loop()
            msg_id = await loop.run_in_executor(None, messaging.send, msg)
            log.info("[fcm.send] PASS token=%s... msg_id=%s", token[:16], msg_id)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("[fcm.send] 실패 token=%s... — %r", token[:16], exc)
            return False


_notifier_singleton: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """notifier singleton — service account 활성 시점 FCMNotifier, 부재 시점 StubNotifier."""
    global _notifier_singleton
    if _notifier_singleton is not None:
        return _notifier_singleton
    if _SERVICE_ACCOUNT_PATH and os.path.isfile(_SERVICE_ACCOUNT_PATH):
        _notifier_singleton = FCMNotifier(_SERVICE_ACCOUNT_PATH)
        log.info("[fcm] FCMNotifier 활성 — sa=%s", _SERVICE_ACCOUNT_PATH)
    else:
        _notifier_singleton = StubNotifier()
        log.info("[fcm] StubNotifier 활성 — FIREBASE_SERVICE_ACCOUNT env 부재")
    return _notifier_singleton


async def send_to_user(
    pool: Any, *, user_id: int, title: str, body: str,
    data: Optional[Dict[str, str]] = None,
) -> int:
    """사용자 active token 전수 fan-out — push send.

    Returns
    -------
    int
        성공 송신 token 수.
    """
    if pool is None:
        return 0
    from server.db.repositories.device_tokens import (
        list_active_tokens, touch_last_used, deactivate_token,
    )
    notifier = get_notifier()
    tokens = await list_active_tokens(pool, user_id=user_id)
    sent = 0
    for t in tokens:
        try:
            ok = await notifier.send(t.fcm_token, title=title, body=body, data=data)
            if ok:
                sent += 1
                await touch_last_used(pool, token_id=t.id)
        except Exception as exc:  # noqa: BLE001
            log.warning("[fcm.send_to_user] token=%d 실패 — %r", t.id, exc)
    return sent
