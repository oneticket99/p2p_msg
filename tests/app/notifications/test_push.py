# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.notifications.push`` 단위 테스트.

transport-agnostic push 알림 skeleton 검증 — 4 platform (APNS/FCM/SILENT/PULL) +
PushTarget 검증 + silent / visible payload 산출 + offline filter + batch helpers.
"""

from __future__ import annotations

import pytest

from app.notifications.push import (
    Platform,
    PushBatch,
    PushPayload,
    PushTarget,
    format_silent_data_payload,
    format_visible_payload,
    select_offline_targets,
)


def _apns_target() -> PushTarget:
    """APNS test target — 32 byte device token placeholder."""

    return PushTarget(
        user_id=1,
        device_id="dev-apns-1",
        platform=Platform.APNS,
        push_token=b"\x00" * 32,
    )


def _fcm_target() -> PushTarget:
    """FCM test target — placeholder registration token."""

    return PushTarget(
        user_id=2,
        device_id="dev-fcm-1",
        platform=Platform.FCM,
        push_token=b"fcm-token-bytes",
    )


def _silent_target() -> PushTarget:
    """SILENT test target — push_token 부재."""

    return PushTarget(
        user_id=3,
        device_id="dev-silent-1",
        platform=Platform.SILENT,
    )


def _pull_target() -> PushTarget:
    """PULL test target — push_token 부재 의무."""

    return PushTarget(
        user_id=4,
        device_id="dev-pull-1",
        platform=Platform.PULL,
    )


class TestPushTargetValidation:
    """``PushTarget`` 의 dataclass 입력 검증."""

    def test_valid_apns_construction(self) -> None:
        target = _apns_target()
        assert target.platform == Platform.APNS
        assert target.push_token == b"\x00" * 32

    def test_valid_silent_no_token(self) -> None:
        target = _silent_target()
        assert target.push_token is None

    def test_zero_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id 양수 의무"):
            PushTarget(user_id=0, device_id="d", platform=Platform.PULL)

    def test_negative_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id 양수 의무"):
            PushTarget(user_id=-1, device_id="d", platform=Platform.PULL)

    def test_empty_device_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="device_id 빈 문자열 불가"):
            PushTarget(user_id=1, device_id="", platform=Platform.PULL)

    def test_pull_with_token_rejected(self) -> None:
        with pytest.raises(ValueError, match="PULL platform 의 push_token 부재 의무"):
            PushTarget(
                user_id=1,
                device_id="d",
                platform=Platform.PULL,
                push_token=b"unexpected",
            )

    def test_apns_without_token_rejected(self) -> None:
        with pytest.raises(ValueError, match="apns platform 의 push_token 의무"):
            PushTarget(user_id=1, device_id="d", platform=Platform.APNS)

    def test_fcm_without_token_rejected(self) -> None:
        with pytest.raises(ValueError, match="fcm platform 의 push_token 의무"):
            PushTarget(user_id=1, device_id="d", platform=Platform.FCM)


class TestPushPayloadValidation:
    """``PushPayload`` 의 invariant 검증."""

    def test_silent_no_title_body_ok(self) -> None:
        target = _silent_target()
        payload = PushPayload(target=target, data={"envelope_id": "abc"})
        assert payload.is_silent
        assert payload.title is None

    def test_silent_with_title_rejected(self) -> None:
        target = _silent_target()
        with pytest.raises(ValueError, match="SILENT platform 의 title / body 의 None 의무"):
            PushPayload(target=target, title="should fail")

    def test_silent_with_body_rejected(self) -> None:
        target = _silent_target()
        with pytest.raises(ValueError, match="SILENT platform 의 title / body 의 None 의무"):
            PushPayload(target=target, body="should fail")

    def test_visible_apns_construction(self) -> None:
        target = _apns_target()
        payload = PushPayload(target=target, title="Alice", body="새 메시지 1개")
        assert not payload.is_silent


class TestFormatSilentDataPayload:
    """``format_silent_data_payload`` 산출 검증."""

    def test_basic_silent_payload(self) -> None:
        target = _silent_target()
        payload = format_silent_data_payload(target, envelope_id="env-abc-123")
        assert payload.is_silent
        assert payload.data == {"envelope_id": "env-abc-123"}
        assert payload.title is None
        assert payload.body is None

    def test_extra_data_merged(self) -> None:
        target = _silent_target()
        payload = format_silent_data_payload(
            target,
            envelope_id="env-xyz",
            extra_data={"chat_id": "42", "priority": "high"},
        )
        assert payload.data == {
            "envelope_id": "env-xyz",
            "chat_id": "42",
            "priority": "high",
        }

    def test_extra_envelope_id_collision_rejected(self) -> None:
        target = _silent_target()
        with pytest.raises(ValueError, match="extra_data 의 envelope_id key 충돌"):
            format_silent_data_payload(
                target,
                envelope_id="env-a",
                extra_data={"envelope_id": "env-b"},
            )

    def test_non_silent_target_rejected(self) -> None:
        target = _apns_target()
        with pytest.raises(ValueError, match="SILENT platform 의무"):
            format_silent_data_payload(target, envelope_id="env")

    def test_empty_envelope_id_rejected(self) -> None:
        target = _silent_target()
        with pytest.raises(ValueError, match="envelope_id 빈 문자열 불가"):
            format_silent_data_payload(target, envelope_id="")


class TestFormatVisiblePayload:
    """``format_visible_payload`` 산출 검증."""

    def test_apns_default(self) -> None:
        target = _apns_target()
        payload = format_visible_payload(target, sender_alias="alice")
        assert payload.title == "alice"
        assert payload.body == "새 메시지 1개"
        assert payload.data == {}

    def test_fcm_with_preview_count(self) -> None:
        target = _fcm_target()
        payload = format_visible_payload(
            target, sender_alias="bob", preview_count=5
        )
        assert payload.body == "새 메시지 5개"

    def test_envelope_id_included(self) -> None:
        target = _apns_target()
        payload = format_visible_payload(
            target, sender_alias="alice", envelope_id="env-42"
        )
        assert payload.data == {"envelope_id": "env-42"}

    def test_collapse_key_propagated(self) -> None:
        target = _fcm_target()
        payload = format_visible_payload(
            target, sender_alias="alice", collapse_key="thread:42"
        )
        assert payload.collapse_key == "thread:42"

    def test_silent_target_rejected(self) -> None:
        target = _silent_target()
        with pytest.raises(ValueError, match="APNS / FCM platform 의무"):
            format_visible_payload(target, sender_alias="alice")

    def test_empty_alias_rejected(self) -> None:
        target = _apns_target()
        with pytest.raises(ValueError, match="sender_alias 빈 문자열 불가"):
            format_visible_payload(target, sender_alias="")

    def test_zero_preview_count_rejected(self) -> None:
        target = _apns_target()
        with pytest.raises(ValueError, match="preview_count 양수 의무"):
            format_visible_payload(target, sender_alias="alice", preview_count=0)


class TestSelectOfflineTargets:
    """``select_offline_targets`` filter 검증."""

    def test_all_offline_returned(self) -> None:
        targets = [_apns_target(), _fcm_target(), _silent_target()]
        offline = select_offline_targets(targets, frozenset())
        assert len(offline) == 3

    def test_online_filtered(self) -> None:
        targets = [_apns_target(), _fcm_target(), _silent_target()]
        online = frozenset({"dev-fcm-1"})
        offline = select_offline_targets(targets, online)
        assert len(offline) == 2
        assert all(t.device_id != "dev-fcm-1" for t in offline)

    def test_all_online_empty_result(self) -> None:
        targets = [_apns_target(), _silent_target()]
        online = frozenset({"dev-apns-1", "dev-silent-1"})
        offline = select_offline_targets(targets, online)
        assert offline == []

    def test_order_preserved(self) -> None:
        targets = [_apns_target(), _fcm_target(), _silent_target()]
        offline = select_offline_targets(targets, frozenset())
        device_ids = [t.device_id for t in offline]
        assert device_ids == ["dev-apns-1", "dev-fcm-1", "dev-silent-1"]


class TestPushBatch:
    """``PushBatch`` aggregation 검증."""

    def test_empty_batch(self) -> None:
        batch = PushBatch()
        assert batch.total == 0
        assert batch.silent_count == 0
        assert batch.visible_count == 0

    def test_counts_split_correctly(self) -> None:
        silent = format_silent_data_payload(_silent_target(), envelope_id="e1")
        visible_apns = format_visible_payload(_apns_target(), sender_alias="a")
        visible_fcm = format_visible_payload(_fcm_target(), sender_alias="b")
        batch = PushBatch(payloads=[silent, visible_apns, visible_fcm])
        assert batch.total == 3
        assert batch.silent_count == 1
        assert batch.visible_count == 2

    def test_by_platform_filter(self) -> None:
        silent = format_silent_data_payload(_silent_target(), envelope_id="e1")
        visible_apns = format_visible_payload(_apns_target(), sender_alias="a")
        visible_fcm = format_visible_payload(_fcm_target(), sender_alias="b")
        batch = PushBatch(payloads=[silent, visible_apns, visible_fcm])
        assert len(batch.by_platform(Platform.APNS)) == 1
        assert len(batch.by_platform(Platform.FCM)) == 1
        assert len(batch.by_platform(Platform.SILENT)) == 1
        assert len(batch.by_platform(Platform.PULL)) == 0
