"""TooTalk core 계층 — 애플리케이션 상태 + 환경변수 로딩.

본 서브패키지는 UI 와 Network 양쪽이 공유하는 **상태/설정** 계층이다.
어떤 IO 도 직접 수행하지 않으며, 단지 다음 두 책임만 진다.

- ``app_state.AppState`` : 현재 room/peer_id/연결 상태 단일 진실 공급원
- ``config.Config``      : ``.env`` 로딩 결과 dataclass + 기본값 폴백
"""
