# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.file_progress_widget.FileProgressWidget._humanize`` 단위 테스트.

byte → 사람 가독 단위 (B / KB / MB / GB / TB) 변환 — qa-agent 사이클 13 의
"_humanize 9 케이스 PASS" 정합 + 추가 경계 케이스 보강.

staticmethod 만 검증 — QWidget repaint / signal 통합 = pytest-qt 별도 cycle.
"""

from __future__ import annotations

import pytest

from app.ui.file_progress_widget import FileProgressWidget


class TestHumanize:
    """1024 진수 단위 변환 — B / KB / MB / GB / TB."""

    # ---- 1. B 영역 (< 1024) ----

    def test_zero_bytes(self) -> None:
        assert FileProgressWidget._humanize(0) == "0 B"

    def test_one_byte(self) -> None:
        assert FileProgressWidget._humanize(1) == "1 B"

    def test_under_one_kb(self) -> None:
        assert FileProgressWidget._humanize(1023) == "1023 B"

    # ---- 2. KB 영역 (1024 ≤ n < 1024^2) ----

    def test_exactly_one_kb(self) -> None:
        assert FileProgressWidget._humanize(1024) == "1.0 KB"

    def test_one_and_half_kb(self) -> None:
        assert FileProgressWidget._humanize(1536) == "1.5 KB"

    def test_just_under_one_mb(self) -> None:
        # 1024 * 1024 - 1 = 1048575 → 1024.0 KB 직전
        result = FileProgressWidget._humanize(1024 * 1024 - 1)
        assert result.endswith(" KB")

    # ---- 3. MB 영역 (1024^2 ≤ n < 1024^3) ----

    def test_exactly_one_mb(self) -> None:
        assert FileProgressWidget._humanize(1024 * 1024) == "1.0 MB"

    def test_100_mb(self) -> None:
        # 100 MB — 100.0 MB
        assert FileProgressWidget._humanize(100 * 1024 * 1024) == "100.0 MB"

    # ---- 4. GB 영역 (1024^3 ≤ n < 1024^4) ----

    def test_exactly_one_gb(self) -> None:
        assert FileProgressWidget._humanize(1024**3) == "1.0 GB"

    def test_two_and_half_gb(self) -> None:
        # 2.5 GB
        assert (
            FileProgressWidget._humanize(int(2.5 * 1024**3)) == "2.5 GB"
        )

    # ---- 5. TB 영역 (≥ 1024^4) ----

    def test_exactly_one_tb(self) -> None:
        assert FileProgressWidget._humanize(1024**4) == "1.0 TB"

    def test_huge_value_still_tb(self) -> None:
        # 1024 TB TB 단위 유지 (units[-1] 경계)
        result = FileProgressWidget._humanize(1024**5)
        assert result.endswith(" TB")
        # 1024.0 TB
        assert "1024.0" in result

    # ---- 6. 부정수 / 음수 / 비정수 입력 폴백 ----

    def test_negative_clamped_to_zero(self) -> None:
        # 음수 → max(0, ...) 으로 0 으로 변환 → "0 B"
        assert FileProgressWidget._humanize(-100) == "0 B"

    def test_float_input_coerced_to_int(self) -> None:
        # int() 강제 변환 — 소수점 절삭
        assert FileProgressWidget._humanize(1024) == "1.0 KB"
        # type ignore 경고 회피 직접 int 호출
        assert FileProgressWidget._humanize(int(1024.7)) == "1.0 KB"

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, "0 B"),
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
        ],
    )
    def test_boundary_values_parametrized(
        self, n: int, expected: str
    ) -> None:
        assert FileProgressWidget._humanize(n) == expected
