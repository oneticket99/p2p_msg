# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.rtc.file_sender`` module-level helper 단위 테스트.

검증 대상:
- ``_env_int`` — file_receiver 와 동일 시그니처 의 의 의 별도 모듈 정합 검증
- ``_sha256_of_file`` — 파일 전체 sha256 hex round-trip + 빈 파일 + 대용량

QObject 상속 ``FileSender`` class 의 backpressure 통합 = ``tests/integration/`` 위탁.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.rtc.file_sender import _env_int, _sha256_of_file


# ---------------------------------------------------------------------------
# 1. _env_int — file_receiver._env_int 와 동일 시그니처 정합
# ---------------------------------------------------------------------------


class TestEnvInt:
    """``_env_int`` 동일 시그니처 — 두 모듈 의 의 의 의 의 의 정합 검증."""

    def test_unset_returns_default(self) -> None:
        assert _env_int("__SENDER_UNSET__", default=16384) == 16384

    def test_valid_integer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__SENDER_KEY__", "32768")
        assert _env_int("__SENDER_KEY__", default=16384) == 32768

    def test_min_value_default_1(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("__SENDER_KEY__", "0")
        assert _env_int("__SENDER_KEY__", default=16384) == 16384

    @pytest.mark.parametrize("raw", ["garbage", "1.5", "1e3", "0xFF"])
    def test_invalid_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        # int() 의 의 의 의 의 float / hex / scientific 모두 거부
        monkeypatch.setenv("__SENDER_KEY__", raw)
        assert _env_int("__SENDER_KEY__", default=16384) == 16384

    def test_realistic_buffer_high(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # observability-baseline.md §3 — FILE_BUFFER_HIGH default 16 MiB
        monkeypatch.setenv("FILE_BUFFER_HIGH", str(16 * 1024 * 1024))
        assert _env_int("FILE_BUFFER_HIGH", default=4 * 1024 * 1024) == 16777216


# ---------------------------------------------------------------------------
# 2. _sha256_of_file — 파일 전체 SHA-256
# ---------------------------------------------------------------------------


class TestSha256OfFile:
    """파일 sha256 동기 산출 — 점진 chunk + 표준 라이브러리 정합."""

    def test_empty_file(self, tmp_path: Path) -> None:
        target = tmp_path / "empty.bin"
        target.touch()
        # 빈 파일 의 의 의 sha256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        expected = hashlib.sha256(b"").hexdigest()
        assert _sha256_of_file(target) == expected

    def test_small_file(self, tmp_path: Path) -> None:
        target = tmp_path / "small.bin"
        payload = b"hello tootalk"
        target.write_bytes(payload)
        assert _sha256_of_file(target) == hashlib.sha256(payload).hexdigest()

    def test_korean_content_byte_safe(self, tmp_path: Path) -> None:
        # 한글 UTF-8 의 의 의 의 의 의 sha256 정합
        target = tmp_path / "korean.txt"
        payload = "안녕하세요 TooTalk".encode("utf-8")
        target.write_bytes(payload)
        assert _sha256_of_file(target) == hashlib.sha256(payload).hexdigest()

    def test_binary_null_bytes(self, tmp_path: Path) -> None:
        target = tmp_path / "binary.bin"
        payload = b"\x00" * 4096 + b"\xff" * 4096
        target.write_bytes(payload)
        assert _sha256_of_file(target) == hashlib.sha256(payload).hexdigest()

    def test_multi_chunk_boundary(self, tmp_path: Path) -> None:
        # 64 KiB chunk_size 의 의 정확히 2 chunk 경계 의 의 의 의 정합
        target = tmp_path / "two_chunk.bin"
        payload = bytes(range(256)) * (64 * 1024 // 256) * 2
        # 정확히 128 KiB
        assert len(payload) == 128 * 1024
        target.write_bytes(payload)
        assert _sha256_of_file(target) == hashlib.sha256(payload).hexdigest()

    def test_partial_last_chunk(self, tmp_path: Path) -> None:
        # 청크 경계 미만 끝 — 64 KiB + 100 byte
        target = tmp_path / "partial.bin"
        payload = b"x" * (64 * 1024 + 100)
        target.write_bytes(payload)
        assert _sha256_of_file(target) == hashlib.sha256(payload).hexdigest()

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _sha256_of_file(tmp_path / "missing.bin")
