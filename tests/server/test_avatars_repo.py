# SPDX-License-Identifier: GPL-3.0-or-later
"""avatar 영속 repository + users.avatar_ref 단위 test — cycle 169.852 M1 (0018 정합).

avatars.py = 디스크 sync I/O (tmp dir + AVATAR_STORAGE_DIR override) — store/load
/exists/key 검증/dedup/traversal 방어. users.py = async pool mock 으로
update_avatar_ref/get_avatar_ref round-trip. pyproject asyncio_mode=auto 정합.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.db.repositories import avatars


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """AVATAR_STORAGE_DIR 을 tmp dir 로 override — 실 server volume 격리."""

    monkeypatch.setenv("AVATAR_STORAGE_DIR", str(tmp_path))
    return tmp_path


# ----------------------------------------------------------------------
# avatars.py — 디스크 저장 repository
# ----------------------------------------------------------------------


def test_store_avatar_key_format_and_write(storage) -> None:
    """store_avatar → avatars/<sha256>.<ext> 키 + 디스크 write."""

    data = b"\x89PNG fake image bytes"
    key = avatars.store_avatar(data, "png")
    digest = hashlib.sha256(data).hexdigest()
    assert key == f"avatars/{digest}.png"
    assert (storage / f"{digest}.png").read_bytes() == data


def test_store_avatar_dedup_skips_rewrite(storage) -> None:
    """동일 byte 재저장 → 동일 키 + write skip(dedup)."""

    data = b"same-bytes"
    key1 = avatars.store_avatar(data, "jpg")
    digest = hashlib.sha256(data).hexdigest()
    dest = storage / f"{digest}.jpg"
    mtime1 = dest.stat().st_mtime_ns
    key2 = avatars.store_avatar(data, "jpg")  # dedup — 재기록 없음
    assert key1 == key2
    assert dest.stat().st_mtime_ns == mtime1  # write skip → mtime 불변


def test_store_avatar_invalid_ext_raises(storage) -> None:
    """허용 외 확장자 → ValueError."""

    with pytest.raises(ValueError, match="허용 외 확장자"):
        avatars.store_avatar(b"x", "gif")


def test_load_avatar_roundtrip(storage) -> None:
    """저장 후 load → 동일 byte."""

    data = b"roundtrip-bytes"
    key = avatars.store_avatar(data, "png")
    assert avatars.load_avatar(key) == data


def test_load_avatar_absent_returns_none(storage) -> None:
    """실재 안 하는 정상 형식 키 → None."""

    fake = "avatars/" + ("a" * 64) + ".png"
    assert avatars.load_avatar(fake) is None


@pytest.mark.parametrize(
    "bad_ref",
    [
        "avatars/../etc/passwd",
        "../../etc/passwd",
        "/etc/passwd",
        "avatars/short.png",
        "avatars/" + ("a" * 64) + ".gif",
        "avatars/" + ("Z" * 64) + ".png",  # 대문자 hex 불가
        "evil/" + ("a" * 64) + ".png",
        "avatars/" + ("a" * 64) + ".png\n",  # trailing newline ($ 허점 — \Z anchor 차단)
    ],
)
def test_load_avatar_traversal_and_format_rejected(storage, bad_ref) -> None:
    """path traversal + 키 형식 위반 → None (디스크 접근 차단)."""

    assert avatars.is_valid_ref(bad_ref) is False
    assert avatars.load_avatar(bad_ref) is None


def test_avatar_exists(storage) -> None:
    """avatar_exists — 실재 True / 부재·형식위반 False."""

    data = b"exists-test"
    key = avatars.store_avatar(data, "jpeg")
    assert avatars.avatar_exists(key) is True
    assert avatars.avatar_exists("avatars/" + ("b" * 64) + ".png") is False
    assert avatars.avatar_exists("../bad") is False


def test_content_type_for_ref() -> None:
    """확장자 → Content-Type 매핑."""

    assert avatars.content_type_for_ref("avatars/x.png") == "image/png"
    assert avatars.content_type_for_ref("avatars/x.jpg") == "image/jpeg"
    assert avatars.content_type_for_ref("avatars/x.jpeg") == "image/jpeg"


# ----------------------------------------------------------------------
# users.py — avatar_ref UPDATE / SELECT
# ----------------------------------------------------------------------


def _build_pool(*, fetchone=None, rowcount=1) -> MagicMock:
    """async DB pool mock (기존 repo test 패턴 준용)."""

    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.rowcount = rowcount
    cur_ctx = MagicMock()
    cur_ctx.__aenter__ = AsyncMock(return_value=cur)
    cur_ctx.__aexit__ = AsyncMock(return_value=None)
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cur_ctx)
    conn.commit = AsyncMock(return_value=None)
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=conn_ctx)
    pool._cur = cur  # test assertion 접근용
    return pool


async def test_update_avatar_ref_executes_update() -> None:
    """update_avatar_ref → UPDATE users SET avatar_ref 실행 + commit."""

    from server.db.repositories.users import update_avatar_ref

    pool = _build_pool()
    await update_avatar_ref(pool, 42, "avatars/" + ("c" * 64) + ".png")
    args = pool._cur.execute.await_args
    assert "UPDATE users SET avatar_ref" in args.args[0]
    assert args.args[1] == ("avatars/" + ("c" * 64) + ".png", 42)


async def test_get_avatar_ref_returns_value() -> None:
    """get_avatar_ref → 조회값 반환."""

    from server.db.repositories.users import get_avatar_ref

    ref = "avatars/" + ("d" * 64) + ".jpg"
    pool = _build_pool(fetchone=(ref,))
    assert await get_avatar_ref(pool, 7) == ref


async def test_get_avatar_ref_absent_row_returns_none() -> None:
    """row 부재 → None."""

    from server.db.repositories.users import get_avatar_ref

    pool = _build_pool(fetchone=None)
    assert await get_avatar_ref(pool, 999) is None
