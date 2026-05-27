# SPDX-License-Identifier: GPL-3.0-or-later
"""DataChannel message payload schema — cycle 156 신설.

역할 — WebRTC DataChannel(P2P 직결)과 signaling fallback 양쪽이 공유하는 단일
JSON payload schema 와 직렬화/역직렬화 + 안전 생성 helper 를 제공한다.

계층 위치 — app/net 클라이언트 계층(정본 §E)의 wire 모델. rtc(DataChannel send/
recv) + UI(MessageBubble) 양쪽이 본 schema 를 거친다. 서버 영속 스키마와 별개의
전송용 계약(wire contract).

의존성 — 표준 `dataclasses`/`json`/`uuid`/`datetime`(외부 의존 부재). frozen
dataclass 라 불변 — 보정은 `__post_init__` 의 `object.__setattr__`.

범위 한계 — 직렬화/역직렬화 + 기본값 보정만. 암복호·전송·순서 보장은 호출자(rtc)
책임. 미지원 type 은 text 로 graceful 폴백(crash 차단).

reply_to + reactions field 포함 (cycle 153.6 MessageBubble + cycle 155 reactions
REST endpoint 정합).

schema v1.0:
    {
        "schema": "tootalk.msg.v1",
        "type": "text" | "file" | "sticker" | "system",
        "id": str,           # message uuid (cycle 156 신설)
        "sender": str,       # sender user_id 또는 nickname
        "text": str,         # 본문 (type=text 의무)
        "ts": int,           # epoch millis (UTC)
        "reply_to": {
            "message_id": str,
            "sender": str,
            "preview": str   # 60자 cap
        } | null,
        "reactions": {
            "👍": int,
            "❤️": int,
            ...
        }                    # optional
    }
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

SCHEMA_VERSION = "tootalk.msg.v1"

VALID_TYPES = ("text", "file", "sticker", "system")


@dataclass(frozen=True)
class ReplyToField:
    """payload 안 reply_to subfield."""
    message_id: str
    sender: str
    preview: str  # 60자 cap


@dataclass(frozen=True)
class MessagePayload:
    """DataChannel json payload model."""
    type: str = "text"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    text: str = ""
    ts: int = 0
    reply_to: Optional[ReplyToField] = None
    reactions: Optional[dict] = None
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.ts == 0:
            # ts 미지정 시 현재 epoch millis 로 보정 — frozen 이라 object.__setattr__ 우회
            object.__setattr__(self, "ts", int(datetime.now(timezone.utc).timestamp() * 1000))
        if self.type not in VALID_TYPES:
            log.warning("[protocol] type=%r 무효 — text 폴백", self.type)
            object.__setattr__(self, "type", "text")

    def to_json(self) -> str:
        """payload → json string (DataChannel.send 의무)."""
        d = asdict(self)
        if self.reply_to is None:
            d["reply_to"] = None
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "MessagePayload":
        """json string → payload model (DataChannel receive 의무)."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("[protocol] json decode 실패 — %r", exc)
            return cls(type="system", text=f"[invalid payload: {exc}]")

        reply_to_raw = data.get("reply_to")
        reply_to_obj: Optional[ReplyToField] = None
        if reply_to_raw and isinstance(reply_to_raw, dict):
            reply_to_obj = ReplyToField(
                message_id=str(reply_to_raw.get("message_id", "")),
                sender=str(reply_to_raw.get("sender", "")),
                preview=str(reply_to_raw.get("preview", ""))[:60],
            )

        return cls(
            type=str(data.get("type", "text")),
            id=str(data.get("id", str(uuid.uuid4()))),
            sender=str(data.get("sender", "")),
            text=str(data.get("text", "")),
            ts=int(data.get("ts", 0)),
            reply_to=reply_to_obj,
            reactions=data.get("reactions"),
            schema=str(data.get("schema", SCHEMA_VERSION)),
        )


def build_text_payload(
    sender: str,
    text: str,
    reply_to: Optional[ReplyToField] = None,
) -> MessagePayload:
    """간편 text payload 생성 helper."""
    return MessagePayload(
        type="text",
        sender=sender,
        text=text,
        reply_to=reply_to,
    )
