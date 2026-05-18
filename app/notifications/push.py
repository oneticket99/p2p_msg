# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 2 push 알림 skeleton — transport-agnostic 의 사이클 47.

Signal Protocol 의 offline device 깨움 패턴 정합. 다음 4 platform 지원
(skeleton — 실 전송 = 별개 cycle):
- ``APNS`` (Apple Push Notification service) — iOS / macOS
- ``FCM`` (Firebase Cloud Messaging) — Android / 일부 Desktop
- ``SILENT`` — visible alert 부재 + data-only payload (privacy-preserving 의무)
- ``PULL`` — push 부재 + server queue 의 pull fallback (FCM/APNS 미사용 시)

설계 결정
---------
- 본 module = pure 함수 (network IO 없음). 실 push gateway 호출 = caller 의무.
- E2EE 정합 — push payload 안 의 메시지 본문 (plaintext) 절대 금지. silent
  payload = envelope_id wake-up signal 만. visible payload = sender alias +
  generic preview ("새 메시지 1개" 등) 만 + 본문 부재.
- offline filter — online_device_ids set 의 보유. target.device_id 의 set
  부재 시 = push 대상.

본 module 범위
-------------
- ``Platform`` Enum — 4 transport 의 식별
- ``PushTarget`` frozen dataclass — user_id + device_id + Platform + push_token Optional
- ``PushPayload`` frozen dataclass — target + title/body Optional + data Dict + collapse_key Optional
- ``PushBatch`` frozen dataclass — N payload 묶음 + helpers
- ``format_silent_data_payload`` — 깨움 signal 의 silent push 산출 (privacy-preserving)
- ``format_visible_payload`` — generic visible push 산출 (low-priority preview)
- ``select_offline_targets`` — online device set 기준 filter

본 cycle 의 범위 외 (별개 cycle):
- APNS / FCM gateway 의 실 HTTP/HTTP2 호출 (aiohttp / httpx)
- iOS push certificate / Firebase service account 의 secrets 관리
- pull queue 의 server-side 영속화 (MariaDB push_queue table)
- E2EE envelope → push wake-up signal 의 server-side 변환
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Optional


class Platform(str, Enum):
    """Push transport 의 4 종 식별."""

    APNS = "apns"
    FCM = "fcm"
    SILENT = "silent"
    PULL = "pull"


@dataclass(frozen=True, slots=True)
class PushTarget:
    """단일 device 의 push 대상.

    Attributes
    ----------
    user_id : int
        recipient 사용자 식별자.
    device_id : str
        recipient device 의 식별자 (DeviceRegistry 정합).
    platform : Platform
        transport 의 4 종 의 1.
    push_token : bytes | None
        APNS device token 또는 FCM registration token (raw bytes).
        PULL platform = None 의무.
    """

    user_id: int
    device_id: str
    platform: Platform
    push_token: Optional[bytes] = None

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError(f"user_id 양수 의무 — {self.user_id}")
        if not self.device_id:
            raise ValueError("device_id 빈 문자열 불가")
        # PULL 의 platform = push_token 부재 의무 (server queue 만 사용)
        if self.platform == Platform.PULL and self.push_token is not None:
            raise ValueError("PULL platform 의 push_token 부재 의무")
        # APNS / FCM 의 platform = push_token 의무
        if self.platform in (Platform.APNS, Platform.FCM) and not self.push_token:
            raise ValueError(
                f"{self.platform.value} platform 의 push_token 의무"
            )


@dataclass(frozen=True, slots=True)
class PushPayload:
    """단일 push payload 본문.

    Attributes
    ----------
    target : PushTarget
        recipient 의 device.
    title : str | None
        visible push 의 제목. silent = None 의무.
    body : str | None
        visible push 본문 (generic preview 만, 실 메시지 plaintext 절대 금지).
        silent = None 의무.
    data : dict[str, str]
        custom data dict. envelope_id 등 의 wake-up signal 보관 권장.
    collapse_key : str | None
        FCM collapse_key (동일 key 의 multi push 의 1건 만 표시).
    """

    target: PushTarget
    title: Optional[str] = None
    body: Optional[str] = None
    data: Dict[str, str] = field(default_factory=dict)
    collapse_key: Optional[str] = None

    def __post_init__(self) -> None:
        # silent = visible field 부재 의무 (data-only 의무)
        is_silent = self.target.platform == Platform.SILENT
        if is_silent and (self.title is not None or self.body is not None):
            raise ValueError(
                "SILENT platform 의 title / body 의 None 의무 (data-only)"
            )

    @property
    def is_silent(self) -> bool:
        """silent (visible alert 부재) 여부."""

        return self.target.platform == Platform.SILENT


@dataclass(frozen=True, slots=True)
class PushBatch:
    """N device push 의 묶음.

    Attributes
    ----------
    payloads : list[PushPayload]
        각 device 별 push. 입력 순서 유지.
    """

    payloads: List[PushPayload] = field(default_factory=list)

    @property
    def total(self) -> int:
        """총 push 의 수."""

        return len(self.payloads)

    @property
    def silent_count(self) -> int:
        """silent push 의 수."""

        return sum(1 for p in self.payloads if p.is_silent)

    @property
    def visible_count(self) -> int:
        """visible push 의 수."""

        return self.total - self.silent_count

    def by_platform(self, platform: Platform) -> List[PushPayload]:
        """platform 별 payload list 의 filter."""

        return [p for p in self.payloads if p.target.platform == platform]


def format_silent_data_payload(
    target: PushTarget,
    envelope_id: str,
    *,
    extra_data: Optional[Dict[str, str]] = None,
) -> PushPayload:
    """silent push payload 산출 — privacy-preserving wake-up signal.

    Parameters
    ----------
    target : PushTarget
        recipient device. platform = SILENT 의무.
    envelope_id : str
        깨움 signal 의 envelope 식별자. caller 의 server queue 의 pop key 정합.
    extra_data : dict[str, str] | None
        추가 custom data. 메시지 plaintext 의 보관 절대 금지.

    Returns
    -------
    PushPayload
        title / body 부재 + data 안 의 envelope_id + (옵션) extra.

    Notes
    -----
    E2EE 정합 — 메시지 본문 (plaintext) 의 push 전달 절대 금지. silent
    의무 = client 의 wake-up + server 의 ciphertext pull.
    """

    if target.platform != Platform.SILENT:
        raise ValueError(
            f"SILENT platform 의무 — 실 = {target.platform.value}"
        )
    if not envelope_id:
        raise ValueError("envelope_id 빈 문자열 불가")
    data: Dict[str, str] = {"envelope_id": envelope_id}
    if extra_data:
        # extra_data 안 의 reserve key 충돌 차단
        if "envelope_id" in extra_data:
            raise ValueError("extra_data 의 envelope_id key 충돌")
        data.update(extra_data)
    return PushPayload(target=target, data=data)


def format_visible_payload(
    target: PushTarget,
    *,
    sender_alias: str,
    preview_count: int = 1,
    envelope_id: Optional[str] = None,
    collapse_key: Optional[str] = None,
) -> PushPayload:
    """visible push payload 산출 — low-priority generic preview.

    Parameters
    ----------
    target : PushTarget
        recipient device. platform = APNS / FCM 의무.
    sender_alias : str
        sender 의 표시 별명 (실 username / display_name). plaintext 본문 부재 의무.
    preview_count : int, default 1
        unread 메시지 갯수 의 generic preview ("새 메시지 N개").
    envelope_id : str | None
        client 단 의 ciphertext fetch 의 식별자.
    collapse_key : str | None
        FCM collapse 식별자.

    Returns
    -------
    PushPayload
        title = sender_alias + body = "새 메시지 N개" + envelope_id data.

    Notes
    -----
    body 안 실 메시지 plaintext 절대 금지 — generic preview 만 의무.
    """

    if target.platform not in (Platform.APNS, Platform.FCM):
        raise ValueError(
            f"APNS / FCM platform 의무 — 실 = {target.platform.value}"
        )
    if not sender_alias:
        raise ValueError("sender_alias 빈 문자열 불가")
    if preview_count <= 0:
        raise ValueError(f"preview_count 양수 의무 — {preview_count}")
    body = f"새 메시지 {preview_count}개"
    data: Dict[str, str] = {}
    if envelope_id:
        data["envelope_id"] = envelope_id
    return PushPayload(
        target=target,
        title=sender_alias,
        body=body,
        data=data,
        collapse_key=collapse_key,
    )


def select_offline_targets(
    targets: Iterable[PushTarget],
    online_device_ids: FrozenSet[str],
) -> List[PushTarget]:
    """online device 기준 filter — offline target 만 반환.

    Parameters
    ----------
    targets : Iterable[PushTarget]
        후보 device list.
    online_device_ids : frozenset[str]
        현재 online 의 device_id set. WebSocket 연결 추적 의 server-side 의무.

    Returns
    -------
    list[PushTarget]
        online_device_ids 의 부재 의 target 만. 입력 순서 유지.

    Notes
    -----
    빈 set = 모든 target 의 offline (= 모두 push 대상). 본 함수 = pure filter.
    """

    return [t for t in targets if t.device_id not in online_device_ids]
