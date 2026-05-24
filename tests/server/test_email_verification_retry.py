# SPDX-License-Identifier: GPL-3.0-or-later
"""email_verification _retry_on_record_changed unit — cycle 169.764 신설.

MariaDB error 1020 (Record has changed) retry helper 의 3 path 회수:
- 1020 → retry 후 성공
- non-1020 OperationalError → 즉시 raise
- 모든 retry fail → 마지막 exception re-raise
"""

from __future__ import annotations

import pytest

from asyncmy.errors import OperationalError


@pytest.fixture(autouse=True)
def _fast_sleep(monkeypatch):
    # 한글 주석 — exponential backoff sleep 제거 (test 가속)
    import server.db.repositories.email_verification as ev

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(ev.asyncio, "sleep", _no_sleep)


class TestRetryOnRecordChanged:
    @pytest.mark.asyncio
    async def test_1020_retry_then_success(self) -> None:
        from server.db.repositories.email_verification import _retry_on_record_changed

        state = {"n": 0}

        async def _op():
            state["n"] += 1
            if state["n"] < 2:
                raise OperationalError(1020, "Record has changed")
            return "ok"

        result = await _retry_on_record_changed("test_op", _op)
        assert result == "ok"
        assert state["n"] == 2  # 한글 주석 — 1회 retry 후 성공

    @pytest.mark.asyncio
    async def test_non_1020_raises_immediately(self) -> None:
        from server.db.repositories.email_verification import _retry_on_record_changed

        calls = {"n": 0}

        async def _op():
            calls["n"] += 1
            raise OperationalError(1213, "Deadlock")  # 한글 주석 — 1020 아님

        with pytest.raises(OperationalError):
            await _retry_on_record_changed("test_op", _op)
        assert calls["n"] == 1  # retry 부재 (즉시 raise)

    @pytest.mark.asyncio
    async def test_all_retries_fail_reraises(self) -> None:
        from server.db.repositories.email_verification import _retry_on_record_changed

        calls = {"n": 0}

        async def _op():
            calls["n"] += 1
            raise OperationalError(1020, "always changed")

        with pytest.raises(OperationalError):
            await _retry_on_record_changed("test_op", _op, max_attempts=3)
        assert calls["n"] == 3  # 한글 주석 — max_attempts 만큼 시도 후 re-raise
