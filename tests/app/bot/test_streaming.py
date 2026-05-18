# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.streaming`` 단위 테스트.

StreamEvent Enum + StreamChunk + parse_sse_line (event/data/JSON/[DONE]) +
extract_anthropic_delta + extract_openai_delta + accumulate_chunks + is_terminal.
"""

from __future__ import annotations

import pytest

from app.bot.streaming import (
    StreamChunk,
    StreamEvent,
    accumulate_chunks,
    extract_anthropic_delta,
    extract_openai_delta,
    is_terminal,
    parse_sse_line,
)


class TestParseSseLineSkip:
    """빈 줄 + 주석 + 인식 불가 line 의 None 반환."""

    def test_empty_line(self) -> None:
        assert parse_sse_line("") is None

    def test_whitespace_only(self) -> None:
        assert parse_sse_line("   \t  ") is None

    def test_comment_line(self) -> None:
        assert parse_sse_line(": ping") is None

    def test_unknown_prefix(self) -> None:
        assert parse_sse_line("id: 12345") is None

    def test_invalid_json_data(self) -> None:
        assert parse_sse_line("data: {not json") is None

    def test_non_dict_json_data(self) -> None:
        assert parse_sse_line("data: 42") is None


class TestParseSseLineEvent:
    """event: <name> line 의 StreamChunk 의 event 만 반환."""

    def test_message_start(self) -> None:
        c = parse_sse_line("event: message_start")
        assert c is not None
        assert c.event == StreamEvent.MESSAGE_START
        assert c.delta_text == ""

    def test_content_block_delta(self) -> None:
        c = parse_sse_line("event: content_block_delta")
        assert c is not None
        assert c.event == StreamEvent.CONTENT_BLOCK_DELTA

    def test_unknown_event(self) -> None:
        c = parse_sse_line("event: weird_thing")
        assert c is not None
        assert c.event == StreamEvent.UNKNOWN


class TestParseSseLineDone:
    """OpenAI [DONE] terminal marker."""

    def test_openai_done(self) -> None:
        c = parse_sse_line("data: [DONE]")
        assert c is not None
        assert c.event == StreamEvent.MESSAGE_STOP
        assert c.done is True

    def test_done_with_whitespace(self) -> None:
        c = parse_sse_line("data:   [DONE]   ")
        assert c is not None
        assert c.done is True


class TestParseSseLineAnthropic:
    """Anthropic SSE chunk 의 parse + delta 추출."""

    def test_anthropic_text_delta(self) -> None:
        line = 'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "안녕"}}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.event == StreamEvent.CONTENT_BLOCK_DELTA
        assert c.delta_text == "안녕"

    def test_anthropic_message_start(self) -> None:
        line = 'data: {"type": "message_start", "message": {}}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.event == StreamEvent.MESSAGE_START
        assert c.delta_text == ""

    def test_anthropic_non_text_delta(self) -> None:
        # tool_use delta 등 비-text 의 빈 string
        line = 'data: {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{}"}}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.delta_text == ""


class TestParseSseLineOpenAI:
    """OpenAI SSE chunk 의 parse + delta 추출."""

    def test_openai_content_delta(self) -> None:
        line = 'data: {"choices": [{"index": 0, "delta": {"content": "hello", "role": "assistant"}}]}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.event == StreamEvent.CONTENT_BLOCK_DELTA
        assert c.delta_text == "hello"

    def test_openai_empty_choices(self) -> None:
        line = 'data: {"choices": []}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.delta_text == ""

    def test_openai_first_chunk_role_only(self) -> None:
        # 첫 chunk 의 role 만 + content 부재
        line = 'data: {"choices": [{"delta": {"role": "assistant"}}]}'
        c = parse_sse_line(line)
        assert c is not None
        assert c.delta_text == ""


class TestExtractAnthropicDelta:
    """``extract_anthropic_delta`` 단위 검증."""

    def test_happy(self) -> None:
        payload = {"delta": {"type": "text_delta", "text": "응답"}}
        assert extract_anthropic_delta(payload) == "응답"

    def test_missing_delta(self) -> None:
        assert extract_anthropic_delta({}) == ""

    def test_wrong_delta_type(self) -> None:
        payload = {"delta": {"type": "input_json_delta", "text": "x"}}
        assert extract_anthropic_delta(payload) == ""

    def test_non_string_text(self) -> None:
        payload = {"delta": {"type": "text_delta", "text": None}}
        assert extract_anthropic_delta(payload) == ""

    def test_non_dict_payload(self) -> None:
        assert extract_anthropic_delta(None) == ""  # type: ignore[arg-type]


class TestExtractOpenAIDelta:
    """``extract_openai_delta`` 단위 검증."""

    def test_happy(self) -> None:
        payload = {"choices": [{"delta": {"content": "hello"}}]}
        assert extract_openai_delta(payload) == "hello"

    def test_missing_choices(self) -> None:
        assert extract_openai_delta({}) == ""

    def test_empty_choices(self) -> None:
        assert extract_openai_delta({"choices": []}) == ""

    def test_missing_delta(self) -> None:
        assert extract_openai_delta({"choices": [{}]}) == ""

    def test_missing_content(self) -> None:
        assert extract_openai_delta(
            {"choices": [{"delta": {"role": "assistant"}}]}
        ) == ""


class TestAccumulateChunks:
    """``accumulate_chunks`` text 합본."""

    def test_empty(self) -> None:
        assert accumulate_chunks([]) == ""

    def test_single_chunk(self) -> None:
        chunks = [
            StreamChunk(
                event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="hi"
            )
        ]
        assert accumulate_chunks(chunks) == "hi"

    def test_multiple_chunks(self) -> None:
        chunks = [
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="안"),
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="녕"),
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text=""),
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="하"),
        ]
        assert accumulate_chunks(chunks) == "안녕하"

    def test_skip_terminal_no_text(self) -> None:
        chunks = [
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="ok"),
            StreamChunk(event=StreamEvent.MESSAGE_STOP, done=True),
        ]
        assert accumulate_chunks(chunks) == "ok"


class TestIsTerminal:
    """``is_terminal`` 종료 marker 판정."""

    def test_done_true(self) -> None:
        c = StreamChunk(event=StreamEvent.MESSAGE_STOP, done=True)
        assert is_terminal(c) is True

    def test_message_stop_without_done(self) -> None:
        c = StreamChunk(event=StreamEvent.MESSAGE_STOP)
        assert is_terminal(c) is True

    def test_delta_not_terminal(self) -> None:
        c = StreamChunk(
            event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="x"
        )
        assert is_terminal(c) is False
