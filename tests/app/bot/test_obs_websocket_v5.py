# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.obs_websocket_client`` cycle 148 actual v5 handshake 단위 테스트.

cycle 148 = obs-websocket v5 protocol 의 actual binding (cycle 141 skeleton →
actual). 본 test 는 ``websockets.connect`` 를 mock 의무 — 실 OBS 호출 차단.

검증 의무 8 test —
- TestObsHelloReceive — op=0 Hello + authentication salt + challenge 수신
- TestIdentifySend — SHA256 password hash + rpcVersion 1 송신
- TestIdentifiedAccepted — op=2 Identified + negotiatedRpcVersion 검증
- TestGetSceneListResponse — op=6 GetSceneList + op=7 response parse
- TestSetCurrentScene — op=6 SetCurrentProgramScene + boolean response
- TestTriggerAlert — CallVendorRequest payload (obs-browser emit_event)
- TestWebSocketsAbsent — websockets 부재 graceful False all method
- TestAuthChallengeMismatch — auth fail → connect False
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from typing import Any, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

import app.bot.obs_websocket_client as obs_mod
from app.bot.obs_websocket_client import (
    ObsConnectionConfig,
    ObsSceneInfo,
    ObsWebSocketClient,
    _compute_auth_string,
)


class _FakeWebSocket:
    """websockets.WebSocketClientProtocol 의 의 minimal mock.

    한글 주석 — 송신 메시지 기록 + recv queue scripted response.
    """

    def __init__(self, scripted_responses: List[str]) -> None:
        # 한글 주석 — 시나리오 별 recv 의 응답 sequence
        self._responses = list(scripted_responses)
        self.sent: List[str] = []
        self.closed = False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if not self._responses:
            raise RuntimeError("scripted recv 고갈")
        return self._responses.pop(0)

    async def close(self) -> None:
        self.closed = True


def _make_hello(with_auth: bool = False) -> str:
    """Hello (op=0) 메시지 JSON 생성 — auth 유/무 분기."""

    d: dict = {
        "obsWebSocketVersion": "5.4.0",
        "rpcVersion": 1,
    }
    if with_auth:
        d["authentication"] = {
            "challenge": "challenge_string_test",
            "salt": "salt_string_test",
        }
    return json.dumps({"op": 0, "d": d})


def _make_identified(rpc_version: int = 1) -> str:
    """Identified (op=2) 메시지 JSON 생성."""

    return json.dumps(
        {"op": 2, "d": {"negotiatedRpcVersion": rpc_version}}
    )


def _make_request_response(
    request_id: str,
    request_type: str,
    result: bool = True,
    response_data: Optional[dict] = None,
    code: int = 100,
) -> str:
    """RequestResponse (op=7) 메시지 JSON 생성."""

    return json.dumps(
        {
            "op": 7,
            "d": {
                "requestType": request_type,
                "requestId": request_id,
                "requestStatus": {
                    "result": result,
                    "code": code,
                },
                "responseData": response_data or {},
            },
        }
    )


def _patched_connect(fake_ws: _FakeWebSocket):
    """``websockets.connect`` AsyncMock 생성 — fake_ws 반환."""

    async def _connect(*args: Any, **kwargs: Any) -> _FakeWebSocket:
        return fake_ws

    return _connect


# 한글 주석 — websockets 의 mock — _WS_AVAILABLE 의 강제 True + connect 패치
@pytest.fixture
def force_ws_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_WS_AVAILABLE = True`` 강제 + ``websockets`` namespace 의 mock 주입."""

    monkeypatch.setattr(obs_mod, "_WS_AVAILABLE", True)

    class _MockWebsocketsModule:
        connect = staticmethod(AsyncMock())

    monkeypatch.setattr(obs_mod, "websockets", _MockWebsocketsModule, raising=False)


class TestObsHelloReceive:
    """op=0 Hello 메시지 수신 + auth challenge salt 검증."""

    def test_hello_no_auth(self, force_ws_available: None) -> None:
        # 한글 주석 — auth 부재 시 Hello 수신 → Identify 송신 → Identified 수신
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient(ObsConnectionConfig(host="localhost"))
        result = asyncio.run(client.connect())
        assert result is True
        assert client.is_connected is True
        # 한글 주석 — Identify 송신 직후 인증 필드 부재 검증
        sent_identify = json.loads(fake.sent[0])
        assert sent_identify["op"] == 1
        assert "authentication" not in sent_identify["d"]

    def test_hello_with_auth_challenge(self, force_ws_available: None) -> None:
        # 한글 주석 — auth 요구 Hello → password 기반 auth string 송신
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=True),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        cfg = ObsConnectionConfig(host="localhost", password="secret_pw")
        client = ObsWebSocketClient(cfg)
        result = asyncio.run(client.connect())
        assert result is True
        sent_identify = json.loads(fake.sent[0])
        assert "authentication" in sent_identify["d"]
        # 한글 주석 — auth string SHA256 base64 expected 검증
        expected_auth = _compute_auth_string(
            "secret_pw", "salt_string_test", "challenge_string_test"
        )
        assert sent_identify["d"]["authentication"] == expected_auth


class TestIdentifySend:
    """SHA256 password hash + rpcVersion 1 의 Identify 송신 검증."""

    def test_identify_rpc_version_one(self, force_ws_available: None) -> None:
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        asyncio.run(client.connect())
        sent_identify = json.loads(fake.sent[0])
        assert sent_identify["op"] == 1
        assert sent_identify["d"]["rpcVersion"] == 1

    def test_auth_string_sha256_double_hash(self) -> None:
        # 한글 주석 — _compute_auth_string 의 SHA256 double-hash + base64 검증
        password = "test_password_xyz"
        salt = "abcdef1234567890"
        challenge = "challenge9876"

        # 한글 주석 — 1단계 — base64(sha256(password+salt))
        step1 = base64.b64encode(
            hashlib.sha256((password + salt).encode("utf-8")).digest()
        ).decode("ascii")
        # 한글 주석 — 2단계 — base64(sha256(step1+challenge))
        expected = base64.b64encode(
            hashlib.sha256((step1 + challenge).encode("utf-8")).digest()
        ).decode("ascii")

        actual = _compute_auth_string(password, salt, challenge)
        assert actual == expected


class TestIdentifiedAccepted:
    """op=2 Identified + negotiatedRpcVersion 검증."""

    def test_identified_rpc_version_match(
        self, force_ws_available: None
    ) -> None:
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(rpc_version=1),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        result = asyncio.run(client.connect())
        assert result is True
        assert client.is_connected is True

    def test_identified_rpc_version_mismatch_rejected(
        self, force_ws_available: None
    ) -> None:
        # 한글 주석 — rpcVersion=2 (서버 future) → 클라 1 mismatch → False
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(rpc_version=2),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        result = asyncio.run(client.connect())
        assert result is False
        assert client.is_connected is False


class TestGetSceneListResponse:
    """op=6 GetSceneList request → op=7 scenes list parse."""

    def test_get_scene_list_parsed(self, force_ws_available: None) -> None:
        # 한글 주석 — handshake 2 msg + GetSceneList response 1 msg
        # requestId 동적 — _make_request_response 의 의 fake 응답 동적 생성
        scenes_response = {
            "currentProgramSceneName": "Main",
            "scenes": [
                {"sceneIndex": 0, "sceneName": "Main"},
                {"sceneIndex": 1, "sceneName": "BRB"},
                {"sceneIndex": 2, "sceneName": "Ending"},
            ],
        }

        # 한글 주석 — connect → send Identify → recv Identified → send GetSceneList → recv response
        # request id 는 client 의 의 uuid4 — fake recv 는 echo 의무
        class _SceneAwareFakeWS(_FakeWebSocket):
            async def send(self, data: str) -> None:
                self.sent.append(data)
                msg = json.loads(data)
                # 한글 주석 — Request (op=6) 송신 시 즉시 response queue 적재
                if msg.get("op") == 6:
                    d = msg["d"]
                    self._responses.append(
                        _make_request_response(
                            request_id=d["requestId"],
                            request_type=d["requestType"],
                            response_data=scenes_response,
                        )
                    )

        fake = _SceneAwareFakeWS(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        asyncio.run(client.connect())
        scenes = asyncio.run(client.get_scene_list())
        assert len(scenes) == 3
        assert all(isinstance(s, ObsSceneInfo) for s in scenes)
        assert scenes[0].name == "Main"
        assert scenes[0].is_program is True
        assert scenes[1].name == "BRB"
        assert scenes[1].is_program is False
        assert scenes[2].index == 2


class TestSetCurrentScene:
    """op=6 SetCurrentProgramScene + boolean response."""

    def test_set_current_scene_success(self, force_ws_available: None) -> None:
        class _SceneAwareFakeWS(_FakeWebSocket):
            async def send(self, data: str) -> None:
                self.sent.append(data)
                msg = json.loads(data)
                if msg.get("op") == 6:
                    d = msg["d"]
                    self._responses.append(
                        _make_request_response(
                            request_id=d["requestId"],
                            request_type=d["requestType"],
                            result=True,
                        )
                    )

        fake = _SceneAwareFakeWS(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        asyncio.run(client.connect())
        result = asyncio.run(client.set_current_scene("BRB"))
        assert result is True
        # 한글 주석 — 송신 메시지 — Identify (1) + SetCurrentProgramScene (2번째)
        request_msg = json.loads(fake.sent[1])
        assert request_msg["op"] == 6
        assert request_msg["d"]["requestType"] == "SetCurrentProgramScene"
        assert request_msg["d"]["requestData"]["sceneName"] == "BRB"

    def test_set_current_scene_failure(self, force_ws_available: None) -> None:
        # 한글 주석 — requestStatus.result=False → False 반환
        class _FailFakeWS(_FakeWebSocket):
            async def send(self, data: str) -> None:
                self.sent.append(data)
                msg = json.loads(data)
                if msg.get("op") == 6:
                    d = msg["d"]
                    self._responses.append(
                        _make_request_response(
                            request_id=d["requestId"],
                            request_type=d["requestType"],
                            result=False,
                            code=600,
                        )
                    )

        fake = _FailFakeWS(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        asyncio.run(client.connect())
        result = asyncio.run(client.set_current_scene("NonExistentScene"))
        assert result is False


class TestTriggerAlert:
    """CallVendorRequest (obs-browser emit_event) payload 검증."""

    def test_trigger_alert_payload(self, force_ws_available: None) -> None:
        class _AlertFakeWS(_FakeWebSocket):
            async def send(self, data: str) -> None:
                self.sent.append(data)
                msg = json.loads(data)
                if msg.get("op") == 6:
                    d = msg["d"]
                    self._responses.append(
                        _make_request_response(
                            request_id=d["requestId"],
                            request_type=d["requestType"],
                            response_data={"vendorResponse": {"ok": True}},
                        )
                    )

        fake = _AlertFakeWS(
            scripted_responses=[
                _make_hello(with_auth=False),
                _make_identified(),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        client = ObsWebSocketClient()
        asyncio.run(client.connect())
        result = asyncio.run(
            client.trigger_alert(
                "donation",
                {"viewer": "alice", "amount": 5000},
            )
        )
        assert result is True

        request_msg = json.loads(fake.sent[1])
        assert request_msg["op"] == 6
        assert request_msg["d"]["requestType"] == "CallVendorRequest"
        req_data = request_msg["d"]["requestData"]
        assert req_data["vendorName"] == "obs-browser"
        assert req_data["requestType"] == "emit_event"
        assert req_data["requestData"]["event_name"] == "donation"
        assert req_data["requestData"]["event_data"]["viewer"] == "alice"
        assert req_data["requestData"]["event_data"]["amount"] == 5000


class TestWebSocketsAbsent:
    """websockets 라이브러리 부재 graceful False 검증."""

    def test_connect_false_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(obs_mod, "_WS_AVAILABLE", False)
        client = ObsWebSocketClient()
        result = asyncio.run(client.connect())
        assert result is False
        assert client.is_connected is False

    def test_get_scene_list_empty_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(obs_mod, "_WS_AVAILABLE", False)
        client = ObsWebSocketClient()
        scenes = asyncio.run(client.get_scene_list())
        assert scenes == []

    def test_set_current_scene_false_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(obs_mod, "_WS_AVAILABLE", False)
        client = ObsWebSocketClient()
        result = asyncio.run(client.set_current_scene("Main"))
        assert result is False

    def test_trigger_alert_false_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(obs_mod, "_WS_AVAILABLE", False)
        client = ObsWebSocketClient()
        result = asyncio.run(
            client.trigger_alert("test_alert", {"key": "value"})
        )
        assert result is False


class TestAuthChallengeMismatch:
    """auth fail → connect False 시나리오."""

    def test_auth_required_but_password_missing(
        self, force_ws_available: None
    ) -> None:
        # 한글 주석 — 서버 auth 요구 + 클라 password 부재 → False
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=True),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        cfg = ObsConnectionConfig(host="localhost", password="")
        client = ObsWebSocketClient(cfg)
        result = asyncio.run(client.connect())
        assert result is False
        assert client.is_connected is False
        # 한글 주석 — Identify 송신 차단 확인
        assert fake.sent == []

    def test_auth_wrong_password_rejected(
        self, force_ws_available: None
    ) -> None:
        # 한글 주석 — wrong password → server 의 Identified 미응답 (op=0 err)
        # 본 mock 은 op 불일치 응답 → False
        fake = _FakeWebSocket(
            scripted_responses=[
                _make_hello(with_auth=True),
                # 한글 주석 — Identified 대신 op=5 Event 시뮬 (auth 실패 의 의 obs server pattern)
                json.dumps({"op": 5, "d": {"eventType": "AuthFailed"}}),
            ]
        )
        obs_mod.websockets.connect = _patched_connect(fake)  # type: ignore[attr-defined]

        cfg = ObsConnectionConfig(host="localhost", password="wrong_pw")
        client = ObsWebSocketClient(cfg)
        result = asyncio.run(client.connect())
        assert result is False
        assert client.is_connected is False
