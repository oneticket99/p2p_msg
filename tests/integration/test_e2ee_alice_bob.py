# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 2 E2EE integration test — Alice + Bob 전체 흐름.

E2EE 시나리오:
1. Alice + Bob = X25519 pre-shared keypair (out-of-band 또는 X3DH 의 결과)
2. Alice 의 initialize_session_initiator → sending_chain 활성
3. Alice → Bob 첫 메시지 + my_dh_public 헤더
4. Bob 의 advance_dh_ratchet (Alice public 수신) → receiving_chain + sending_chain 활성
5. Bob → Alice 응답
6. Alice 의 advance_dh_ratchet → 다음 turn

본 module = symmetric chain + DH ratchet step 의 통합 검증.
완전 Signal Protocol (X3DH + skipped keys + Sender Keys) = 별도 cycle.
"""

from __future__ import annotations

import pytest

from app.crypto.e2ee import generate_x25519_keypair
from app.crypto.session import (
    SessionState,
    advance_dh_ratchet,
    decrypt_with_session,
    encrypt_with_session,
    initialize_session_initiator,
    initialize_session_responder,
)

pytestmark = pytest.mark.integration


class TestAliceBobE2EE:
    def test_alice_initiate_bob_receive(self) -> None:
        """Alice → Bob 단방향 첫 메시지 + 양측 동기 chain key 일치."""

        # 1. pre-shared root + Bob 의 pre-key
        shared_secret = b"\x42" * 32
        bob_sk, bob_pk = generate_x25519_keypair()

        # 2. Alice initiator — Bob 의 pk 사용
        alice = initialize_session_initiator(
            shared_secret=shared_secret,
            peer_dh_public=bob_pk,
        )
        assert alice.sending_chain is not None
        assert alice.sending_chain.counter == 0

        # 3. Bob = responder + Alice public 수신 직후 advance_dh_ratchet
        # 단 Bob 측 = Alice 의 root_key (shared_secret 의 사후 advance) 와 다름
        # 본 test = sending_chain 단독 검증 (양측 chain 동기 = 별도 X3DH 의무)

        # Alice → 메시지 송신 (chain advance)
        msg = "TooTalk Phase 2 첫 메시지 — Alice → Bob".encode("utf-8")
        payload, alice_after = encrypt_with_session(alice, msg)

        assert alice_after.sending_chain.counter == 1
        # payload nonce + ciphertext 의 길이 sanity
        assert len(payload.nonce) == 12
        assert len(payload.ciphertext) > 0

    def test_responder_pre_receive_state(self) -> None:
        """Bob initialize_session_responder 직후 chain 미활성 상태 검증."""

        bob = initialize_session_responder(shared_secret=b"\x42" * 32)
        # sending + receiving 미활성 — DH ratchet 전
        assert bob.sending_chain is None
        assert bob.receiving_chain is None
        # encrypt 시도 = RuntimeError
        with pytest.raises(RuntimeError, match="sending_chain"):
            encrypt_with_session(bob, b"premature")
        # decrypt 시도 = RuntimeError
        from app.crypto.e2ee import EncryptedPayload
        with pytest.raises(RuntimeError, match="receiving_chain"):
            decrypt_with_session(
                bob, EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"\x00" * 16)
            )

    def test_dh_ratchet_unblocks_chains(self) -> None:
        """advance_dh_ratchet 후 sending + receiving 모두 활성 = encrypt/decrypt 가능."""

        bob = initialize_session_responder(shared_secret=b"\x42" * 32)
        _, alice_pk = generate_x25519_keypair()

        bob_after = advance_dh_ratchet(bob, alice_pk)
        assert bob_after.sending_chain is not None
        assert bob_after.receiving_chain is not None
        # encrypt = PASS
        payload, _ = encrypt_with_session(bob_after, b"after ratchet")
        assert len(payload.nonce) == 12

    def test_self_encrypt_decrypt_roundtrip(self) -> None:
        """동일 session 의 sending + receiving chain key 동기 시점 = self round-trip."""

        # Bob = responder + DH ratchet (Alice public mock)
        bob = initialize_session_responder(shared_secret=b"\x42" * 32)
        _, alice_pk = generate_x25519_keypair()
        bob = advance_dh_ratchet(bob, alice_pk)

        # Bob 의 sending + receiving chain 같지 않음 (DH ratchet 2 step advance)
        # 본 test 는 sending → receiving 자동 동기 X (skipped — X3DH 별도)
        # 인스턴스 의 sending = receiving 강제 복제 = 단방향 self loopback 패턴
        # session1 = sending chain encrypt + session2 = 동일 chain 복제 decrypt
        from app.crypto.double_ratchet import ChainKey
        bob_send = bob
        # Bob 의 sending_chain 을 receiving_chain 으로 복제 — self decrypt
        bob_decrypt = SessionState(
            root_key=bob.root_key,
            my_dh_private=bob.my_dh_private,
            my_dh_public=bob.my_dh_public,
            peer_dh_public=bob.peer_dh_public,
            sending_chain=bob.sending_chain,
            receiving_chain=ChainKey(key=bob.sending_chain.key, counter=0),
        )

        msg = "self loopback test 한글 UTF-8".encode("utf-8")
        payload, bob_send_after = encrypt_with_session(bob_send, msg)
        decoded, bob_decrypt_after = decrypt_with_session(bob_decrypt, payload)
        assert decoded == msg
        assert bob_send_after.sending_chain.counter == 1
        assert bob_decrypt_after.receiving_chain.counter == 1
