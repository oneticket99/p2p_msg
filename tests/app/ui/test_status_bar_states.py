# SPDX-License-Identifier: GPL-3.0-or-later
"""StatusBar 연결 상태 화이트리스트 회귀 test — cycle 169.780 신설.

reviewer-agent finding F1(MED) 회수 — cycle 169.775 가 SignalingClient 에 RECONNECTING
상태를 추가했으나 `app/ui/status_bar.py` `_VALID_STATES` 화이트리스트 미동기로 재연결 중
"ERROR" 오표시 회귀. 본 test 는 화이트리스트가 RECONNECTING 을 포함하는지 + app_state
정본 상태 집합과 정합하는지 검증한다 (widget 미인스턴스화 — tests/app/ui hang 회피).
"""

from __future__ import annotations

from app.core.app_state import _VALID_CONN_STATES
from app.ui.status_bar import _VALID_STATES


def test_reconnecting_in_status_bar_whitelist() -> None:
    # 한글 주석 — RECONNECTING 이 화이트리스트에 있어야 set_connection_state 가 ERROR 폴백 안 함
    assert "RECONNECTING" in _VALID_STATES


def test_status_bar_whitelist_matches_app_state() -> None:
    # 한글 주석 — UI 화이트리스트와 app_state 정본 연결 상태 집합 정합 (drift 차단)
    assert _VALID_STATES == _VALID_CONN_STATES


def test_status_bar_whitelist_five_states() -> None:
    assert _VALID_STATES == frozenset(
        {"DISCONNECTED", "CONNECTING", "CONNECTED", "RECONNECTING", "ERROR"}
    )
