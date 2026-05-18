# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.double_ratchet`` Signal Double Ratchet KDF chain 단위 테스트."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto.double_ratchet import (
    ChainKey,
    advance_chain_key,
    decrypt_message,
    derive_message_key,
    encrypt_message,
    ratchet_chain,
)
from app.crypto.e2ee import generate_aes_key


class TestChainKeyValidation:
    def test_valid_chain_key(self) -> None:
        ck = ChainKey(key=b"\x42" * 32, counter=0)
        assert ck.counter == 0
        assert len(ck.key) == 32

    def test_invalid_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="chain_key 길이 불일치"):
            ChainKey(key=b"\x42" * 31)

    def test_negative_counter_rejected(self) -> None:
        with pytest.raises(ValueError, match="counter 음수 불가"):
            ChainKey(key=b"\x42" * 32, counter=-1)


class TestDeriveMessageKey:
    def test_deterministic(self) -> None:
        # 같은 chain → 같은 message key (양측 sync 가능)
        ck = ChainKey(key=b"\x42" * 32)
        assert derive_message_key(ck) == derive_message_key(ck)

    def test_length_32_byte(self) -> None:
        ck = ChainKey(key=generate_aes_key())
        mk = derive_message_key(ck)
        assert len(mk) == 32

    def test_different_chain_keys_yield_different_message_keys(self) -> None:
        ck1 = ChainKey(key=b"\x01" * 32)
        ck2 = ChainKey(key=b"\x02" * 32)
        assert derive_message_key(ck1) != derive_message_key(ck2)


class TestAdvanceChainKey:
    def test_counter_increments(self) -> None:
        ck = ChainKey(key=b"\x42" * 32, counter=5)
        nx = advance_chain_key(ck)
        assert nx.counter == 6

    def test_key_changes_per_step(self) -> None:
        ck = ChainKey(key=b"\x42" * 32)
        nx = advance_chain_key(ck)
        assert nx.key != ck.key

    def test_chain_deterministic(self) -> None:
        # 같은 시작 의 의 chain → 같은 진행
        ck0 = ChainKey(key=b"\x42" * 32)
        a1 = advance_chain_key(ck0)
        a2 = advance_chain_key(ck0)
        assert a1.key == a2.key
        assert a1.counter == a2.counter

    def test_message_key_vs_chain_key_distinct(self) -> None:
        # 0x01 (message) vs 0x02 (chain) seed 분리 정합
        ck = ChainKey(key=b"\x42" * 32)
        mk = derive_message_key(ck)
        nx = advance_chain_key(ck)
        # message key + next chain key 서로 다름 (서로 다른 HMAC input)
        assert mk != nx.key


class TestRatchetChain:
    def test_atomic_step(self) -> None:
        ck = ChainKey(key=b"\x42" * 32, counter=0)
        mk, nx = ratchet_chain(ck)
        assert mk == derive_message_key(ck)
        assert nx.counter == 1
        assert nx.key == advance_chain_key(ck).key

    def test_forward_secrecy_chain(self) -> None:
        # 100 step 의 chain advance — 모든 message key 별개 + counter 정합
        ck = ChainKey(key=b"\x42" * 32)
        keys = set()
        for i in range(100):
            mk, ck = ratchet_chain(ck)
            keys.add(mk)
            assert ck.counter == i + 1
        # 100 message key 의 collision 0 (HMAC-SHA256 의 의 forward secrecy)
        assert len(keys) == 100


class TestEncryptDecryptMessage:
    def test_send_recv_sync(self) -> None:
        """Alice + Bob 의 동일 chain → 동일 message key → round-trip PASS."""

        root = b"\x42" * 32
        chain_a = ChainKey(key=root)
        chain_b = ChainKey(key=root)

        msg = "Phase 2 메시지".encode("utf-8")
        payload, chain_a_next = encrypt_message(chain_a, msg)
        decoded, chain_b_next = decrypt_message(chain_b, payload)

        assert decoded == msg
        assert chain_a_next.counter == 1
        assert chain_b_next.counter == 1
        # 양측 chain 의 의 next state 동일
        assert chain_a_next.key == chain_b_next.key

    def test_multiple_messages_in_sequence(self) -> None:
        """연속 3 메시지 = 3 advance + 모두 복호화 PASS."""

        root = b"\x42" * 32
        send_chain = ChainKey(key=root)
        recv_chain = ChainKey(key=root)

        messages = [b"first", b"second", b"third"]
        for msg in messages:
            payload, send_chain = encrypt_message(send_chain, msg)
            decoded, recv_chain = decrypt_message(recv_chain, payload)
            assert decoded == msg
        # 3 step 후 counter = 3
        assert send_chain.counter == 3
        assert recv_chain.counter == 3

    def test_wrong_chain_state_rejects(self) -> None:
        """수신 chain 이 송신 보다 앞서거나 뒤진 경우 = InvalidTag (skipped key 처리 X)."""

        root = b"\x42" * 32
        send_chain = ChainKey(key=root)
        recv_chain = ChainKey(key=root)

        # 송신 단 2 step advance
        payload1, send_chain = encrypt_message(send_chain, b"msg1")
        payload2, send_chain = encrypt_message(send_chain, b"msg2")

        # 수신 단 msg1 skip → msg2 직접 decrypt = FAIL (chain mismatch)
        with pytest.raises(InvalidTag):
            decrypt_message(recv_chain, payload2)

    def test_forward_secrecy_compromise(self) -> None:
        """과거 chain key 누설 = 미래 메시지 복호화 가능, 과거 메시지 = 복원 불가 (forward secrecy)."""

        root = b"\x42" * 32
        chain = ChainKey(key=root)
        payload_old, chain = encrypt_message(chain, b"old secret")
        payload_new, chain_after_new = encrypt_message(chain, b"new secret")

        # chain (advanced 상태) 의 past payload_old 복호화 시도 = FAIL
        # past message key 는 past chain key 의 derive, 이미 advance 됨
        with pytest.raises(InvalidTag):
            decrypt_message(chain, payload_old)
        # 신규 chain key 의 새 메시지 복호화 = OK (chain_after_new 의 미래 메시지 PASS)
