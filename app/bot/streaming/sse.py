# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot streaming SSE parser — 사이클 87.

memory `project_bot_framework.md` + bot-framework.md §10 의 "streaming response
(SSE)" 별개 cycle entry. Anthropic Messages API + OpenAI Chat Completions API
의 SSE chunked response 의 parser layer.

본 module 범위
-------------
- ``StreamEvent`` Enum (MESSAGE_START / CONTENT_BLOCK_DELTA / MESSAGE_STOP /
  UNKNOWN 등 7종)
- ``StreamChunk`` frozen dataclass — event + data + delta_text + done
- ``parse_sse_line`` — "event: foo\\ndata: {...}" 의 line buffer 파싱
- ``extract_anthropic_delta`` — Anthropic delta.text 추출
- ``extract_openai_delta`` — OpenAI choices[0].delta.content 추출
- ``accumulate_chunks`` — 누적 chunks 의 text 합본

본 cycle 의 범위 외 (별개 cycle):
- httpx.AsyncClient.stream() 의 실 transport binding
- backpressure (slow consumer 의 의 buffer cap)
- tool_use streaming (function calling delta)
- 별개 SSE library 의존 (sse-starlette 등)
- 연결 끊김 시 reconnect + cursor resume
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, List, Optional


class StreamEvent(Enum):
    """SSE event 의 7종 매핑 — Anthropic + OpenAI 의 통일 추상."""

    MESSAGE_START = "message_start"  # Anthropic 의 message 시작
    CONTENT_BLOCK_START = "content_block_start"  # Anthropic content block 시작
    CONTENT_BLOCK_DELTA = "content_block_delta"  # Anthropic + OpenAI delta
    CONTENT_BLOCK_STOP = "content_block_stop"  # Anthropic content block 종료
    MESSAGE_DELTA = "message_delta"  # Anthropic message 의 의 metadata delta
    MESSAGE_STOP = "message_stop"  # Anthropic + OpenAI 종료 signal
    UNKNOWN = "unknown"  # 미지 event


# OpenAI 의 SSE 종료 signal — "data: [DONE]" 의 literal
_OPENAI_DONE_MARKER: Final[str] = "[DONE]"


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """단일 SSE chunk 의 parsed 결과.

    Attributes
    ----------
    event : StreamEvent
        event 종류 (Anthropic 의 event 또는 OpenAI 의 추정).
    data : dict
        chunk payload (JSON parse 결과 + 빈 dict default).
    delta_text : str
        chunk 의 incremental text (CONTENT_BLOCK_DELTA 의 경우 의 의 추출 결과).
    done : bool
        stream 종료 marker (MESSAGE_STOP 또는 OpenAI [DONE]).
    """

    event: StreamEvent
    data: dict = field(default_factory=dict)
    delta_text: str = ""
    done: bool = False


def _parse_event_string(raw: str) -> StreamEvent:
    """SSE event 문자열 → StreamEvent enum (미지 = UNKNOWN)."""

    raw_l = raw.strip().lower()
    for ev in StreamEvent:
        if ev.value == raw_l:
            return ev
    return StreamEvent.UNKNOWN


def parse_sse_line(line: str) -> Optional[StreamChunk]:
    """단일 SSE line 의 → StreamChunk (또는 None 의 skip).

    SSE format:
        event: <name>
        data: <json or literal>

    본 helper 는 한 줄 의 의 처리 의무. caller 의 multi-line buffer 의 의
    accumulation 의무 — 실 client 는 별개 cycle 의 streaming reader 의 layer.

    Notes
    -----
    - 빈 줄 + 주석 (": ...") → None
    - "data: [DONE]" → StreamChunk(event=MESSAGE_STOP, done=True)
    - "data: {...json}" → JSON parse + delta_text 추출 시도
    - "event: name" → event 만 의 chunk (data 부재)
    """

    stripped = line.strip()
    if not stripped or stripped.startswith(":"):
        return None
    if stripped.startswith("event:"):
        ev = _parse_event_string(stripped[len("event:") :])
        return StreamChunk(event=ev)
    if not stripped.startswith("data:"):
        return None
    raw_data = stripped[len("data:") :].strip()
    if raw_data == _OPENAI_DONE_MARKER:
        return StreamChunk(event=StreamEvent.MESSAGE_STOP, done=True)
    try:
        payload = json.loads(raw_data)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    # event 의 의 추정 — Anthropic = payload["type"], OpenAI = inference
    ev_raw = payload.get("type")
    if isinstance(ev_raw, str):
        ev = _parse_event_string(ev_raw)
    else:
        # OpenAI = type 부재 + choices array 존재 시 추정
        ev = (
            StreamEvent.CONTENT_BLOCK_DELTA
            if isinstance(payload.get("choices"), list)
            else StreamEvent.UNKNOWN
        )
    delta = ""
    if ev == StreamEvent.CONTENT_BLOCK_DELTA:
        delta = extract_anthropic_delta(payload) or extract_openai_delta(payload)
    return StreamChunk(event=ev, data=payload, delta_text=delta)


def extract_anthropic_delta(payload: dict) -> str:
    """Anthropic content_block_delta 의 ``delta.text`` 의 추출.

    Anthropic stream schema (요약)::

        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "..."}}

    Returns
    -------
    str
        추출된 text + 부재 시 빈 문자열.
    """

    if not isinstance(payload, dict):
        return ""
    delta = payload.get("delta")
    if not isinstance(delta, dict):
        return ""
    if delta.get("type") != "text_delta":
        return ""
    text = delta.get("text")
    return text if isinstance(text, str) else ""


def extract_openai_delta(payload: dict) -> str:
    """OpenAI streaming chunk 의 ``choices[0].delta.content`` 추출.

    OpenAI stream schema (요약)::

        {"choices": [{"index": 0, "delta": {"content": "...", "role": "assistant"}}]}

    Returns
    -------
    str
        추출된 content + 부재 시 빈 문자열.
    """

    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    return content if isinstance(content, str) else ""


def accumulate_chunks(chunks: List[StreamChunk]) -> str:
    """chunks 의 delta_text 의 의 순차 합본 — 종료 signal 의 의 무시.

    Returns
    -------
    str
        모든 chunk 의 delta_text 의 의 string 합. 빈 chunks = "".
    """

    if not chunks:
        return ""
    return "".join(c.delta_text for c in chunks if c.delta_text)


def is_terminal(chunk: StreamChunk) -> bool:
    """stream 종료 marker 의 판정 — done 또는 MESSAGE_STOP."""

    return chunk.done or chunk.event == StreamEvent.MESSAGE_STOP
