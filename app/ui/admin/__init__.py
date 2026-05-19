# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 admin UI 패키지 — owner role 만 access 의 management dialog 모음.

cycle 144 신설 — emoji moderation admin dialog 의 entry. cycle 148 의
``open_emoji_moderation`` helper 추가 (main_window 진입점 의 standard chain).
추후 cycle 의 user management / DMCA queue / bot framework admin 등 추가 예정.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

log = logging.getLogger(__name__)


def open_emoji_moderation(
    *,
    parent: Any = None,
    base_url: str,
    admin_token: str,
    pending_items: Optional[List[Any]] = None,
) -> Optional[Any]:
    """EmojiModerationDialog 의 standard instantiation helper (cycle 148 신설).

    Parameters
    ----------
    parent : QWidget | None
        Qt parent widget (보통 MainWindow). None = top level.
    base_url : str
        signaling server base URL (예: "https://demo.example.com").
    admin_token : str
        EMOJI_MODERATION_ADMIN_TOKEN — caller 의 env / KeyChain 주입 의무.
    pending_items : List[PendingPackItem] | None
        초기 pending queue snapshot. None = 빈 list (caller 가 추후 repopulate).

    Returns
    -------
    EmojiModerationDialog | None
        instantiation 결과. PyQt6 부재 / RuntimeError 시 None graceful.

    Notes
    -----
    - 본 helper = main_window 등 의 caller 의 단일 진입점 — 직접 dialog 생성 회피.
    - admin_token 의 검증 = caller 의무 (빈 차단 / env 폴백 / KeyChain refresh).
    - actual REST chain (fetch_pending_queue + post_decision) = caller 의 책임.
    """

    # 한글 주석: lazy import — PyQt6 / httpx 부재 환경 graceful
    try:
        from app.ui.admin.emoji_moderation_dialog import EmojiModerationDialog
    except Exception as exc:  # noqa: BLE001
        log.warning("[admin] EmojiModerationDialog import 실패 — %r", exc)
        return None

    # 한글 주석: 초기 빈 list — fetch_pending_queue 의 repopulate chain 의무
    initial = list(pending_items) if pending_items else []

    try:
        dialog = EmojiModerationDialog(
            pending_items=initial,
            parent=parent,
            base_url=base_url,
            admin_token=admin_token,
        )
        log.info(
            "[admin] open_emoji_moderation instantiation PASS base_url=%s initial=%d",
            base_url,
            len(initial),
        )
        return dialog
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[admin] open_emoji_moderation instantiation 실패 — graceful (%r)", exc
        )
        return None


__all__ = ["open_emoji_moderation"]
