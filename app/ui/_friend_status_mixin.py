# SPDX-License-Identifier: GPL-3.0-or-later
"""FriendStatusMixin — friend last_seen REST fetch (cycle 169.529 신설).

codex 2.5 14차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 169.221 origin):
- `_fetch_user_status(user_id)` — GET /api/auth/users/{user_id}/status →
  active chat 시점 chat_header 갱신 (online/last_active)

본 mixin 안 의존:
- `self._config.api_base`, `self._session_token`
- `self._active_chat_kind`, `self._active_chat_target_id`, `self._chat_header`
- `self._lookup_friend_name()` (FriendProfileMixin)
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class FriendStatusMixin:
    """friend last_seen REST fetch + chat_header status 갱신 mixin (cycle 169.529)."""

    async def _fetch_user_status(self, user_id: int) -> None:
        """cycle 169.221 — friend last_seen REST fetch (cycle 169.216 endpoint).

        GET /api/auth/users/{user_id}/status → chat_header status 갱신.
        graceful exception (server 부재 시 기존 fallback retain).
        """
        import aiohttp
        try:
            api_base = getattr(self._config, "api_base", None) or "http://114.207.112.73:8765"
            token = getattr(self, "_session_token", None) or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    f"{api_base}/api/auth/users/{user_id}/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()
                    online = data.get("online", False)
                    last_active = data.get("last_active_at")
            # active chat 의 의 retain 시점만 갱신
            if self._active_chat_kind == "friend" and self._active_chat_target_id == user_id:
                if online:
                    status = "온라인"
                elif last_active:
                    status = f"마지막 접속: {last_active[:16]}"
                else:
                    status = "최근에 접속함"
                name = self._lookup_friend_name(user_id)
                self._chat_header.set_chat(name, status=status)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("[user_status] fetch 실패 — %r", exc)
