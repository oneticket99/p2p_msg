# SPDX-License-Identifier: GPL-3.0-or-later
"""client push token register chain (cycle 169.448 신설).

사용자 directive — FCM 실시간 push 의무. client startup 시점 device token register.

본 module 범위:
- ``register_device_token(base_url, auth_token, fcm_token, platform, label)`` — POST /api/push/register
- ``unregister_device_token(base_url, auth_token, token_id)`` — DELETE /api/push/tokens/{token_id}

본 cycle 의 범위 외 (별 cycle):
- FCM token 실 발급 chain — firebase-messaging Python client 부재. macOS APNs / Windows WNS native bridge 의무
- 본 cycle = 사용자 manual paste 또는 placeholder token 의 의 register chain only
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)


def register_device_token(
    base_url: str,
    auth_token: str,
    fcm_token: str,
    platform: str = "macos",
    device_label: Optional[str] = None,
) -> Optional[int]:
    """POST /api/push/register — 디바이스 token 등록.

    Returns
    -------
    int | None
        token_id (성공) 또는 None (실패).
    """
    if not base_url or not auth_token or not fcm_token:
        return None
    url = f"{base_url.rstrip('/')}/api/push/register"
    payload = json.dumps({
        "fcm_token": fcm_token,
        "platform": platform,
        "device_label": device_label,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
        method="POST",
    )
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            raw = resp.read()
            data = json.loads(raw) if raw else {}
            token_id = data.get("token_id")
            log.info("[push.register] PASS token_id=%s", token_id)
            return int(token_id) if isinstance(token_id, int) else None
    except urllib.error.HTTPError as exc:
        log.warning("[push.register] HTTP %d — %s", exc.code, exc.reason)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("[push.register] 실패 — %r", exc)
        return None


def unregister_device_token(
    base_url: str,
    auth_token: str,
    token_id: int,
) -> bool:
    """DELETE /api/push/tokens/{token_id} — 디바이스 token 비활성."""
    if not base_url or not auth_token or token_id <= 0:
        return False
    url = f"{base_url.rstrip('/')}/api/push/tokens/{token_id}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {auth_token}"},
        method="DELETE",
    )
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            log.info("[push.unregister] HTTP %d", resp.status)
            return resp.status in (200, 204)
    except Exception as exc:  # noqa: BLE001
        log.warning("[push.unregister] 실패 — %r", exc)
        return False
