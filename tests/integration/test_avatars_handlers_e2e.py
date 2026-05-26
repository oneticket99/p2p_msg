# SPDX-License-Identifier: GPL-3.0-or-later
"""avatar handlers E2E — cycle 169.852 M2 (Exec Plan §4 REST 계약).

handler 직접 호출(folder e2e 패턴 준용) + multipart fake reader + 실 Pillow 이미지.
upload(가공/검증) / get(traversal 방어) / patch_me(영속) 전 분기. AVATAR_STORAGE_DIR
tmp override. pytestmark integration (default-run deselected, CI 포함).
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.avatars_handlers import (
    handle_get_avatar,
    handle_patch_me_avatar,
    handle_upload_avatar,
)

pytestmark = pytest.mark.integration


def _png_bytes(size=(600, 400)) -> bytes:
    """실 PNG byte 생성 (Pillow decode 통과용)."""

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, (10, 100, 200)).save(buf, "PNG")
    return buf.getvalue()


def _jpeg_bytes(size=(800, 500)) -> bytes:
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, (200, 50, 50)).save(buf, "JPEG")
    return buf.getvalue()


class _FakeField:
    """multipart BodyPartReader mock — 단일 chunk read."""

    def __init__(self, name: str, content_type: str, data: bytes) -> None:
        self.name = name
        self.headers = {"Content-Type": content_type}
        self._data = data
        self._done = False

    async def read_chunk(self, size: int = 8192) -> bytes:
        if self._done:
            return b""
        self._done = True
        return self._data


class _FakeReader:
    def __init__(self, field: Optional[_FakeField]) -> None:
        self._field = field
        self._done = False

    async def next(self):  # noqa: A003
        if self._done:
            return None
        self._done = True
        return self._field


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        user_id: Optional[int] = None,
        content_type: str = "application/json",
        field: Optional[_FakeField] = "__unset__",  # type: ignore[assignment]
        body: Optional[dict] = None,
        filename: str = "",
    ) -> None:
        self.app = app
        self.content_type = content_type
        self.match_info = {"filename": filename} if filename else {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self._field = field
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def multipart(self):
        # 한글 주석 — field "__unset__" sentinel = file field 부재 시나리오
        fld = None if self._field == "__unset__" else self._field
        return _FakeReader(fld)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


@pytest.fixture
def app(tmp_path, monkeypatch) -> web.Application:
    monkeypatch.setenv("AVATAR_STORAGE_DIR", str(tmp_path))
    application = web.Application()
    application["db_pool"] = None  # patch_me 의 일부 test 가 override
    return application


def _multipart_req(app, *, user_id=7, content_type="image/png", data=None, name="file"):
    field = _FakeField(name, content_type, data if data is not None else _png_bytes())
    return _FakeRequest(app, user_id=user_id, content_type="multipart/form-data", field=field)


# ----------------------------------------------------------------------
# POST /api/avatars
# ----------------------------------------------------------------------


async def test_upload_png_returns_201_avatar_ref(app) -> None:
    resp = await handle_upload_avatar(_multipart_req(app, data=_png_bytes()))
    assert resp.status == 201
    import json

    payload = json.loads(resp.body)
    assert payload["avatar_ref"].startswith("avatars/")
    assert payload["avatar_ref"].endswith(".png")
    assert payload["width"] == 512 and payload["height"] == 512


async def test_upload_jpeg_returns_201(app) -> None:
    req = _multipart_req(app, content_type="image/jpeg", data=_jpeg_bytes())
    resp = await handle_upload_avatar(req)
    assert resp.status == 201
    import json

    assert json.loads(resp.body)["avatar_ref"].endswith(".jpg")


async def test_upload_unauth_401(app) -> None:
    req = _multipart_req(app, user_id=None)
    assert (await handle_upload_avatar(req)).status == 401


async def test_upload_non_multipart_415(app) -> None:
    req = _FakeRequest(app, user_id=7, content_type="application/json")
    assert (await handle_upload_avatar(req)).status == 415


async def test_upload_no_file_field_400(app) -> None:
    req = _FakeRequest(app, user_id=7, content_type="multipart/form-data", field="__unset__")
    assert (await handle_upload_avatar(req)).status == 400


async def test_upload_bad_content_type_415(app) -> None:
    req = _multipart_req(app, content_type="image/gif", data=_png_bytes())
    assert (await handle_upload_avatar(req)).status == 415


async def test_upload_oversize_413(app) -> None:
    big = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 10)
    req = _multipart_req(app, content_type="image/png", data=big)
    assert (await handle_upload_avatar(req)).status == 413


async def test_upload_corrupt_bytes_400(app) -> None:
    # 한글 주석 — content-type 은 png 라 주장하나 실 byte 는 decode 불가
    req = _multipart_req(app, content_type="image/png", data=b"not a real image")
    assert (await handle_upload_avatar(req)).status == 400


# ----------------------------------------------------------------------
# GET /api/avatars/{filename}
# ----------------------------------------------------------------------


async def test_get_avatar_roundtrip_200(app) -> None:
    up = await handle_upload_avatar(_multipart_req(app, data=_png_bytes()))
    import json

    ref = json.loads(up.body)["avatar_ref"]  # avatars/<sha>.png
    filename = ref.split("/", 1)[1]
    req = _FakeRequest(app, user_id=7, filename=filename)
    resp = await handle_get_avatar(req)
    assert resp.status == 200
    assert resp.content_type == "image/png"


async def test_get_avatar_traversal_400(app) -> None:
    req = _FakeRequest(app, user_id=7, filename="..%2fetc")
    # match_info filename 은 raw — is_valid_ref 가 차단
    req.match_info = {"filename": "../etc/passwd"}
    assert (await handle_get_avatar(req)).status == 400


async def test_get_avatar_absent_404(app) -> None:
    req = _FakeRequest(app, user_id=7, filename=("a" * 64) + ".png")
    assert (await handle_get_avatar(req)).status == 404


async def test_get_avatar_unauth_401(app) -> None:
    req = _FakeRequest(app, user_id=None, filename=("a" * 64) + ".png")
    assert (await handle_get_avatar(req)).status == 401


# ----------------------------------------------------------------------
# PATCH /api/me/avatar
# ----------------------------------------------------------------------


def _build_pool() -> MagicMock:
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
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
    return pool


async def test_patch_me_valid_ref_200(app) -> None:
    up = await handle_upload_avatar(_multipart_req(app, data=_png_bytes()))
    import json

    ref = json.loads(up.body)["avatar_ref"]
    app["db_pool"] = _build_pool()
    req = _FakeRequest(app, user_id=7, body={"avatar_ref": ref})
    resp = await handle_patch_me_avatar(req)
    assert resp.status == 200
    assert json.loads(resp.body)["avatar_ref"] == ref


async def test_patch_me_empty_removes_200(app) -> None:
    app["db_pool"] = _build_pool()
    req = _FakeRequest(app, user_id=7, body={"avatar_ref": ""})
    resp = await handle_patch_me_avatar(req)
    assert resp.status == 200
    import json

    assert json.loads(resp.body)["avatar_ref"] == ""


async def test_patch_me_nonexistent_ref_400(app) -> None:
    app["db_pool"] = _build_pool()
    req = _FakeRequest(
        app, user_id=7, body={"avatar_ref": "avatars/" + ("f" * 64) + ".png"}
    )
    assert (await handle_patch_me_avatar(req)).status == 400


async def test_patch_me_unauth_401(app) -> None:
    req = _FakeRequest(app, user_id=None, body={"avatar_ref": ""})
    assert (await handle_patch_me_avatar(req)).status == 401


async def test_patch_me_db_disabled_503(app) -> None:
    app["db_pool"] = None
    req = _FakeRequest(app, user_id=7, body={"avatar_ref": ""})
    assert (await handle_patch_me_avatar(req)).status == 503
