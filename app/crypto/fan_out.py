# SPDX-License-Identifier: GPL-3.0-or-later
"""multi-device fan-out 송신 — Phase 2 사이클 44.

Signal Protocol multi-device 모델 정합. 1 sender → N recipient device
loop 송신. 각 device 별 독립 ratchet session 보유 (forward secrecy 의무
— 1 device 의 key 누출 → 다른 device 영향 없음).

본 module 범위
-------------
- ``FanOutEnvelope`` dataclass — 단일 device 의 ciphertext + 메타데이터
- ``FanOutBatch`` dataclass — N device 의 envelope 묶음
- ``encrypt_fan_out`` — sender 의 사용자 1명 의 모든 device 의 encrypt loop
- ``rotate_session`` — encrypt 후 advanced SessionState 의 caller 갱신 helper

설계 결정
---------
- sender 는 각 recipient device 별 SessionState 의 dict 보유 (device_id → state).
  loop 안 의 각 state 의 encrypt → advanced state 의 dict 갱신 의무.
- 1 device 의 ratchet 실패 = 다른 device 의 전송 차단 금지 (partial 송신 허용).
  실패 detail = FanOutEnvelope.error 필드 + FanOutBatch.failures count.
- 본 module = pure 함수 (network IO 없음). 실 네트워크 송신 = caller 의무
  (server signaling 의 fan-out 단계 의 별도 cycle).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.crypto.e2ee import EncryptedPayload
from app.crypto.session import SessionState, encrypt_with_session

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FanOutEnvelope:
    """단일 recipient device 의 fan-out 결과.

    Attributes
    ----------
    device_id : str
        recipient device 식별자.
    payload : EncryptedPayload | None
        encrypt 성공 시 ciphertext + nonce. 실패 = None.
    error : str | None
        encrypt 실패 사유. 성공 = None.
    """

    device_id: str
    payload: Optional[EncryptedPayload] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """encrypt 성공 여부."""

        return self.payload is not None and self.error is None


@dataclass(frozen=True, slots=True)
class FanOutBatch:
    """N device fan-out 결과 묶음 + 갱신된 SessionState dict.

    Attributes
    ----------
    envelopes : list[FanOutEnvelope]
        각 device 별 결과. 입력 순서 유지.
    advanced_sessions : dict[str, SessionState]
        encrypt 성공 device 의 advanced state. caller 단 갱신 의무.
    """

    envelopes: List[FanOutEnvelope] = field(default_factory=list)
    advanced_sessions: Dict[str, SessionState] = field(default_factory=dict)

    @property
    def successes(self) -> int:
        """성공 device 수."""

        return sum(1 for e in self.envelopes if e.ok)

    @property
    def failures(self) -> int:
        """실패 device 수."""

        return sum(1 for e in self.envelopes if not e.ok)

    @property
    def total(self) -> int:
        """총 device 수."""

        return len(self.envelopes)


def encrypt_fan_out(
    plaintext: bytes,
    sessions: Dict[str, SessionState],
    *,
    associated_data: Optional[bytes] = None,
) -> FanOutBatch:
    """N device 의 fan-out encrypt loop.

    Parameters
    ----------
    plaintext : bytes
        송신 메시지 본문. 매 device 의 동일 본문 + 별개 ratchet 의 encrypt.
    sessions : dict[str, SessionState]
        device_id → 현재 SessionState. encrypt 후 advanced state 반환.
    associated_data : bytes | None
        AES-GCM AAD. 모든 device 에 동일 적용.

    Returns
    -------
    FanOutBatch
        envelopes (device_id 순) + advanced_sessions dict.

    Notes
    -----
    빈 sessions = 빈 batch 반환 (FanOutBatch.total=0). 1 device 실패 =
    error 필드 보존 + 다른 device 의 encrypt 계속 (partial 송신 허용).
    """

    envelopes: List[FanOutEnvelope] = []
    advanced: Dict[str, SessionState] = {}

    for device_id, state in sessions.items():
        try:
            payload, new_state = encrypt_with_session(
                state, plaintext, associated_data=associated_data
            )
        except Exception as exc:  # noqa: BLE001 - per-device 실패 격리 의무
            log.warning(
                "fan-out encrypt 실패 — device_id=%s reason=%s",
                device_id,
                exc,
            )
            envelopes.append(FanOutEnvelope(device_id=device_id, error=str(exc)))
            continue
        envelopes.append(FanOutEnvelope(device_id=device_id, payload=payload))
        advanced[device_id] = new_state

    return FanOutBatch(envelopes=envelopes, advanced_sessions=advanced)


def rotate_session(
    sessions: Dict[str, SessionState],
    batch: FanOutBatch,
) -> Dict[str, SessionState]:
    """fan-out 후 sessions dict 갱신 helper.

    성공 device = advanced state 로 교체. 실패 device = 기존 state 유지.
    원본 dict 변경 없음 — 새 dict 반환 (immutable 의도).

    Returns
    -------
    dict[str, SessionState]
        device_id → state. successes 는 advanced + failures 는 stale.
    """

    next_sessions = dict(sessions)
    for device_id, advanced_state in batch.advanced_sessions.items():
        next_sessions[device_id] = advanced_state
    return next_sessions


def collect_failures(batch: FanOutBatch) -> List[Tuple[str, str]]:
    """실패 envelope 만 추출. (device_id, error) tuple list.

    UI 의 retry 또는 사용자 alert 용. 성공만 있는 경우 빈 list.
    """

    return [
        (e.device_id, e.error or "unknown")
        for e in batch.envelopes
        if not e.ok
    ]
