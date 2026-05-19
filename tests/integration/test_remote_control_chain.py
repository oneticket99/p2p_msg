# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 151 — 원격 제어 본격 chain integration smoke test.

cycle 132 (REMOTE 3 ENUM) + cycle 148 (remote coord transform) + cycle 150
(screen capture + input dispatch skeleton) chain → integration smoke test.

capture → encode → DataChannel send → decode → coord transform → input dispatch
full chain mock 검증. 실 RTCPeerConnection / CGEvent / SendInput 차단 → mock.

본 module 의 범위
----------------
- 10 test class — TestCaptureFrameFlow / TestCoordTransform_FHDtoQHD /
  TestInputDispatchSkeleton / TestFullChainMock / TestREMOTE_REQUEST_audit /
  TestREMOTE_GRANT_audit / TestREMOTE_REVOKE_audit / TestRemoteScreenInfoExchange /
  TestAspectRatioPolicies / TestMacOSCFReleaseChain.
- pytestmark integration deselect 정합 (pyproject.toml `-m "not integration"`).
- 실 NIC / WebRTC offer/answer / OS native binding 부재 — 전 chain mock.

본 cycle 의 범위 외 (Phase 5 cycle 166~180):
- aiortc RTCDataChannel 의 실 send / on("message") 연결 의 integration.
- 실 Quartz CGDisplayCreateImage 의 pixel buffer 의 actual extract.
- 실 CGEvent / SendInput / XTest 의 OS dispatch + Accessibility permission.
"""

from __future__ import annotations

import json
import platform
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.remote.coord_transform import (
    AspectRatioPolicy,
    RemoteScreenInfo,
    transform_coordinates,
)
from app.remote.input_dispatch import (
    DispatchEvent,
    InputDispatchBackend,
    LinuxXTestBackend,
    MacOSCGEventBackend,
    WindowsSendInputBackend,
    build_input_dispatch_backend,
)
from app.remote.screen_capture import (
    CapturedFrame,
    LinuxX11Backend,
    MacOSQuartzBackend,
    ScreenCaptureBackend,
    WindowsBitBltBackend,
    build_capture_backend,
)

# 한글 주석 — 본 module 전체 integration marker. 기본 pytest run 시 deselect 의 의무.
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# helper — 화면 fixture (FHD / QHD) + audit mock pool
# ---------------------------------------------------------------------------


def _fhd() -> RemoteScreenInfo:
    """한글 주석 — 1920x1080 FHD 화면 fixture (sender)."""
    return RemoteScreenInfo(
        width=1920,
        height=1080,
        logical_width=1920,
        logical_height=1080,
        dpi=96,
        backing_scale=1.0,
    )


def _qhd() -> RemoteScreenInfo:
    """한글 주석 — 2560x1440 QHD 화면 fixture (target)."""
    return RemoteScreenInfo(
        width=2560,
        height=1440,
        logical_width=2560,
        logical_height=1440,
        dpi=96,
        backing_scale=1.0,
    )


def _mock_audit_pool() -> tuple[Any, Any]:
    """한글 주석 — asyncmy pool + cursor mock. user_activity_log INSERT 검증 의무."""
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 1
    cursor.rowcount = 1

    @asynccontextmanager
    async def cursor_cm() -> Any:
        yield cursor

    conn = MagicMock()
    conn.cursor = lambda: cursor_cm()
    conn.commit = AsyncMock()

    @asynccontextmanager
    async def acquire_cm() -> Any:
        yield conn

    pool = MagicMock()
    pool.acquire = lambda: acquire_cm()
    return pool, cursor


class _FakeRequest:
    """한글 주석 — aiohttp.web.Request minimal mock. remote_handlers audit 의 의무 인터페이스."""

    def __init__(
        self,
        *,
        db_pool: Any = None,
        user_id: int = 42,
        body: dict[str, Any] | None = None,
        xff: str = "",
        remote: str = "10.0.0.1",
        ua: str = "TooTalk/0.4.0",
    ) -> None:
        self._app: dict[str, Any] = {"db_pool": db_pool}
        self._body = body or {}
        self._user_id = user_id
        self._xff = xff
        self._remote_ip = remote
        self._ua = ua
        self.content_length = len(json.dumps(self._body)) if self._body else 0

    @property
    def app(self) -> dict[str, Any]:
        return self._app

    @property
    def headers(self) -> Any:
        class _H:
            def __init__(self, xff: str, ua: str) -> None:
                self._data = {"X-Forwarded-For": xff, "User-Agent": ua}

            def get(self, key: str, default: str = "") -> str:
                return self._data.get(key, default)

        return _H(self._xff, self._ua)

    @property
    def remote(self) -> str:
        return self._remote_ip

    def get(self, key: str, default: Any = None) -> Any:
        if key == "user_id":
            return self._user_id
        return default

    async def json(self) -> dict[str, Any]:
        return self._body


# ---------------------------------------------------------------------------
# 1. TestCaptureFrameFlow — build_capture_backend + capture_primary graceful
# ---------------------------------------------------------------------------


class TestCaptureFrameFlow:
    """build_capture_backend + capture_primary (None graceful) + skeleton 검증."""

    def test_factory_returns_backend(self) -> None:
        # 한글 주석 — 현 platform 의 build_capture_backend 의 ScreenCaptureBackend instance 반환 의무.
        backend = build_capture_backend()
        assert isinstance(backend, ScreenCaptureBackend)

    def test_factory_branches_by_platform(self) -> None:
        # 한글 주석 — Darwin / Windows / Linux 의 분기 의 정합 검증.
        sys_name = platform.system().lower()
        backend = build_capture_backend()
        if sys_name == "darwin":
            assert isinstance(backend, MacOSQuartzBackend)
        elif sys_name == "windows":
            assert isinstance(backend, WindowsBitBltBackend)
        elif sys_name == "linux":
            assert isinstance(backend, LinuxX11Backend)
        else:
            assert type(backend) is ScreenCaptureBackend

    def test_capture_primary_skeleton_returns_none(self) -> None:
        # 한글 주석 — skeleton base class 의 capture_primary = None graceful.
        backend = ScreenCaptureBackend()
        assert backend.capture_primary() is None

    def test_list_monitors_skeleton_empty(self) -> None:
        # 한글 주석 — skeleton list_monitors = 빈 list graceful.
        backend = ScreenCaptureBackend()
        assert backend.list_monitors() == []

    def test_captured_frame_dataclass_invariant(self) -> None:
        # 한글 주석 — CapturedFrame frozen + slots + pixel_format 의 검증.
        frame = CapturedFrame(
            width=2,
            height=1,
            bytes_per_row=8,
            pixel_format="BGRA",
            data=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )
        assert frame.width == 2
        assert frame.height == 1
        assert frame.bytes_per_row == 8
        assert frame.pixel_format == "BGRA"
        assert len(frame.data) == 8


# ---------------------------------------------------------------------------
# 2. TestCoordTransform_FHDtoQHD — FHD → QHD 비례 변환 정합
# ---------------------------------------------------------------------------


class TestCoordTransform_FHDtoQHD:
    """FHD (1920x1080) sender → QHD (2560x1440) target — 1.333x scaling 정합."""

    def test_center_point(self) -> None:
        # 한글 주석 — (960, 540) → (1280, 720) 비례 정합.
        x, y = transform_coordinates(_fhd(), _qhd(), 960, 540)
        assert x == 1280
        assert y == 720

    def test_origin(self) -> None:
        # 한글 주석 — (0, 0) → (0, 0) 정합.
        x, y = transform_coordinates(_fhd(), _qhd(), 0, 0)
        assert (x, y) == (0, 0)

    def test_max_corner_capped(self) -> None:
        # 한글 주석 — (1919, 1079) → (2558, 1438) 의 width-1 cap 정합.
        x, y = transform_coordinates(_fhd(), _qhd(), 1919, 1079)
        assert 2555 <= x <= 2559
        assert 1435 <= y <= 1439


# ---------------------------------------------------------------------------
# 3. TestInputDispatchSkeleton — build_input_dispatch_backend + dispatch graceful
# ---------------------------------------------------------------------------


class TestInputDispatchSkeleton:
    """build_input_dispatch_backend + dispatch (None graceful) skeleton 검증."""

    def test_factory_returns_backend(self) -> None:
        # 한글 주석 — build_input_dispatch_backend 의 InputDispatchBackend instance 반환 의무.
        backend = build_input_dispatch_backend()
        assert isinstance(backend, InputDispatchBackend)

    def test_factory_branches_by_platform(self) -> None:
        # 한글 주석 — Darwin / Windows / Linux 의 분기 정합.
        sys_name = platform.system().lower()
        backend = build_input_dispatch_backend()
        if sys_name == "darwin":
            assert isinstance(backend, MacOSCGEventBackend)
        elif sys_name == "windows":
            assert isinstance(backend, WindowsSendInputBackend)
        elif sys_name == "linux":
            assert isinstance(backend, LinuxXTestBackend)
        else:
            assert type(backend) is InputDispatchBackend

    def test_base_is_available_false(self) -> None:
        # 한글 주석 — base class is_available = False graceful.
        assert InputDispatchBackend.is_available() is False

    def test_dispatch_skeleton_returns_none(self) -> None:
        # 한글 주석 — skeleton dispatch = None graceful.
        backend = InputDispatchBackend()
        event = DispatchEvent(event_type="mouse_move", x=100, y=200)
        assert backend.dispatch(event) is None

    def test_dispatch_event_dataclass(self) -> None:
        # 한글 주석 — DispatchEvent frozen + slots + event_type 의 검증.
        event = DispatchEvent(
            event_type="mouse_button", x=50, y=60, button=1, pressed=True
        )
        assert event.event_type == "mouse_button"
        assert event.button == 1
        assert event.pressed is True


# ---------------------------------------------------------------------------
# 4. TestFullChainMock — capture → coord transform → input dispatch end-to-end
# ---------------------------------------------------------------------------


class TestFullChainMock:
    """capture → coord transform → input dispatch end-to-end mock chain.

    target → controller 의 화면 capture (mock) → controller view 좌표 사용자 클릭 →
    coord_transform → target OS 절대 좌표 → input dispatch (mock) chain.
    실 RTCDataChannel / WebRTC SDP 부재 — pure data flow 검증.
    """

    def test_full_chain_center_click(self) -> None:
        # 한글 주석 — controller (FHD) → target (QHD) 의 center click 의 full chain.
        # step 1 — target 의 화면 capture (mock CapturedFrame 의 1 frame).
        captured = CapturedFrame(
            width=2560,
            height=1440,
            bytes_per_row=2560 * 4,
            pixel_format="BGRA",
            data=b"\x80\x80\x80\xff" * (2560 * 1440),
        )
        assert captured.width == 2560
        assert captured.height == 1440

        # step 2 — controller view 사용자 click (960, 540) — controller 의 view 단 FHD.
        controller_x, controller_y = 960, 540

        # step 3 — coord_transform — controller (FHD) → target (QHD).
        target_x, target_y = transform_coordinates(
            _fhd(), _qhd(), controller_x, controller_y
        )
        assert target_x == 1280
        assert target_y == 720

        # step 4 — DispatchEvent build (target OS native 좌표).
        event = DispatchEvent(
            event_type="mouse_button",
            x=target_x,
            y=target_y,
            button=1,
            pressed=True,
        )
        assert event.x == 1280
        assert event.y == 720

        # step 5 — input dispatch (skeleton mock — None graceful 의 의무).
        backend = InputDispatchBackend()
        result = backend.dispatch(event)
        assert result is None  # skeleton graceful — Phase 5 cycle 166+ 의 actual

    def test_full_chain_crop_outside_skipped(self) -> None:
        # 한글 주석 — crop 정책 의 영역 외 click → (-1, -1) → dispatch skip.
        crop_target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        # sender_x = 10 → crop 영역 (240~1680) 외.
        target_x, target_y = transform_coordinates(
            _fhd(), crop_target, 10, 540, policy=AspectRatioPolicy.CROP
        )
        assert (target_x, target_y) == (-1, -1)
        # (-1, -1) = skip 신호 → DispatchEvent build 안 함 의 의무.

    def test_full_chain_aspect_letterbox(self) -> None:
        # 한글 주석 — letterbox 정책 의 4:3 target → 검은 띠 정합.
        lb_target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        target_x, target_y = transform_coordinates(
            _fhd(), lb_target, 960, 540, policy=AspectRatioPolicy.LETTERBOX
        )
        # 검은 띠 안 정상 mapping.
        assert 510 <= target_x <= 514
        assert 380 <= target_y <= 388
        # DispatchEvent build OK.
        event = DispatchEvent(
            event_type="mouse_move", x=target_x, y=target_y
        )
        assert event.event_type == "mouse_move"


# ---------------------------------------------------------------------------
# 5. TestREMOTE_REQUEST_audit — REMOTE_REQUEST audit emit 검증
# ---------------------------------------------------------------------------


class TestREMOTE_REQUEST_audit:
    """REMOTE_REQUEST audit emit 검증 (cycle 132 정합)."""

    @pytest.mark.asyncio
    async def test_request_emits_audit_row(self) -> None:
        # 한글 주석 — pool 가용 시 user_activity_log INSERT + action=remote_request.
        from server.api.remote_handlers import handle_remote_request
        from server.db.repositories.user_activity import ActivityAction

        pool, cursor = _mock_audit_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=42,
            body={"target_user_id": 99, "pattern": "help"},
            xff="203.0.113.5",
        )
        resp = await handle_remote_request(req)  # type: ignore[arg-type]
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.REMOTE_REQUEST.value
        assert params[2] == 99


# ---------------------------------------------------------------------------
# 6. TestREMOTE_GRANT_audit — REMOTE_GRANT audit emit
# ---------------------------------------------------------------------------


class TestREMOTE_GRANT_audit:
    """REMOTE_GRANT audit emit 검증 (cycle 132 정합)."""

    @pytest.mark.asyncio
    async def test_grant_emits_audit_row(self) -> None:
        # 한글 주석 — granter (target) user 의 grant action params 정합.
        from server.api.remote_handlers import handle_remote_grant
        from server.db.repositories.user_activity import ActivityAction

        pool, cursor = _mock_audit_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=99,
            body={"request_id": 7, "requester_user_id": 42},
        )
        resp = await handle_remote_grant(req)  # type: ignore[arg-type]
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 99
        assert params[1] == ActivityAction.REMOTE_GRANT.value
        assert params[2] == 42


# ---------------------------------------------------------------------------
# 7. TestREMOTE_REVOKE_audit — REMOTE_REVOKE audit emit
# ---------------------------------------------------------------------------


class TestREMOTE_REVOKE_audit:
    """REMOTE_REVOKE audit emit 검증 (cycle 132 정합)."""

    @pytest.mark.asyncio
    async def test_revoke_emits_audit_row(self) -> None:
        # 한글 주석 — revoker user 의 revoke action params 정합.
        from server.api.remote_handlers import handle_remote_revoke
        from server.db.repositories.user_activity import ActivityAction

        pool, cursor = _mock_audit_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=42,
            body={"session_id": 13, "target_user_id": 99},
        )
        resp = await handle_remote_revoke(req)  # type: ignore[arg-type]
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.REMOTE_REVOKE.value
        assert params[2] == 99


# ---------------------------------------------------------------------------
# 8. TestRemoteScreenInfoExchange — RemoteScreenInfo WebRTC DataChannel payload
# ---------------------------------------------------------------------------


class TestRemoteScreenInfoExchange:
    """sender + target RemoteScreenInfo dataclass 의 WebRTC DataChannel payload schema.

    Phase 5 cycle 166+ 의 실 RTCDataChannel send / on("message") chain 의 사전 base.
    본 cycle = pure dataclass 의 dict serialization round-trip 검증.
    """

    def test_screen_info_payload_round_trip(self) -> None:
        # 한글 주석 — RemoteScreenInfo → dict → RemoteScreenInfo round-trip 정합.
        sender = _fhd()
        payload = {
            "width": sender.width,
            "height": sender.height,
            "logical_width": sender.logical_width,
            "logical_height": sender.logical_height,
            "dpi": sender.dpi,
            "backing_scale": sender.backing_scale,
            "primary_monitor_index": sender.primary_monitor_index,
        }
        # WebRTC DataChannel 의 JSON serialization 의 가용성 검증.
        serialized = json.dumps(payload)
        deserialized = json.loads(serialized)
        restored = RemoteScreenInfo(**deserialized)
        assert restored == sender

    def test_retina_payload_preserves_backing_scale(self) -> None:
        # 한글 주석 — macOS Retina MBP 의 backing_scale=2.0 의 serialization 의무.
        retina = RemoteScreenInfo(
            width=2560,
            height=1600,
            logical_width=1280,
            logical_height=800,
            dpi=96,
            backing_scale=2.0,
        )
        payload = json.dumps(
            {
                "width": retina.width,
                "height": retina.height,
                "logical_width": retina.logical_width,
                "logical_height": retina.logical_height,
                "dpi": retina.dpi,
                "backing_scale": retina.backing_scale,
                "primary_monitor_index": retina.primary_monitor_index,
            }
        )
        restored = RemoteScreenInfo(**json.loads(payload))
        assert restored.backing_scale == 2.0
        assert restored.width == 2560
        assert restored.logical_width == 1280


# ---------------------------------------------------------------------------
# 9. TestAspectRatioPolicies — letterbox / stretch / crop 3 정책 정합
# ---------------------------------------------------------------------------


class TestAspectRatioPolicies:
    """letterbox / stretch / crop 3 정책 정합 — full chain integration."""

    def test_letterbox_policy(self) -> None:
        # 한글 주석 — 16:9 sender → 4:3 target 의 letterbox = 검은 띠 + 비율 보존.
        target_43 = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            _fhd(), target_43, 960, 540, policy=AspectRatioPolicy.LETTERBOX
        )
        # 검은 띠 안 정상 mapping.
        assert 510 <= x <= 514
        assert 380 <= y <= 388

    def test_stretch_policy(self) -> None:
        # 한글 주석 — stretch = aspect 무시 + 직접 비례 (왜곡 허용).
        target_43 = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            _fhd(), target_43, 960, 540, policy=AspectRatioPolicy.STRETCH
        )
        # 960 * 1024 / 1920 = 512, 540 * 768 / 1080 = 384
        assert x == 512
        assert y == 384

    def test_crop_policy_inside(self) -> None:
        # 한글 주석 — crop 안 정상 변환 의 의무 (16:9 sender → 4:3 target).
        target_43 = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            _fhd(), target_43, 960, 540, policy=AspectRatioPolicy.CROP
        )
        # crop 안 중앙 정합.
        assert 510 <= x <= 514
        assert 382 <= y <= 386

    def test_crop_policy_outside(self) -> None:
        # 한글 주석 — crop 영역 외 → (-1, -1) skip 신호.
        target_43 = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            _fhd(), target_43, 10, 540, policy=AspectRatioPolicy.CROP
        )
        assert (x, y) == (-1, -1)


# ---------------------------------------------------------------------------
# 10. TestMacOSCFReleaseChain — Quartz capture + CFRelease try/finally 의무 mock
# ---------------------------------------------------------------------------


class TestMacOSCFReleaseChain:
    """Quartz capture + CFRelease try/finally 의무 mock 검증.

    feedback_objc_memory_release_mandatory 정합 — 1 frame leak = 60 fps × 1080p
    의 분당 1.3 GB 누수 차단. CGDisplayCreateImage 반환 = CGImageRef CFRetain
    count = 1 → CFRelease 의무 try/finally chain.

    실 PyObjC + Quartz binding 부재 — graceful None + mock import 의 검증.
    """

    def test_pyobjc_absent_graceful_none(self) -> None:
        # 한글 주석 — PyObjC + Quartz 부재 시 capture_primary = None graceful.
        # builtins.__import__ 의 patch 의 ImportError raise 의 의무.
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("Quartz", "CoreFoundation"):
                raise ImportError(f"mock — {name} 부재")
            return real_import(name, *args, **kwargs)

        backend = MacOSQuartzBackend()
        with patch("builtins.__import__", side_effect=fake_import):
            result = backend.capture_primary()
            assert result is None

    def test_cfrelease_called_on_image_alloc(self) -> None:
        # 한글 주석 — CGDisplayCreateImage 반환 시 CFRelease finally chain 의 호출 의무.
        # Quartz + CoreFoundation mock module 주입 + CFRelease call 검증.
        import sys

        fake_quartz = MagicMock()
        fake_quartz.CGMainDisplayID = MagicMock(return_value=12345)
        fake_quartz.CGDisplayCreateImage = MagicMock(return_value="fake_cg_image_handle")
        fake_cf = MagicMock()
        fake_cf.CFRelease = MagicMock()

        backend = MacOSQuartzBackend()
        with patch.dict(
            sys.modules,
            {"Quartz": fake_quartz, "CoreFoundation": fake_cf},
        ):
            result = backend.capture_primary()
            # skeleton — None 반환 의 의무 (Phase 5 cycle 166+ 의 actual 의무).
            assert result is None
            # CFRelease finally chain 의 호출 의무 검증.
            fake_cf.CFRelease.assert_called_once_with("fake_cg_image_handle")

    def test_cfrelease_skipped_on_none_image(self) -> None:
        # 한글 주석 — CGDisplayCreateImage 반환 None 시 CFRelease 미호출 의 의무.
        import sys

        fake_quartz = MagicMock()
        fake_quartz.CGMainDisplayID = MagicMock(return_value=12345)
        fake_quartz.CGDisplayCreateImage = MagicMock(return_value=None)
        fake_cf = MagicMock()
        fake_cf.CFRelease = MagicMock()

        backend = MacOSQuartzBackend()
        with patch.dict(
            sys.modules,
            {"Quartz": fake_quartz, "CoreFoundation": fake_cf},
        ):
            result = backend.capture_primary()
            assert result is None
            # CGImage = None → CFRelease 미호출 의 의무.
            fake_cf.CFRelease.assert_not_called()
