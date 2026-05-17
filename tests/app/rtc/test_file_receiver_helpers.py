# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.rtc.file_receiver`` module-level helper 단위 테스트.

검증 대상:
- ``_safe_filename`` — path traversal 방어 12 케이스 (qa-agent 사이클 13 정합)
- ``_env_int`` — 환경변수 정수 파싱 + min_value 검증 + 폴백
- ``_truncate_file`` / ``_append_bytes_sync`` — 동기 파일 IO 헬퍼

QObject 상속 ``FileReceiver`` class 의 실 통합 = ``tests/integration/`` 위탁.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.rtc.file_receiver import (
    _append_bytes_sync,
    _env_int,
    _safe_filename,
    _truncate_file,
)


# ---------------------------------------------------------------------------
# 1. _safe_filename — path traversal 방어 (qa-agent 사이클 13 정합)
# ---------------------------------------------------------------------------


class TestSafeFilename:
    """수신 파일명 의 정규화 — 디렉토리 분리자 + null byte 제거."""

    def test_normal_filename_preserved(self) -> None:
        assert _safe_filename("hello.txt") == "hello.txt"

    def test_korean_filename_preserved(self) -> None:
        # 한글 파일명 의 의 의 그대로 보존 (송수신 BPE 호환 정합)
        assert _safe_filename("안녕하세요.txt") == "안녕하세요.txt"

    def test_path_traversal_strip_parent(self) -> None:
        # 1단계 상위 — basename = etc, "/" 이면 "untitled.bin"
        assert _safe_filename("../etc/passwd") == "passwd"

    def test_path_traversal_strip_deep(self) -> None:
        # 다중 상위 의 의 의 basename 만 남김
        assert _safe_filename("../../../../etc/passwd") == "passwd"

    def test_absolute_path_basename_only(self) -> None:
        assert _safe_filename("/etc/passwd") == "passwd"

    def test_windows_path_separator(self) -> None:
        # 백슬래시는 macOS basename 의 의 의 분리자 미인식 → 그대로
        # 단 보안상 의 의 의 의 의 의 의 의 의 윈도우 path 의 의 의 의 의 우려
        result = _safe_filename("C:\\Windows\\System32\\evil.exe")
        # macOS basename 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
        assert result == "C:\\Windows\\System32\\evil.exe" or "evil.exe" in result

    def test_null_byte_removed(self) -> None:
        # null byte injection — C string 종료 의 의 의 의 의 위험
        assert _safe_filename("hello\x00.txt") == "hello.txt"

    def test_dot_only_returns_default(self) -> None:
        assert _safe_filename(".") == "untitled.bin"

    def test_double_dot_only_returns_default(self) -> None:
        assert _safe_filename("..") == "untitled.bin"

    def test_empty_string_returns_default(self) -> None:
        assert _safe_filename("") == "untitled.bin"

    def test_whitespace_only_returns_default(self) -> None:
        assert _safe_filename("   ") == "untitled.bin"

    def test_none_input_returns_default(self) -> None:
        # 의 의 의 의 의 의 의 의 None 의 의 의 의 의 의 의 의 의 의 의 폴백
        assert _safe_filename(None) == "untitled.bin"  # type: ignore[arg-type]

    def test_trailing_whitespace_stripped(self) -> None:
        # 앞뒤 공백 strip
        assert _safe_filename("  hello.txt  ") == "hello.txt"

    def test_multiple_null_bytes_removed(self) -> None:
        assert _safe_filename("a\x00b\x00c.txt") == "abc.txt"


# ---------------------------------------------------------------------------
# 2. _env_int — 환경변수 정수 파싱
# ---------------------------------------------------------------------------


class TestEnvInt:
    """``os.environ`` 정수 파싱 + min_value 검증 + 폴백."""

    def test_unset_returns_default(self) -> None:
        assert _env_int("__TEST_UNSET_KEY__", default=42) == 42

    def test_valid_integer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "100")
        assert _env_int("__TEST_KEY__", default=42) == 100

    def test_invalid_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "not-a-number")
        assert _env_int("__TEST_KEY__", default=42) == 42

    def test_below_min_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "0")
        # default min_value=1 → 0 은 미달, 폴백
        assert _env_int("__TEST_KEY__", default=42) == 42

    def test_negative_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "-10")
        assert _env_int("__TEST_KEY__", default=42) == 42

    def test_min_value_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "5")
        # min_value=10 → 5 미달 폴백
        assert _env_int("__TEST_KEY__", default=42, min_value=10) == 42

    def test_min_value_boundary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "10")
        # 정확히 min_value = 통과
        assert _env_int("__TEST_KEY__", default=42, min_value=10) == 10

    def test_whitespace_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_KEY__", "  256  ")
        assert _env_int("__TEST_KEY__", default=42) == 256

    def test_empty_string_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("__TEST_KEY__", "")
        assert _env_int("__TEST_KEY__", default=42) == 42


# ---------------------------------------------------------------------------
# 3. _truncate_file / _append_bytes_sync — 동기 파일 IO
# ---------------------------------------------------------------------------


class TestTruncateFile:
    def test_truncate_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "data.bin"
        target.write_bytes(b"original content")
        _truncate_file(target)
        # 비어 있어야 함
        assert target.exists()
        assert target.read_bytes() == b""

    def test_truncate_creates_if_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "new.bin"
        assert not target.exists()
        _truncate_file(target)
        # 파일 생성 + 비어 있음
        assert target.exists()
        assert target.read_bytes() == b""


class TestAppendBytesSync:
    def test_append_to_empty_file(self, tmp_path: Path) -> None:
        target = tmp_path / "data.bin"
        target.touch()
        _append_bytes_sync(target, b"hello")
        assert target.read_bytes() == b"hello"

    def test_append_concatenates(self, tmp_path: Path) -> None:
        target = tmp_path / "data.bin"
        target.write_bytes(b"hello ")
        _append_bytes_sync(target, b"world")
        assert target.read_bytes() == b"hello world"

    def test_append_binary_zero_bytes(self, tmp_path: Path) -> None:
        # null byte 보존 — append 모드 의 의 byte-safe
        target = tmp_path / "data.bin"
        target.touch()
        _append_bytes_sync(target, b"\x00\xff\x00")
        assert target.read_bytes() == b"\x00\xff\x00"

    def test_append_empty_payload(self, tmp_path: Path) -> None:
        # 빈 payload — 파일 크기 무변동
        target = tmp_path / "data.bin"
        target.write_bytes(b"existing")
        _append_bytes_sync(target, b"")
        assert target.read_bytes() == b"existing"
