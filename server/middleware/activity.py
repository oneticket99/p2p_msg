# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 111 — 사용자 활동 추적 middleware.

DB audit migration 0003 의 actual code wiring. 매 인증된 request 직후
`users.last_active_at` + `user_sessions.last_active_at` 갱신. 1분 throttle 의
write storm 회피 + 90일 IP retention 정합 ([[feedback-db-audit-timestamp-ip-activity]]).

설계 결정
---------
- ActivityTracker dataclass — in-memory `Dict[user_id, last_seen_seconds]` +
  `throttle_seconds=60` (default). throttle 안 의 중복 update skip.
- middleware = auth_middleware 직후 chain. request["user_id"] 의무 (auth
  middleware 가 주입). request_ip = `X-Forwarded-For` 의 첫 토큰 (nginx 정합).
- DB write = `request.app["db_pool"]` 의 가용 여부 분기 — None 시 graceful
  skip (개발 환경 + DB_ENABLED=0 정합). pool 가용 시 mariadb UPDATE 호출
  (별개 cycle 의 actual SQL 의 wiring — 본 cycle = throttle + hook 의 base).
- 동기 throttle dict — 단일 worker process 가정 (multi-worker 의 distributed
  throttle = 별개 cycle 의 Redis 또는 DB token bucket).

본 module 범위 외
----------------
- 실 DB UPDATE 의 SQL 호출 (UPDATE users SET last_active_at + INSERT INTO
  user_activity_log) — 별개 cycle 의 repositories 의 wiring.
- multi-worker safety — 별개 cycle 의 Redis 의무.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from aiohttp import web

log = logging.getLogger(__name__)


_DEFAULT_THROTTLE_SECONDS = 60
_HEADER_XFF = "X-Forwarded-For"


@dataclass
class ActivityTracker:
    """In-memory user 활동 throttle.

    매 인증 request 의 ``user_id`` 의 `last_seen_seconds` 갱신. 동일 사용자
    의 throttle 안 의 중복 갱신 skip → DB write storm 차단.

    Parameters
    ----------
    throttle_seconds : int
        동일 user_id 의 갱신 사이 의 최소 간격 (default 60초).
    """

    throttle_seconds: int = _DEFAULT_THROTTLE_SECONDS
    _last_seen: Dict[int, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.throttle_seconds <= 0:
            raise ValueError(
                f"throttle_seconds 양수 의무 — {self.throttle_seconds}"
            )

    def should_update(self, user_id: int, now_seconds: Optional[float] = None) -> bool:
        """user_id 의 갱신 의무 여부 — throttle 안 = False / 외 = True.

        본 호출 자체가 throttle 갱신 — True 반환 시 next throttle window 시작.
        """

        if user_id <= 0:
            return False
        now = now_seconds if now_seconds is not None else time.time()
        last = self._last_seen.get(user_id)
        if last is None or (now - last) >= self.throttle_seconds:
            self._last_seen[user_id] = now
            return True
        return False

    def size(self) -> int:
        return len(self._last_seen)

    def prune_stale(self, cutoff_seconds: float) -> int:
        """cutoff 이전 entry 의 evict — 메모리 누수 회피 (1분 throttle 의 inactive user)."""

        removed = [uid for uid, t in self._last_seen.items() if t < cutoff_seconds]
        for uid in removed:
            del self._last_seen[uid]
        return len(removed)


def extract_client_ip(request: web.Request) -> str:
    """`X-Forwarded-For` header parse — nginx reverse proxy 정합.

    `X-Forwarded-For: client, proxy1, proxy2` 의 첫 토큰 (client IP).
    부재 시 ``request.remote`` fallback. 빈 string 시 ``""`` 반환.
    """

    xff = request.headers.get(_HEADER_XFF, "").strip()
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return (request.remote or "").strip()


APP_KEY_ACTIVITY = web.AppKey("activity_tracker", ActivityTracker)


@web.middleware
async def activity_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Any],
) -> web.StreamResponse:
    """auth_middleware 직후 chain. user_id + IP 의 활동 갱신 trigger.

    request["user_id"] 의 auth_middleware 주입 의무. 부재 시 갱신 skip
    (public endpoint 정합).
    """

    response = await handler(request)
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return response

    tracker = request.app.get(APP_KEY_ACTIVITY)
    if tracker is None:
        return response

    if tracker.should_update(user_id):
        client_ip = extract_client_ip(request)
        log.info(
            "activity update user_id=%d ip=%s ua=%r path=%s",
            user_id,
            client_ip,
            request.headers.get("User-Agent", ""),
            request.path,
        )
        # cycle 120 — actual DB UPDATE wiring. pool 부재 graceful skip + 예외 swallow.
        token = request.get("session_token") if hasattr(request, "get") else None
        pool = request.app.get("db_pool") if hasattr(request.app, "get") else None
        if pool is not None and isinstance(token, str) and token:
            try:
                import hashlib

                from server.db.repositories.user_activity import (
                    update_session_last_active,
                )

                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                await update_session_last_active(
                    pool, session_token_hash=token_hash
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "user_sessions.last_active_at 갱신 실패 (user_id=%d): %s",
                    user_id,
                    exc,
                )
    return response
