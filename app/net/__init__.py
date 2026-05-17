"""TooTalk 네트워크 계층 — 시그널링 WebSocket 클라이언트.

본 서브패키지는 모든 IO 가 비동기(``aiohttp``)다. Qt slot 에서 호출할
때는 반드시 ``asyncio.create_task`` 또는 ``asyncio.ensure_future`` 로
코루틴을 예약해야 한다 (정본 §E — 비동기 전용 규약).

WebRTC 본체(DataChannel·PeerConnection) 는 본 계층의 책임이 아니다 —
Task #16 에서 ``app.net.webrtc`` 등 별도 모듈로 추가될 예정.
"""
