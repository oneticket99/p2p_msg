# SPDX-License-Identifier: GPL-3.0-or-later
"""RoomsClient unit test — cycle 169.665 omit 제거 path."""

from __future__ import annotations

import pytest


class TestRoomsClientInit:
    def test_trims_trailing_slash(self) -> None:
        from app.net.rooms_client import RoomsClient

        c = RoomsClient("https://api.local/", token="t")
        assert c._base_url == "https://api.local"
        assert c._token == "t"
        assert c._owns_client is True

    def test_empty_base_url_raises(self) -> None:
        from app.net.rooms_client import RoomsClient

        with pytest.raises(ValueError, match="base_url"):
            RoomsClient("", token="t")

    def test_empty_token_raises(self) -> None:
        from app.net.rooms_client import RoomsClient

        with pytest.raises(ValueError, match="token"):
            RoomsClient("https://api.local", token="")


class TestRoomsErrorHierarchy:
    def test_all_subclass_base(self) -> None:
        from app.net.rooms_client import (
            RoomsAuthError, RoomsBadRequestError, RoomsClientError,
            RoomsConflictError, RoomsForbiddenError, RoomsNetworkError,
            RoomsNotFoundError, RoomsServerError,
        )

        for cls in (
            RoomsAuthError, RoomsBadRequestError, RoomsForbiddenError,
            RoomsNotFoundError, RoomsConflictError, RoomsServerError,
            RoomsNetworkError,
        ):
            assert issubclass(cls, RoomsClientError)


class TestRoomPayload:
    def test_room_payload_fields(self) -> None:
        from app.net.rooms_client import RoomPayload

        # 한글 주석 — RoomPayload dataclass attribute 존재 verify
        assert hasattr(RoomPayload, "__dataclass_fields__")

    def test_room_member_payload_fields(self) -> None:
        from app.net.rooms_client import RoomMemberPayload

        assert hasattr(RoomMemberPayload, "__dataclass_fields__")

class TestCreateRoomBody:
    """create_room body 구성 — cycle 169.852 avatar_ref/description (M4)."""

    @pytest.mark.asyncio
    async def test_avatar_ref_and_description_included(self) -> None:
        from unittest.mock import AsyncMock

        from app.net.rooms_client import RoomsClient

        c = RoomsClient("https://api.local", token="t")
        c._request = AsyncMock(
            return_value={"id": 1, "room_code": "x", "owner_id": 1, "kind": "group"}
        )
        await c.create_room(
            name="내 그룹", kind="group",
            avatar_ref="avatars/aa.png", description="설명",
        )
        body = c._request.await_args.kwargs["json"]
        assert body == {
            "kind": "group", "name": "내 그룹",
            "avatar_ref": "avatars/aa.png", "description": "설명",
        }

    @pytest.mark.asyncio
    async def test_empty_optionals_omitted(self) -> None:
        # 한글 주석 — 빈 name/avatar_ref/description 은 body 에서 생략(backward compat)
        from unittest.mock import AsyncMock

        from app.net.rooms_client import RoomsClient

        c = RoomsClient("https://api.local", token="t")
        c._request = AsyncMock(
            return_value={"id": 1, "room_code": "x", "owner_id": 1, "kind": "group"}
        )
        await c.create_room(kind="group")
        assert c._request.await_args.kwargs["json"] == {"kind": "group"}
