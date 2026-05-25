"""AppState — 애플리케이션 단일 진실 공급원 (싱글톤).

UI 위젯, 시그널링 클라이언트, 추후 추가될 DataChannel 매니저가 동일한
상태를 참조하도록 본 모듈이 process-wide 싱글톤을 제공한다.

보유 상태:

- ``room_id``         : 현재 합류한 방 식별자 (None = 미입장)
- ``peer_id``         : self peer 식별자 (None = 미설정)
- ``connection_state``: ``DISCONNECTED`` / ``CONNECTING`` / ``CONNECTED`` / ``RECONNECTING`` / ``ERROR``
- ``known_peers``     : 동일 방 안의 다른 peer_id 집합 (self 제외)

본 클래스는 의도적으로 Qt 의존성을 갖지 않는다 — PyQt 미설치 환경에서도
``app.core`` 만 import 하여 상태 머신을 단위 테스트할 수 있어야 한다.
"""

from __future__ import annotations

import threading
from typing import Final, Optional


_VALID_CONN_STATES: Final[frozenset[str]] = frozenset(
    # cycle 169.775 — RECONNECTING 추가 (SignalingClient backoff 재연결 상태)
    {"DISCONNECTED", "CONNECTING", "CONNECTED", "RECONNECTING", "ERROR"}
)


class AppState:
    """애플리케이션 상태 싱글톤.

    Notes
    -----
    - 단일 GUI 프로세스에서만 사용된다는 전제 — 멀티 프로세스 공유 금지.
    - 동일 스레드(qasync 단일 루프) 내부 호출이 일반적이지만, 추후 백그라운드
      스레드 합류 가능성을 대비해 인스턴스 발급 자체는 lock 으로 보호한다.
    """

    _instance: Optional["AppState"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # 직접 생성 금지 — ``AppState.instance()`` 만 사용
        if AppState._instance is not None:
            raise RuntimeError(
                "AppState 는 싱글톤입니다 — AppState.instance() 로 접근하세요."
            )

        # 식별자
        self._room_id: Optional[str] = None
        self._peer_id: Optional[str] = None

        # 연결 상태
        self._connection_state: str = "DISCONNECTED"

        # 동일 방의 다른 peer 들
        self._known_peers: set[str] = set()

    # ------------------------------------------------------------------
    # 싱글톤 진입점
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "AppState":
        """프로세스 전역 인스턴스 반환 (lazy 생성)."""

        with cls._lock:
            if cls._instance is None:
                cls._instance = cls.__new__(cls)
                # __init__ 우회 후 수동 초기화 — 싱글톤 가드 회피
                cls._instance._room_id = None
                cls._instance._peer_id = None
                cls._instance._connection_state = "DISCONNECTED"
                cls._instance._known_peers = set()
            return cls._instance

    # ------------------------------------------------------------------
    # 식별자 관리
    # ------------------------------------------------------------------

    @property
    def room_id(self) -> Optional[str]:
        """현재 방 식별자 (없으면 None)."""

        return self._room_id

    @property
    def peer_id(self) -> Optional[str]:
        """self peer 식별자 (없으면 None)."""

        return self._peer_id

    def set_identity(self, room_id: str, peer_id: str) -> None:
        """방/self 식별자 설정.

        빈 문자열은 거부한다 (정본 §E — 외부 입력 무효값 안전 폴백 규약).
        """

        if not room_id or not peer_id:
            raise ValueError("room_id 와 peer_id 는 비어 있을 수 없습니다.")
        self._room_id = room_id
        self._peer_id = peer_id

    def clear_identity(self) -> None:
        """방 이탈 시 식별자 초기화 — peer 목록도 함께 비운다."""

        self._room_id = None
        self._peer_id = None
        self._known_peers.clear()

    # ------------------------------------------------------------------
    # 연결 상태
    # ------------------------------------------------------------------

    @property
    def connection_state(self) -> str:
        """현재 시그널링 연결 상태."""

        return self._connection_state

    def set_connection_state(self, state: str) -> None:
        """연결 상태 갱신 (화이트리스트 검증)."""

        if state not in _VALID_CONN_STATES:
            raise ValueError(
                f"허용되지 않은 connection_state: {state!r} "
                f"(허용: {sorted(_VALID_CONN_STATES)})"
            )
        self._connection_state = state

    # ------------------------------------------------------------------
    # peer 목록
    # ------------------------------------------------------------------

    @property
    def known_peers(self) -> frozenset[str]:
        """동일 방의 다른 peer 목록 (불변 스냅샷)."""

        return frozenset(self._known_peers)

    def replace_peers(self, peers: list[str]) -> None:
        """JOIN 응답(``PEERS``) 수신 시 전체 목록 교체."""

        self._known_peers = set(p for p in peers if p)

    def add_peer(self, peer_id: str) -> None:
        """``PEER_JOINED`` 수신 시 1명 추가."""

        if peer_id:
            self._known_peers.add(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        """``PEER_LEFT`` 수신 시 1명 제거 — 없으면 무시."""

        self._known_peers.discard(peer_id)

    # ------------------------------------------------------------------
    # 테스트 보조 — 싱글톤 리셋 (단위 테스트에서만 사용)
    # ------------------------------------------------------------------

    @classmethod
    def _reset_for_tests(cls) -> None:
        """싱글톤 인스턴스를 폐기하여 다음 ``instance()`` 호출 시 재생성.

        프로덕션 코드 경로에서는 호출 금지. 단위 테스트 전용.
        """

        with cls._lock:
            cls._instance = None
