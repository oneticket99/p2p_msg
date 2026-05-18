# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.fan_out`` 단위 테스트.

Signal Protocol multi-device fan-out 검증 — N device 의 별개 ciphertext +
forward secrecy (1 device 누출 의 다른 device 영향 없음) + partial 실패
격리 + advanced session dict 갱신 helper.
"""

from __future__ import annotations

from typing import Dict

import pytest

from app.crypto.e2ee import generate_x25519_keypair, x25519_shared_secret
from app.crypto.fan_out import (
    FanOutBatch,
    FanOutEnvelope,
    collect_failures,
    encrypt_fan_out,
    rotate_session,
)
from app.crypto.session import (
    SessionState,
    advance_dh_ratchet,
    decrypt_with_session,
    initialize_session_initiator,
    initialize_session_responder,
)


def _alice_bob_session_pair() -> tuple[SessionState, SessionState]:
    """Alice (initiator) + Bob (responder pre-receive 의 advance_dh_ratchet 적용)."""

    bob_priv, bob_pub = generate_x25519_keypair()
    alice_priv, _ = generate_x25519_keypair()
    shared = x25519_shared_secret(alice_priv, bob_pub)

    alice_state = initialize_session_initiator(
        shared_secret=shared, peer_dh_public=bob_pub
    )
    # Bob = responder pre-receive + advance_dh_ratchet 의 의 receiving_chain 활성
    bob_pre = initialize_session_responder(shared_secret=shared)
    # responder 의 keypair = Alice 가 의 peer 로 가정한 bob_pub 일치 의무
    bob_pre = SessionState(
        root_key=bob_pre.root_key,
        my_dh_private=bob_priv,
        my_dh_public=bob_pub,
        peer_dh_public=None,
        sending_chain=None,
        receiving_chain=None,
    )
    bob_state = advance_dh_ratchet(bob_pre, alice_state.my_dh_public)
    return (alice_state, bob_state)


def _multi_device_sessions(n: int) -> tuple[Dict[str, SessionState], Dict[str, SessionState]]:
    """sender N device 별개 session dict + recipient counterpart dict.

    각 device 별개 keypair = forward secrecy isolation 검증.
    """

    sender_sessions: Dict[str, SessionState] = {}
    recipient_sessions: Dict[str, SessionState] = {}
    for i in range(n):
        device_id = f"dev-{i}"
        a_state, b_state = _alice_bob_session_pair()
        sender_sessions[device_id] = a_state
        recipient_sessions[device_id] = b_state
    return (sender_sessions, recipient_sessions)


class TestFanOutEnvelope:
    def test_ok_with_payload(self) -> None:
        envelope = FanOutEnvelope(device_id="d1", payload=object())  # type: ignore[arg-type]
        assert envelope.ok is True

    def test_not_ok_with_error(self) -> None:
        envelope = FanOutEnvelope(device_id="d1", error="encrypt 실패")
        assert envelope.ok is False

    def test_not_ok_with_no_payload(self) -> None:
        envelope = FanOutEnvelope(device_id="d1")
        assert envelope.ok is False


class TestFanOutBatch:
    def test_empty_batch(self) -> None:
        batch = FanOutBatch()
        assert batch.total == 0
        assert batch.successes == 0
        assert batch.failures == 0

    def test_counts_mixed(self) -> None:
        env_ok = FanOutEnvelope(device_id="d1", payload=object())  # type: ignore[arg-type]
        env_fail = FanOutEnvelope(device_id="d2", error="boom")
        batch = FanOutBatch(envelopes=[env_ok, env_fail])
        assert batch.total == 2
        assert batch.successes == 1
        assert batch.failures == 1


class TestEncryptFanOut:
    def test_empty_sessions(self) -> None:
        batch = encrypt_fan_out(b"hello", {})
        assert batch.total == 0
        assert batch.successes == 0
        assert batch.advanced_sessions == {}

    def test_single_device(self) -> None:
        sender, recipient = _multi_device_sessions(1)
        batch = encrypt_fan_out(b"hello", sender)
        assert batch.total == 1
        assert batch.successes == 1
        assert batch.failures == 0
        # recipient decrypt 정상
        envelope = batch.envelopes[0]
        assert envelope.payload is not None
        decrypted, _ = decrypt_with_session(
            recipient["dev-0"], envelope.payload
        )
        assert decrypted == b"hello"

    def test_multi_device_all_succeed(self) -> None:
        sender, recipient = _multi_device_sessions(3)
        batch = encrypt_fan_out(b"meeting at 5pm", sender)
        assert batch.total == 3
        assert batch.successes == 3
        # 각 device 별개 ciphertext = forward secrecy isolation
        ciphertexts = {e.payload.ciphertext for e in batch.envelopes}  # type: ignore[union-attr]
        assert len(ciphertexts) == 3
        # 각 recipient device 의 decrypt 정상
        for envelope in batch.envelopes:
            decrypted, _ = decrypt_with_session(
                recipient[envelope.device_id], envelope.payload  # type: ignore[arg-type]
            )
            assert decrypted == b"meeting at 5pm"

    def test_partial_failure_isolated(self) -> None:
        """1 device 의 broken state = 다른 device 의 전송 계속."""

        sender, _recipient = _multi_device_sessions(3)
        # dev-1 sending_chain = None 인위적 broken
        broken_state = SessionState(
            root_key=sender["dev-1"].root_key,
            my_dh_private=sender["dev-1"].my_dh_private,
            my_dh_public=sender["dev-1"].my_dh_public,
            peer_dh_public=sender["dev-1"].peer_dh_public,
            sending_chain=None,  # 의도적 broken
            receiving_chain=sender["dev-1"].receiving_chain,
        )
        sender["dev-1"] = broken_state

        batch = encrypt_fan_out(b"hello", sender)
        assert batch.total == 3
        assert batch.successes == 2
        assert batch.failures == 1
        # dev-1 의 failure envelope
        failures = [e for e in batch.envelopes if not e.ok]
        assert len(failures) == 1
        assert failures[0].device_id == "dev-1"
        assert "sending_chain" in (failures[0].error or "")

    def test_associated_data_propagated(self) -> None:
        """AAD = 모든 device 의 동일 적용."""

        sender, recipient = _multi_device_sessions(2)
        aad = b"room-id-42"
        batch = encrypt_fan_out(b"hello", sender, associated_data=aad)
        assert batch.successes == 2
        for envelope in batch.envelopes:
            decrypted, _ = decrypt_with_session(
                recipient[envelope.device_id],
                envelope.payload,  # type: ignore[arg-type]
                associated_data=aad,
            )
            assert decrypted == b"hello"

    def test_ordering_preserved(self) -> None:
        sender, _ = _multi_device_sessions(5)
        batch = encrypt_fan_out(b"x", sender)
        device_ids = [e.device_id for e in batch.envelopes]
        assert device_ids == [f"dev-{i}" for i in range(5)]


class TestRotateSession:
    def test_successes_replaced(self) -> None:
        sender, _ = _multi_device_sessions(2)
        original_a = sender["dev-0"]
        batch = encrypt_fan_out(b"hi", sender)
        rotated = rotate_session(sender, batch)
        # advanced state = 새 sending_chain.counter 갱신
        assert rotated["dev-0"] is not original_a
        assert rotated["dev-0"].sending_chain is not None
        assert (
            rotated["dev-0"].sending_chain.counter
            > original_a.sending_chain.counter  # type: ignore[union-attr]
        )

    def test_failures_keep_original(self) -> None:
        sender, _ = _multi_device_sessions(2)
        broken = SessionState(
            root_key=sender["dev-1"].root_key,
            my_dh_private=sender["dev-1"].my_dh_private,
            my_dh_public=sender["dev-1"].my_dh_public,
            peer_dh_public=sender["dev-1"].peer_dh_public,
            sending_chain=None,
            receiving_chain=sender["dev-1"].receiving_chain,
        )
        sender["dev-1"] = broken
        batch = encrypt_fan_out(b"hi", sender)
        rotated = rotate_session(sender, batch)
        assert rotated["dev-1"] is broken  # 실패 = stale 유지

    def test_returns_new_dict(self) -> None:
        sender, _ = _multi_device_sessions(1)
        batch = encrypt_fan_out(b"x", sender)
        rotated = rotate_session(sender, batch)
        assert rotated is not sender


class TestCollectFailures:
    def test_all_ok_empty(self) -> None:
        sender, _ = _multi_device_sessions(2)
        batch = encrypt_fan_out(b"x", sender)
        assert collect_failures(batch) == []

    def test_failures_returned(self) -> None:
        sender, _ = _multi_device_sessions(2)
        broken = SessionState(
            root_key=sender["dev-1"].root_key,
            my_dh_private=sender["dev-1"].my_dh_private,
            my_dh_public=sender["dev-1"].my_dh_public,
            peer_dh_public=sender["dev-1"].peer_dh_public,
            sending_chain=None,
            receiving_chain=sender["dev-1"].receiving_chain,
        )
        sender["dev-1"] = broken
        batch = encrypt_fan_out(b"x", sender)
        failures = collect_failures(batch)
        assert len(failures) == 1
        assert failures[0][0] == "dev-1"
        assert "sending_chain" in failures[0][1]
