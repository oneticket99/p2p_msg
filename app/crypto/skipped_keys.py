# SPDX-License-Identifier: GPL-3.0-or-later
"""Signal Protocol skipped message keys 저장소 — out-of-order delivery 처리.

본 module = Double Ratchet 수신 측 의 message reordering 대응:
- counter 5 수신 직후 counter 3 도착 시 = chain advance 시 skip 된 key 보관 → 차후 사용
- LRU expire (MAX_SKIP=1000) — 메모리 폭주 차단 (productization §8.1 보안 해결책 정합)
- TTL = 1시간 (chain key 의 forward secrecy 균형)

API:
- `SkippedKeyStore` dataclass — (DH_public, counter) → message_key
- `put(dh_pub, counter, key)` — 신규 skipped key 저장
- `get(dh_pub, counter)` — 보관된 key 조회 + 자동 폐기 (one-shot)
- `expire()` — TTL + LRU 정리
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Final, Optional, Tuple

# Signal Protocol 권장 — out-of-order skip 한계 (productization §8.1 보안 정합)
_MAX_SKIP: Final[int] = 1000
# TTL 1시간 — 너무 짧으면 정상 reorder 차단, 너무 길면 forward secrecy 손상
_DEFAULT_TTL_SECONDS: Final[float] = 3600.0


@dataclass(slots=True)
class SkippedKeyStore:
    """LRU + TTL 기반 skipped message key 저장소.

    Attributes
    ----------
    max_skip : int
        최대 보관 entry 수. 초과 시 LRU evict.
    ttl_seconds : float
        entry 의 expire 시각 (저장 시점 + ttl).
    _entries : OrderedDict[(bytes, int), tuple[bytes, float]]
        (dh_public_raw, counter) → (message_key, deadline_unix).
        OrderedDict = LRU 의 의 access order 유지.
    """

    max_skip: int = _MAX_SKIP
    ttl_seconds: float = _DEFAULT_TTL_SECONDS
    _entries: "OrderedDict[Tuple[bytes, int], Tuple[bytes, float]]" = field(
        default_factory=OrderedDict
    )

    def __post_init__(self) -> None:
        if self.max_skip < 1:
            raise ValueError(f"max_skip 최소 1 — got {self.max_skip}")
        if self.ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds 양수 의무 — got {self.ttl_seconds}")

    def put(self, dh_public_raw: bytes, counter: int, message_key: bytes) -> None:
        """skipped message key 저장 + LRU 정리.

        Parameters
        ----------
        dh_public_raw : bytes
            peer X25519 public key (32 byte) — chain 식별자.
        counter : int
            chain key counter (0~).
        message_key : bytes
            32 byte AES-256 message key.

        Raises
        ------
        ValueError
            dh_public_raw 길이 32 byte 아님 또는 message_key 길이 32 byte 아님.
        """

        if len(dh_public_raw) != 32:
            raise ValueError(f"dh_public_raw 32 byte 의무 — got {len(dh_public_raw)}")
        if len(message_key) != 32:
            raise ValueError(f"message_key 32 byte 의무 — got {len(message_key)}")
        if counter < 0:
            raise ValueError(f"counter 음수 불가 — {counter}")

        key = (dh_public_raw, counter)
        deadline = time.monotonic() + self.ttl_seconds
        # 동일 key 재저장 = LRU 갱신 (move_to_end)
        self._entries[key] = (message_key, deadline)
        self._entries.move_to_end(key)
        # LRU evict — max_skip 초과 시 oldest 폐기
        while len(self._entries) > self.max_skip:
            self._entries.popitem(last=False)

    def get(self, dh_public_raw: bytes, counter: int) -> Optional[bytes]:
        """보관된 key 조회 + 자동 폐기 (one-shot, replay 차단).

        Returns
        -------
        bytes | None
            message_key (32 byte) — 부재 시 None.
        """

        key = (dh_public_raw, counter)
        entry = self._entries.get(key)
        if entry is None:
            return None
        message_key, deadline = entry
        # TTL 만료 check
        if time.monotonic() > deadline:
            del self._entries[key]
            return None
        # one-shot — 사용 후 즉시 삭제 (forward secrecy + replay 차단)
        del self._entries[key]
        return message_key

    def expire(self) -> int:
        """만료된 entry 일괄 정리 — cron 호출.

        Returns
        -------
        int
            삭제된 entry 수.
        """

        now = time.monotonic()
        expired = [k for k, (_, deadline) in self._entries.items() if now > deadline]
        for k in expired:
            del self._entries[k]
        return len(expired)

    def __len__(self) -> int:
        return len(self._entries)
