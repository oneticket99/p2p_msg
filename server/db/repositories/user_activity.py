# SPDX-License-Identifier: GPL-3.0-or-later
"""user_activity_log + user_sessions repository — Phase 4 cycle 115.

DDL 정합: ``server/db/migrations/0003_user_activity.sql``.
모든 함수 = pool dependency injection 패턴 + asyncmy execute.

설계 결정
---------
- 22 action ENUM 의 type-safe ActivityAction 상수 — caller 의 string typo 차단.
- log_activity = INSERT user_activity_log + 부수 update users.last_activity_at
  + user_sessions.last_active_at (활성 세션 가용 시 단일 query).
- create_session = INSERT user_sessions (login 직후) + users.last_login_ip +
  last_login_at 갱신.
- close_session = UPDATE disconnected_at + duration_seconds + end_reason.
- 모든 SQL = parameterized (SQL injection 차단).

본 module 범위 외
----------------
- aiohttp middleware 의 actual call site wiring — 별개 cycle 의무 (auth_handlers
  + bot_handlers 등 caller 영역 hook).
- batch INSERT 또는 활동 log buffering — Phase 5+ 의 성능 최적화.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ActivityAction(str, Enum):
    """user_activity_log.action ENUM 의 22종 정합."""

    SIGNUP = "signup"
    SIGNUP_OTP_VERIFY = "signup_otp_verify"
    RECLAIM_UNVERIFIED = "reclaim_unverified"  # reviewer cycle 169.42 M-3 회수
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    ROOM_CREATE = "room_create"
    ROOM_JOIN = "room_join"
    ROOM_LEAVE = "room_leave"
    ROOM_CLOSE = "room_close"
    MESSAGE_SEND = "message_send"
    FILE_SEND = "file_send"
    FILE_RECEIVE = "file_receive"
    DEVICE_REGISTER = "device_register"
    DEVICE_REVOKE = "device_revoke"
    BOT_CHAT = "bot_chat"
    BOT_ESCALATE = "bot_escalate"
    REMOTE_REQUEST = "remote_request"
    REMOTE_GRANT = "remote_grant"
    REMOTE_REVOKE = "remote_revoke"
    PROFILE_UPDATE = "profile_update"
    EMAIL_CHANGE = "email_change"
    ACCOUNT_DELETE = "account_delete"
    # 한글 주석: cycle 144 친구 관리 chain — DDL 0007 의 ENUM 확장 정합.
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPT = "friend_accept"
    FRIEND_REJECT = "friend_reject"
    FRIEND_BLOCK = "friend_block"
    FRIEND_REMOVE = "friend_remove"


class SessionEndReason(str, Enum):
    """user_sessions.end_reason ENUM 의 5종."""

    LOGOUT = "logout"
    IDLE_TIMEOUT = "idle_timeout"
    TOKEN_REVOKE = "token_revoke"
    FORCE_DISCONNECT = "force_disconnect"
    SERVER_RESTART = "server_restart"


@dataclass(frozen=True, slots=True)
class ActivityLogRow:
    """user_activity_log row 도메인 객체."""

    id: int
    user_id: int
    action: ActivityAction
    target_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[dict]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SessionRow:
    """user_sessions row 도메인 객체."""

    id: int
    user_id: int
    session_token_hash: str
    ip_address: str
    user_agent: Optional[str]
    connected_at: datetime
    last_active_at: datetime
    disconnected_at: Optional[datetime]
    duration_seconds: Optional[int]
    end_reason: Optional[SessionEndReason]


# ─── INSERT 의 SQL ──────────────────────────────────────────────────────────

_INSERT_ACTIVITY = """
INSERT INTO user_activity_log
    (user_id, action, target_id, ip_address, user_agent, metadata, created_at)
VALUES
    (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
"""

_INSERT_SESSION = """
INSERT INTO user_sessions
    (user_id, session_token_hash, ip_address, user_agent,
     connected_at, last_active_at)
VALUES
    (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

# ─── UPDATE 의 SQL ──────────────────────────────────────────────────────────

_UPDATE_USERS_LAST_ACTIVITY = """
UPDATE users SET last_activity_at = CURRENT_TIMESTAMP WHERE id = %s
"""

_UPDATE_USERS_LAST_LOGIN = """
UPDATE users
    SET last_login_at = CURRENT_TIMESTAMP, last_login_ip = %s
    WHERE id = %s
"""

_UPDATE_SESSION_LAST_ACTIVE = """
UPDATE user_sessions SET last_active_at = CURRENT_TIMESTAMP
    WHERE session_token_hash = %s AND disconnected_at IS NULL
"""

_CLOSE_SESSION = """
UPDATE user_sessions
    SET disconnected_at = CURRENT_TIMESTAMP,
        duration_seconds = TIMESTAMPDIFF(SECOND, connected_at, CURRENT_TIMESTAMP),
        end_reason = %s
    WHERE session_token_hash = %s AND disconnected_at IS NULL
"""


# ─── repository 함수 ────────────────────────────────────────────────────────

async def log_activity(
    pool: Any,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """user_activity_log INSERT — 22 action 중 1건 의 audit row 신규 생성.

    Parameters
    ----------
    pool : asyncmy.Pool
        DB pool. None 시 ValueError.
    user_id : int
        활동 사용자 PK. 양수 의무.
    action : ActivityAction
        22 ENUM 중 1.
    target_id : Optional[int]
        action 별 대상 ID (room_id / target_user_id / device_id 등).
    ip_address : Optional[str]
        활동 발생 IP (X-Forwarded-For parse 결과).
    user_agent : Optional[str]
        User-Agent header.
    metadata : Optional[dict]
        action 부가 정보 JSON. PII (이메일/비번/토큰 평문) 절대 금지.

    Returns
    -------
    int
        신규 row 의 AUTO_INCREMENT id.

    Raises
    ------
    ValueError
        user_id <= 0 또는 pool 부재.
    """

    if pool is None:
        raise ValueError("pool 의무 — DB_ENABLED=1 graceful skip 은 caller 영역")
    if user_id <= 0:
        raise ValueError(f"user_id 양수 의무 — {user_id}")

    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_ACTIVITY,
                (
                    user_id,
                    action.value,
                    target_id,
                    ip_address,
                    user_agent,
                    metadata_json,
                ),
            )
            new_id = cur.lastrowid
            await cur.execute(_UPDATE_USERS_LAST_ACTIVITY, (user_id,))
            await conn.commit()
            return int(new_id)


async def create_session(
    pool: Any,
    *,
    user_id: int,
    session_token_hash: str,
    ip_address: str,
    user_agent: Optional[str] = None,
) -> int:
    """user_sessions INSERT — login 직후 신규 세션 row.

    부수 — users.last_login_at + last_login_ip 갱신.
    """

    if pool is None:
        raise ValueError("pool 의무")
    if user_id <= 0:
        raise ValueError(f"user_id 양수 의무 — {user_id}")
    if not session_token_hash or len(session_token_hash) != 64:
        raise ValueError("session_token_hash 64자 SHA-256 hex 의무")
    if not ip_address:
        raise ValueError("ip_address 의무")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_SESSION,
                (user_id, session_token_hash, ip_address, user_agent),
            )
            new_id = cur.lastrowid
            await cur.execute(_UPDATE_USERS_LAST_LOGIN, (ip_address, user_id))
            await conn.commit()
            return int(new_id)


async def update_session_last_active(
    pool: Any,
    *,
    session_token_hash: str,
) -> int:
    """user_sessions.last_active_at 갱신 — 활성 세션 만 (disconnected_at IS NULL).

    Returns
    -------
    int
        갱신된 row 수 (0 = 활성 세션 부재 / 1 = 갱신).
    """

    if pool is None:
        raise ValueError("pool 의무")
    if not session_token_hash:
        raise ValueError("session_token_hash 의무")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_UPDATE_SESSION_LAST_ACTIVE, (session_token_hash,))
            await conn.commit()
            return int(cur.rowcount or 0)


async def close_session(
    pool: Any,
    *,
    session_token_hash: str,
    end_reason: SessionEndReason,
) -> int:
    """user_sessions disconnected_at + duration_seconds + end_reason 갱신.

    duration_seconds = TIMESTAMPDIFF(SECOND, connected_at, NOW()) — MariaDB 영역 계산.
    """

    if pool is None:
        raise ValueError("pool 의무")
    if not session_token_hash:
        raise ValueError("session_token_hash 의무")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _CLOSE_SESSION, (end_reason.value, session_token_hash)
            )
            await conn.commit()
            return int(cur.rowcount or 0)
