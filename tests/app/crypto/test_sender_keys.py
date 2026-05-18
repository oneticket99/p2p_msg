# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.sender_keys`` 단위 테스트.

Signal Protocol Sender Keys 검증 — 그룹 N×M cipher 폭증 의 N+M reduction.
sender 의 chain ratchet + recipient 단 distribution 적용 round-trip + counter
advance + forward secrecy (sender 의 advanced chain 의 직전 message key 의
recover 차단).
"""

from __future__ import annotations

import secrets

import pytest

from app.crypto.double_ratchet import ChainKey
from app.crypto.sender_keys import (
    SenderKeyDistribution,
    SenderKeyState,
    apply_distribution,
    build_distribution,
    create_sender_key,
    decrypt_group_message,
    encrypt_group_message,
)


def _random_key(n: int = 32) -> bytes:
    """테스트 용 무작위 32 byte key 산출."""

    return secrets.token_bytes(n)


class TestSenderKeyStateValidation:
    """``SenderKeyState`` dataclass 의 입력 검증."""

    def test_valid_construction(self) -> None:
        chain = ChainKey(key=_random_key(), counter=0)
        state = SenderKeyState(
            sender_id="alice",
            chain=chain,
            signing_public_key=_random_key(),
        )
        assert state.sender_id == "alice"
        assert state.chain.counter == 0

    def test_empty_sender_id_rejected(self) -> None:
        chain = ChainKey(key=_random_key(), counter=0)
        with pytest.raises(ValueError, match="sender_id 빈 문자열 불가"):
            SenderKeyState(
                sender_id="",
                chain=chain,
                signing_public_key=_random_key(),
            )

    def test_signing_public_key_length_mismatch(self) -> None:
        chain = ChainKey(key=_random_key(), counter=0)
        with pytest.raises(ValueError, match="signing_public_key 길이 불일치"):
            SenderKeyState(
                sender_id="alice",
                chain=chain,
                signing_public_key=b"too_short",
            )


class TestSenderKeyDistributionValidation:
    """``SenderKeyDistribution`` wire format 의 입력 검증."""

    def test_valid_construction(self) -> None:
        dist = SenderKeyDistribution(
            sender_id="alice",
            chain_key=_random_key(),
            counter=0,
            signing_public_key=_random_key(),
        )
        assert dist.sender_id == "alice"
        assert dist.counter == 0
        assert len(dist.chain_key) == 32

    def test_empty_sender_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="sender_id 빈 문자열 불가"):
            SenderKeyDistribution(
                sender_id="",
                chain_key=_random_key(),
                counter=0,
                signing_public_key=_random_key(),
            )

    def test_chain_key_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="chain_key 길이 불일치"):
            SenderKeyDistribution(
                sender_id="alice",
                chain_key=b"short",
                counter=0,
                signing_public_key=_random_key(),
            )

    def test_negative_counter_rejected(self) -> None:
        with pytest.raises(ValueError, match="counter 음수 불가"):
            SenderKeyDistribution(
                sender_id="alice",
                chain_key=_random_key(),
                counter=-1,
                signing_public_key=_random_key(),
            )

    def test_signing_public_key_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="signing_public_key 길이 불일치"):
            SenderKeyDistribution(
                sender_id="alice",
                chain_key=_random_key(),
                counter=0,
                signing_public_key=b"short",
            )


class TestCreateSenderKey:
    """``create_sender_key`` 의 초기 상태 생성."""

    def test_default_counter_zero(self) -> None:
        state = create_sender_key(
            sender_id="alice",
            initial_chain_key=_random_key(),
            signing_public_key=_random_key(),
        )
        assert state.chain.counter == 0

    def test_custom_counter(self) -> None:
        state = create_sender_key(
            sender_id="alice",
            initial_chain_key=_random_key(),
            signing_public_key=_random_key(),
            counter=42,
        )
        assert state.chain.counter == 42

    def test_chain_key_preserved(self) -> None:
        key = _random_key()
        state = create_sender_key(
            sender_id="alice",
            initial_chain_key=key,
            signing_public_key=_random_key(),
        )
        assert state.chain.key == key


class TestEncryptDecryptRoundTrip:
    """단일 메시지 의 encrypt → decrypt round-trip 검증."""

    def test_basic_round_trip(self) -> None:
        # Alice sender + Bob recipient 의 동일 초기 chain 의무
        chain_key = _random_key()
        signing_pub = _random_key()
        alice = create_sender_key("alice", chain_key, signing_pub)
        bob = create_sender_key("alice", chain_key, signing_pub)

        plaintext = b"hello group"
        ciphertext, alice_next = encrypt_group_message(alice, plaintext)
        decoded, bob_next = decrypt_group_message(bob, ciphertext)

        assert decoded == plaintext
        # 양측 의 counter 동일 advance — 1
        assert alice_next.chain.counter == 1
        assert bob_next.chain.counter == 1

    def test_aad_binding(self) -> None:
        chain_key = _random_key()
        signing_pub = _random_key()
        alice = create_sender_key("alice", chain_key, signing_pub)
        bob = create_sender_key("alice", chain_key, signing_pub)

        aad = b"group:42"
        ciphertext, _ = encrypt_group_message(alice, b"msg", associated_data=aad)
        plaintext, _ = decrypt_group_message(bob, ciphertext, associated_data=aad)
        assert plaintext == b"msg"

    def test_aad_mismatch_fails_decrypt(self) -> None:
        from cryptography.exceptions import InvalidTag

        chain_key = _random_key()
        signing_pub = _random_key()
        alice = create_sender_key("alice", chain_key, signing_pub)
        bob = create_sender_key("alice", chain_key, signing_pub)

        ciphertext, _ = encrypt_group_message(alice, b"msg", associated_data=b"a")
        with pytest.raises(InvalidTag):
            decrypt_group_message(bob, ciphertext, associated_data=b"b")


class TestSequentialMessages:
    """다수 메시지 순차 encrypt + 동일 순서 decrypt 검증."""

    def test_three_messages_in_order(self) -> None:
        chain_key = _random_key()
        signing_pub = _random_key()
        alice = create_sender_key("alice", chain_key, signing_pub)
        bob = create_sender_key("alice", chain_key, signing_pub)

        messages = [b"first", b"second", b"third"]
        ciphertexts = []
        for msg in messages:
            ct, alice = encrypt_group_message(alice, msg)
            ciphertexts.append(ct)

        for expected, ct in zip(messages, ciphertexts, strict=True):
            decoded, bob = decrypt_group_message(bob, ct)
            assert decoded == expected

        assert alice.chain.counter == 3
        assert bob.chain.counter == 3

    def test_counter_monotonic_after_encrypt(self) -> None:
        state = create_sender_key("alice", _random_key(), _random_key())
        counters = []
        for _ in range(5):
            _, state = encrypt_group_message(state, b"x")
            counters.append(state.chain.counter)
        assert counters == [1, 2, 3, 4, 5]


class TestDistributionWireFormat:
    """``build_distribution`` + ``apply_distribution`` round-trip 검증."""

    def test_round_trip_preserves_state(self) -> None:
        original = create_sender_key("alice", _random_key(), _random_key())
        # 의도적 chain advance 후 distribution → counter 비-0 검증 의무
        _, advanced = encrypt_group_message(original, b"warmup")

        dist = build_distribution(advanced)
        restored = apply_distribution(dist)

        assert restored.sender_id == advanced.sender_id
        assert restored.chain.key == advanced.chain.key
        assert restored.chain.counter == advanced.chain.counter
        assert restored.signing_public_key == advanced.signing_public_key

    def test_distribution_carries_counter(self) -> None:
        chain_key = _random_key()
        signing_pub = _random_key()
        state = create_sender_key("alice", chain_key, signing_pub, counter=7)
        dist = build_distribution(state)
        assert dist.counter == 7
        assert dist.chain_key == chain_key

    def test_late_join_decrypts_after_distribution(self) -> None:
        """그룹 의 mid-stream join 시나리오 — alice 송신 2회 후 carol 의 join.

        carol 의 distribution 적용 시점 의 alice 의 advanced state →
        carol 도 alice 의 3번째 msg 의 decrypt 가능.
        """
        chain_key = _random_key()
        signing_pub = _random_key()
        alice = create_sender_key("alice", chain_key, signing_pub)
        # 그룹 안 의 메시지 2회 사전 송신 (carol 부재)
        _, alice = encrypt_group_message(alice, b"pre1")
        _, alice = encrypt_group_message(alice, b"pre2")
        # carol 의 join — distribution 송신
        dist = build_distribution(alice)
        carol = apply_distribution(dist)
        # alice 의 3번째 msg → carol decrypt
        ct, alice = encrypt_group_message(alice, b"after_join")
        decoded, carol = decrypt_group_message(carol, ct)
        assert decoded == b"after_join"
