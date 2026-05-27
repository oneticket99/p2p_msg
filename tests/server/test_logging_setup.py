# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.logging_setup`` 단위 테스트.

KSTFormatter + KSTJSONFormatter + RedactingFilter + configure_logging
의 4 component 의 정합 검증.
"""

from __future__ import annotations

import io
import json
import logging
import re
from typing import Any

import pytest

from server.logging_setup import (
    KSTFormatter,
    KSTJSONFormatter,
    RedactingFilter,
    configure_logging,
    redact_sensitive,
)


def _make_record(
    *,
    level: int = logging.INFO,
    msg: str = "hello",
    name: str = "test.logger",
    args: Any = None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=42,
        msg=msg,
        args=args,
        exc_info=None,
    )


class TestKSTFormatter:
    def test_format_includes_kst_marker(self) -> None:
        formatter = KSTFormatter()
        out = formatter.format(_make_record(msg="msg-body"))
        assert "KST" in out
        assert "INFO" in out
        assert "msg-body" in out
        assert "test.logger" in out

    def test_request_id_dash_when_no_context(self) -> None:
        formatter = KSTFormatter()
        out = formatter.format(_make_record())
        # middleware 외 → request_id = "-"
        assert "[-]" in out

    def test_timestamp_format_iso_like(self) -> None:
        formatter = KSTFormatter()
        out = formatter.format(_make_record())
        # [YYYY-mm-dd HH:MM:SS.mmm KST] prefix 검증
        assert re.search(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} KST\]", out)


class TestKSTJSONFormatter:
    def test_basic_json_payload(self) -> None:
        formatter = KSTJSONFormatter()
        out = formatter.format(_make_record(msg="json-test"))
        payload = json.loads(out)
        assert payload["level"] == "INFO"
        assert payload["name"] == "test.logger"
        assert payload["message"] == "json-test"
        assert "ts" in payload
        assert payload["request_id"] == "-"

    def test_iso_timestamp_with_kst_offset(self) -> None:
        formatter = KSTJSONFormatter()
        payload = json.loads(formatter.format(_make_record()))
        # KST = +09:00
        assert "+09:00" in payload["ts"]

    def test_extra_fields_absorbed(self) -> None:
        formatter = KSTJSONFormatter()
        record = _make_record()
        record.user_id = 42
        record.action = "login"
        payload = json.loads(formatter.format(record))
        assert payload["extra"]["user_id"] == 42
        assert payload["extra"]["action"] == "login"

    def test_unicode_korean_preserved(self) -> None:
        formatter = KSTJSONFormatter()
        out = formatter.format(_make_record(msg="한글 메시지"))
        payload = json.loads(out)
        assert payload["message"] == "한글 메시지"

    def test_exception_info_included(self) -> None:
        formatter = KSTJSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="t.py",
                lineno=1,
                msg="boom",
                args=None,
                exc_info=sys.exc_info(),
            )
        payload = json.loads(formatter.format(record))
        assert "exc_info" in payload
        assert "ValueError" in payload["exc_info"]


class TestRedactSensitive:
    def test_anthropic_api_key(self) -> None:
        out = redact_sensitive("token=sk-ant-api01-abc1234567890123456789xyz")
        assert "sk-ant-api01-abc" not in out
        assert "sk-***" in out

    def test_bearer_token(self) -> None:
        out = redact_sensitive("Authorization: Bearer abcdef0123456789xyzABCDEF")
        assert "Bearer ***" in out
        assert "abcdef0123456789" not in out

    def test_jwt_token(self) -> None:
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdef_xyz"
        out = redact_sensitive(f"jwt={jwt}")
        assert "jwt-***" in out
        assert "eyJhbGciOiJIUzI1NiJ9" not in out

    def test_password_field(self) -> None:
        out = redact_sensitive("password=mySecret123")
        assert "password=***" in out
        assert "mySecret123" not in out

    def test_api_key_field(self) -> None:
        out = redact_sensitive("api_key=verysecret-xyz")
        assert "api_key=***" in out

    def test_rrn_redacted(self) -> None:
        out = redact_sensitive("주민번호: 901225-1234567")
        assert "901225-1234567" not in out
        assert "RRN-***" in out

    def test_card_number_redacted(self) -> None:
        out = redact_sensitive("card: 4111-1111-1111-1111")
        assert "4111-1111-1111-1111" not in out
        assert "CARD-***" in out

    def test_email_partial_mask_domain_preserved(self) -> None:
        out = redact_sensitive("user@example.com")
        # local part 의 첫 3자 + ***  + 도메인 보존
        assert "@example.com" in out
        assert "use***@example.com" in out

    def test_db_connection_string(self) -> None:
        out = redact_sensitive("mysql://admin:secretPW@host:3306/db")
        assert "mysql://***:***@" in out
        assert "secretPW" not in out

    def test_benign_message_unchanged(self) -> None:
        msg = "사용자 로그인 성공 — user_id=42"
        out = redact_sensitive(msg)
        assert out == msg

    def test_empty_string(self) -> None:
        assert redact_sensitive("") == ""


class TestRedactingFilter:
    def test_filter_msg_redacted(self) -> None:
        record = _make_record(msg="api_key=verysecret-xyz")
        filt = RedactingFilter()
        filt.filter(record)
        assert "verysecret" not in record.msg
        assert "***" in record.msg

    def test_filter_args_redacted(self) -> None:
        record = _make_record(msg="login: %s", args=("password=hunter2",))
        filt = RedactingFilter()
        filt.filter(record)
        assert "hunter2" not in record.getMessage()

    def test_filter_extras_redacted(self) -> None:
        record = _make_record()
        record.token = "sk-ant-api01-abcdefghij1234567890xyz"
        filt = RedactingFilter()
        filt.filter(record)
        assert "abcdefghij" not in record.token
        assert "sk-***" in record.token

    def test_filter_returns_true(self) -> None:
        # filter 의 return True 의무 (record propagate)
        record = _make_record(msg="hello")
        assert RedactingFilter().filter(record) is True


class TestConfigureLogging:
    def test_text_format_default(self) -> None:
        configure_logging(level="DEBUG", log_format="text")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, KSTFormatter)

    def test_json_format_active(self) -> None:
        configure_logging(level="INFO", log_format="json")
        root = logging.getLogger()
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, KSTJSONFormatter)

    def test_invalid_level_falls_back_info(self) -> None:
        configure_logging(level="NONSENSE", log_format="text")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_redact_filter_attached(self) -> None:
        configure_logging(level="INFO", log_format="text")
        root = logging.getLogger()
        assert any(isinstance(f, RedactingFilter) for f in root.filters)

    def test_redact_disabled(self) -> None:
        configure_logging(level="INFO", log_format="text", enable_redact=False)
        root = logging.getLogger()
        assert not any(isinstance(f, RedactingFilter) for f in root.filters)

    def test_idempotent_handler_clear(self) -> None:
        configure_logging(level="INFO", log_format="text")
        configure_logging(level="INFO", log_format="json")
        root = logging.getLogger()
        # 2 회 호출 의 1 handler 만 유지
        assert len(root.handlers) == 1

    def test_aiohttp_access_capped_to_warning(self) -> None:
        configure_logging(level="DEBUG", log_format="text")
        access = logging.getLogger("aiohttp.access")
        assert access.level == logging.WARNING


class TestEndToEndLogging:
    """real logger emit + handler capture — JSON output 의 wire-level."""

    def test_json_output_with_redact(self, capsys: pytest.CaptureFixture) -> None:
        configure_logging(level="INFO", log_format="json")
        logger = logging.getLogger("test.e2e")
        logger.info("user login api_key=sk-ant-api01-abcdef123456789012345xyz")
        captured = capsys.readouterr()
        # JSON line 의 parse + redact 검증
        line = captured.out.strip().split("\n")[-1]
        payload = json.loads(line)
        assert "sk-ant-api01" not in payload["message"]
        assert "api_key=***" in payload["message"]

    def test_text_output_kst_prefix(self, capsys: pytest.CaptureFixture) -> None:
        configure_logging(level="INFO", log_format="text")
        logger = logging.getLogger("test.e2e")
        logger.info("simple message")
        captured = capsys.readouterr()
        assert "KST" in captured.out
        assert "simple message" in captured.out


@pytest.fixture(autouse=True)
def _restore_logging() -> Any:
    """모든 test 후 root logger handler 의 cleanup — 다른 test pollution 회피."""

    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    for f in list(root.filters):
        root.removeFilter(f)
    root.setLevel(logging.WARNING)
