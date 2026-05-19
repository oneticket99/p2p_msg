# SPDX-License-Identifier: GPL-3.0-or-later
"""DataChannel message payload schema — cycle 156 신설.

WebRTC DataChannel + signaling fallback 양쪽 의 json payload schema 통합.
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
            # 한글 주석 — frozen dataclass 안 ts default = epoch millis 강제 보정
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
