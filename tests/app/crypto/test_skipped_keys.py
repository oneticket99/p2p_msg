# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.skipped_keys`` 단위 테스트 — out-of-order delivery LRU + TTL."""

from __future__ import annotations

import time

import pytest

from app.crypto.skipped_keys import SkippedKeyStore


_PK = b"\x01" * 32
_MK = b"\x02" * 32
_PK2 = b"\x03" * 32


class TestValidation:
    def test_invalid_max_skip(self) -> None:
        with pytest.raises(ValueError, match="max_skip"):
            SkippedKeyStore(max_skip=0)

    def test_invalid_ttl(self) -> None:
        with pytest.raises(ValueError, match="ttl_seconds"):
            SkippedKeyStore(ttl_seconds=0)

    def test_put_invalid_dh_pub(self) -> None:
        s = SkippedKeyStore()
        with pytest.raises(ValueError, match="dh_public_raw"):
            s.put(b"\x01" * 31, 0, _MK)

    def test_put_invalid_key(self) -> None:
        s = SkippedKeyStore()
        with pytest.raises(ValueError, match="message_key"):
            s.put(_PK, 0, b"\x02" * 31)

    def test_put_negative_counter(self) -> None:
        s = SkippedKeyStore()
        with pytest.raises(ValueError, match="counter"):
            s.put(_PK, -1, _MK)


class TestPutGet:
    def test_round_trip(self) -> None:
        s = SkippedKeyStore()
        s.put(_PK, 5, _MK)
        assert len(s) == 1
        assert s.get(_PK, 5) == _MK
        # one-shot — 사용 후 자동 폐기
        assert len(s) == 0
        assert s.get(_PK, 5) is None

    def test_get_missing(self) -> None:
        s = SkippedKeyStore()
        assert s.get(_PK, 0) is None

    def test_different_pk_isolated(self) -> None:
        s = SkippedKeyStore()
        s.put(_PK, 0, b"\xaa" * 32)
        s.put(_PK2, 0, b"\xbb" * 32)
        assert s.get(_PK, 0) == b"\xaa" * 32
        assert s.get(_PK2, 0) == b"\xbb" * 32

    def test_different_counter_isolated(self) -> None:
        s = SkippedKeyStore()
        s.put(_PK, 0, b"\xaa" * 32)
        s.put(_PK, 1, b"\xbb" * 32)
        assert s.get(_PK, 0) == b"\xaa" * 32
        assert s.get(_PK, 1) == b"\xbb" * 32


class TestLRUEvict:
    def test_max_skip_eviction(self) -> None:
        s = SkippedKeyStore(max_skip=3)
        for i in range(5):
            s.put(_PK, i, bytes([i + 1]) * 32)
        # max 3 보관 — oldest 2건 evict
        assert len(s) == 3
        # counter 0, 1 evicted
        assert s.get(_PK, 0) is None
        assert s.get(_PK, 1) is None
        # counter 2, 3, 4 잔존
        assert s.get(_PK, 2) == b"\x03" * 32

    def test_put_same_key_updates_lru(self) -> None:
        # 동일 key 재저장 = LRU 갱신 (oldest 의 위치 → newest)
        s = SkippedKeyStore(max_skip=3)
        s.put(_PK, 0, b"\xaa" * 32)
        s.put(_PK, 1, b"\xbb" * 32)
        s.put(_PK, 2, b"\xcc" * 32)
        # counter 0 재저장 → LRU 갱신
        s.put(_PK, 0, b"\xdd" * 32)
        # counter 3 추가 → counter 1 evict (counter 0 = newest)
        s.put(_PK, 3, b"\xee" * 32)
        assert s.get(_PK, 1) is None
        assert s.get(_PK, 0) == b"\xdd" * 32


class TestExpire:
    def test_ttl_expire(self) -> None:
        s = SkippedKeyStore(ttl_seconds=0.05)
        s.put(_PK, 0, _MK)
        time.sleep(0.1)
        # TTL 만료 후 get = None
        assert s.get(_PK, 0) is None

    def test_expire_batch(self) -> None:
        s = SkippedKeyStore(ttl_seconds=0.05)
        for i in range(5):
            s.put(_PK, i, bytes([i + 1]) * 32)
        time.sleep(0.1)
        evicted = s.expire()
        assert evicted == 5
        assert len(s) == 0

    def test_expire_partial(self) -> None:
        s = SkippedKeyStore(ttl_seconds=1.0)
        s.put(_PK, 0, _MK)
        # 직전 entry 는 1초 유효 — 즉시 expire 시 0건
        assert s.expire() == 0
        assert len(s) == 1
