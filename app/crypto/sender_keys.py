# SPDX-License-Identifier: GPL-3.0-or-later
"""Signal Protocol Sender Keys — Phase 2 사이클 46.

그룹 채팅 의 N×M (각 메시지 의 N 멤버 × M 디바이스 곱) cipher 폭증 → N+M
reduction 구현. Signal Protocol 의 Sender Keys spec 정합.

설계 개요
---------
- 각 그룹 멤버 = 별개 ``SenderKey`` 보유 (32B chain_key + 32B signing public).
- 초기 분배 = pairwise X3DH/Double Ratchet session 1회 사용 의 ``SenderKeyDistribution``
  wire format 송신. 이후 그룹 메시지 = sender 가 sender 의 chain 1회만 encrypt.
- 수신자 = sender_id → SenderKeyState dict 보유. 각 sender 의 chain ratchet
  독립 갱신 — forward secrecy 보장.
- chain key advance = ``app.crypto.double_ratchet`` 의 KDF (HMAC-SHA256 + 0x01/0x02
  seed) 재사용. 별개 KDF 신설 회피.

본 module 범위
-------------
- ``SenderKeyState`` frozen dataclass — sender_id + ChainKey + signing_public_key
- ``SenderKeyDistribution`` frozen dataclass — wire format (분배 시 송신)
- ``create_sender_key`` — 초기 chain_key + signing_public 의 SenderKeyState 생성
- ``encrypt_group_message`` — sender 단 group encrypt + chain advance
- ``decrypt_group_message`` — recipient 단 group decrypt + chain advance
- ``build_distribution`` — SenderKeyState → 분배 wire format
- ``apply_distribution`` — 수신자 단 wire format → SenderKeyState 복원

본 cycle 의 범위 외 (별개 cycle):
- Ed25519 signature 검증 (signing_public_key 의 실 사용)
- skip 처리 (group 의 OOO 메시지)
- 그룹 멤버 변경 의 key 재생성 (member-leaves trigger)
- 서버 fan-out distribution 전송 path
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional, Tuple

from app.crypto.double_ratchet import ChainKey, decrypt_message, encrypt_message
from app.crypto.e2ee import EncryptedPayload

# signing public key 길이 = 32 byte (Ed25519 raw public — 본 cycle = placeholder)
_SIGNING_KEY_BYTES: Final[int] = 32
# chain key 길이 = 32 byte (ChainKey 자체 검증 의 의무)
_CHAIN_KEY_BYTES: Final[int] = 32


@dataclass(frozen=True, slots=True)
class SenderKeyState:
    """그룹 멤버 1명 의 sender key 현재 상태.

    Attributes
    ----------
    sender_id : str
        그룹 안 sender 식별자 (user_id 또는 device-scoped id).
    chain : ChainKey
        symmetric ratchet 의 chain key + counter (double_ratchet 의 ChainKey 재사용).
    signing_public_key : bytes
        sender 의 Ed25519 public (32 byte). 본 cycle = 미사용 (signature 별개 cycle).
    """

    sender_id: str
    chain: ChainKey
    signing_public_key: bytes

    def __post_init__(self) -> None:
        # sender_id 빈 문자열 차단 — 그룹 안 식별 의무
        if not self.sender_id:
            raise ValueError("sender_id 빈 문자열 불가")
        if len(self.signing_public_key) != _SIGNING_KEY_BYTES:
            raise ValueError(
                f"signing_public_key 길이 불일치 — "
                f"len={len(self.signing_public_key)} (기대 {_SIGNING_KEY_BYTES})"
            )


@dataclass(frozen=True, slots=True)
class SenderKeyDistribution:
    """신규 그룹 멤버 의 wire format — pairwise session 의 1회 송신 의무.

    Attributes
    ----------
    sender_id : str
        sender 식별자.
    chain_key : bytes
        초기 chain key 의 raw 32 byte.
    counter : int
        chain key 의 현재 counter — 그룹 join 시점 의 sender 상태 반영.
    signing_public_key : bytes
        sender 의 Ed25519 public (32 byte).
    """

    sender_id: str
    chain_key: bytes
    counter: int
    signing_public_key: bytes

    def __post_init__(self) -> None:
        # 모든 필드 의 wire format 정합 검증
        if not self.sender_id:
            raise ValueError("sender_id 빈 문자열 불가")
        if len(self.chain_key) != _CHAIN_KEY_BYTES:
            raise ValueError(
                f"chain_key 길이 불일치 — "
                f"len={len(self.chain_key)} (기대 {_CHAIN_KEY_BYTES})"
            )
        if self.counter < 0:
            raise ValueError(f"counter 음수 불가 — {self.counter}")
        if len(self.signing_public_key) != _SIGNING_KEY_BYTES:
            raise ValueError(
                f"signing_public_key 길이 불일치 — "
                f"len={len(self.signing_public_key)} (기대 {_SIGNING_KEY_BYTES})"
            )


def create_sender_key(
    sender_id: str,
    initial_chain_key: bytes,
    signing_public_key: bytes,
    *,
    counter: int = 0,
) -> SenderKeyState:
    """초기 ``SenderKeyState`` 생성.

    Parameters
    ----------
    sender_id : str
        sender 식별자.
    initial_chain_key : bytes
        32 byte 초기 chain key (HKDF 또는 secrets.token_bytes 의 외부 산출).
    signing_public_key : bytes
        sender 의 Ed25519 public (32 byte).
    counter : int, default 0
        chain key 의 초기 counter.

    Returns
    -------
    SenderKeyState
        초기 상태. encrypt/decrypt 의 의 시작점.
    """

    chain = ChainKey(key=initial_chain_key, counter=counter)
    return SenderKeyState(
        sender_id=sender_id,
        chain=chain,
        signing_public_key=signing_public_key,
    )


def encrypt_group_message(
    state: SenderKeyState,
    plaintext: bytes,
    *,
    associated_data: Optional[bytes] = None,
) -> Tuple[EncryptedPayload, SenderKeyState]:
    """sender 단 그룹 메시지 encrypt + chain advance.

    Parameters
    ----------
    state : SenderKeyState
        sender 의 현재 상태.
    plaintext : bytes
        암호화 대상 본문.
    associated_data : bytes | None
        AES-GCM AAD. sender_id 등 의 메타데이터 binding 권장.

    Returns
    -------
    tuple[EncryptedPayload, SenderKeyState]
        (ciphertext, advanced state). caller 의 advanced state 의 저장 의무.

    Notes
    -----
    double_ratchet 의 ``encrypt_message`` 재사용 — chain → message key →
    AES-GCM encrypt. counter 자동 +1.
    """

    payload, next_chain = encrypt_message(
        state.chain, plaintext, associated_data=associated_data
    )
    next_state = SenderKeyState(
        sender_id=state.sender_id,
        chain=next_chain,
        signing_public_key=state.signing_public_key,
    )
    return (payload, next_state)


def decrypt_group_message(
    state: SenderKeyState,
    payload: EncryptedPayload,
    *,
    associated_data: Optional[bytes] = None,
) -> Tuple[bytes, SenderKeyState]:
    """recipient 단 그룹 메시지 decrypt + chain advance.

    Parameters
    ----------
    state : SenderKeyState
        recipient 단 의 sender 의 현재 SenderKeyState.
    payload : EncryptedPayload
        sender 의 encrypt 결과.
    associated_data : bytes | None
        AES-GCM AAD. encrypt 단 의 동일 값 의무.

    Returns
    -------
    tuple[bytes, SenderKeyState]
        (plaintext, advanced state). caller 의 advanced state 의 저장 의무.

    Notes
    -----
    sender + recipient 의 chain counter 동일 의무. 불일치 = AES-GCM 의
    decrypt 실패 (InvalidTag exception) — 별개 skip 처리 cycle.
    """

    plaintext, next_chain = decrypt_message(
        state.chain, payload, associated_data=associated_data
    )
    next_state = SenderKeyState(
        sender_id=state.sender_id,
        chain=next_chain,
        signing_public_key=state.signing_public_key,
    )
    return (plaintext, next_state)


def build_distribution(state: SenderKeyState) -> SenderKeyDistribution:
    """``SenderKeyState`` → ``SenderKeyDistribution`` wire format 산출.

    pairwise session 의 1회 송신 의무. 수신자 단 의 ``apply_distribution``
    의 reverse 함수.
    """

    return SenderKeyDistribution(
        sender_id=state.sender_id,
        chain_key=state.chain.key,
        counter=state.chain.counter,
        signing_public_key=state.signing_public_key,
    )


def apply_distribution(distribution: SenderKeyDistribution) -> SenderKeyState:
    """wire format → 수신자 단 의 ``SenderKeyState`` 복원.

    Notes
    -----
    수신자 의 모든 그룹 멤버 별 SenderKeyState dict (sender_id → state) 보유 의무.
    동일 sender 의 신규 distribution 수신 = 기존 state 의 완전 교체 (group rekey
    semantics — 별개 cycle 의 정책 명시 의무).
    """

    return create_sender_key(
        sender_id=distribution.sender_id,
        initial_chain_key=distribution.chain_key,
        signing_public_key=distribution.signing_public_key,
        counter=distribution.counter,
    )
