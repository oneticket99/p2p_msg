# SPDX-License-Identifier: GPL-3.0-or-later
"""FCM (Firebase Cloud Messaging) push notification helper (cycle 169.446 신설).

사용자 directive 메신저 기본 — 신규 메시지 도착 시점 push notification 의무.

본 module 범위 (cycle 169.446 skeleton):
- ``Notifier`` interface — send(token, title, body, data) 단일 method
- ``StubNotifier`` — Firebase service account 부재 시점 graceful noop + log
- ``FCMNotifier`` — firebase-admin SDK actual binding (별 cycle 의무 — service account JSON load + initialize_app + messaging.send)
- ``send_to_user(pool, user_id, title, body)`` — fan-out helper (사용자 active token 전수)

본 cycle 의 범위 외 (별 cycle):
- firebase-admin SDK 의 actual import + initialize chain
- FCM_INVALID_REGISTRATION 응답 시점 deactivate_token chain
- APNs (iOS) 별 payload + WNS (Windows) bridge
- retry + exponential backoff + circuit breaker
"""

from .notifier import (
    Notifier, StubNotifier, FCMNotifier, get_notifier, send_to_user,
)

__all__ = ["Notifier", "StubNotifier", "FCMNotifier", "get_notifier", "send_to_user"]
