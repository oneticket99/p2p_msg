# SPDX-License-Identifier: GPL-3.0-or-later
"""bot streaming sse parser unit — cycle 169.732 신설."""

from __future__ import annotations


class TestParseSseLine:
    def test_empty_line_none(self) -> None:
        from app.bot.streaming.sse import parse_sse_line

        assert parse_sse_line("") is None
        assert parse_sse_line("   ") is None

    def test_comment_line_none(self) -> None:
        from app.bot.streaming.sse import parse_sse_line

        assert parse_sse_line(": heartbeat") is None

    def test_event_line(self) -> None:
        from app.bot.streaming.sse import StreamEvent, parse_sse_line

        chunk = parse_sse_line("event: message_start")
        assert chunk is not None
        assert chunk.event == StreamEvent.MESSAGE_START

    def test_openai_done_marker(self) -> None:
        from app.bot.streaming.sse import StreamEvent, parse_sse_line

        chunk = parse_sse_line("data: [DONE]")
        assert chunk.event == StreamEvent.MESSAGE_STOP
        assert chunk.done is True

    def test_anthropic_delta(self) -> None:
        from app.bot.streaming.sse import StreamEvent, parse_sse_line

        line = 'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi"}}'
        chunk = parse_sse_line(line)
        assert chunk.event == StreamEvent.CONTENT_BLOCK_DELTA
        assert chunk.delta_text == "Hi"

    def test_invalid_json_none(self) -> None:
        from app.bot.streaming.sse import parse_sse_line

        assert parse_sse_line("data: {not json") is None

    def test_non_data_non_event_none(self) -> None:
        from app.bot.streaming.sse import parse_sse_line

        assert parse_sse_line("id: 12345") is None


class TestExtractAnthropicDelta:
    def test_text_delta(self) -> None:
        from app.bot.streaming.sse import extract_anthropic_delta

        payload = {"type": "content_block_delta",
                   "delta": {"type": "text_delta", "text": "hello"}}
        assert extract_anthropic_delta(payload) == "hello"

    def test_missing_delta_empty(self) -> None:
        from app.bot.streaming.sse import extract_anthropic_delta

        assert extract_anthropic_delta({}) == ""

    def test_non_text_delta_empty(self) -> None:
        # 한글 주석 — type != text_delta → 빈
        from app.bot.streaming.sse import extract_anthropic_delta

        payload = {"delta": {"type": "input_json_delta", "partial_json": "x"}}
        assert extract_anthropic_delta(payload) == ""


class TestExtractOpenAIDelta:
    def test_content_delta(self) -> None:
        from app.bot.streaming.sse import extract_openai_delta

        payload = {"choices": [{"delta": {"content": "world"}}]}
        assert extract_openai_delta(payload) == "world"

    def test_missing_choices_empty(self) -> None:
        from app.bot.streaming.sse import extract_openai_delta

        assert extract_openai_delta({}) == ""


class TestAccumulateChunks:
    def test_empty_chunks(self) -> None:
        from app.bot.streaming.sse import accumulate_chunks

        assert accumulate_chunks([]) == ""

    def test_concat_deltas(self) -> None:
        from app.bot.streaming.sse import (
            StreamChunk, StreamEvent, accumulate_chunks,
        )

        chunks = [
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="Hello "),
            StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="World"),
            StreamChunk(event=StreamEvent.MESSAGE_STOP, done=True),
        ]
        assert accumulate_chunks(chunks) == "Hello World"


class TestIsTerminal:
    def test_done_flag(self) -> None:
        from app.bot.streaming.sse import StreamChunk, StreamEvent, is_terminal

        chunk = StreamChunk(event=StreamEvent.UNKNOWN, done=True)
        assert is_terminal(chunk) is True

    def test_message_stop_event(self) -> None:
        from app.bot.streaming.sse import StreamChunk, StreamEvent, is_terminal

        chunk = StreamChunk(event=StreamEvent.MESSAGE_STOP)
        assert is_terminal(chunk) is True

    def test_delta_not_terminal(self) -> None:
        from app.bot.streaming.sse import StreamChunk, StreamEvent, is_terminal

        chunk = StreamChunk(event=StreamEvent.CONTENT_BLOCK_DELTA, delta_text="x")
        assert is_terminal(chunk) is False
