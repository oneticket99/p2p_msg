"""TooTalk(코드명 p2p_msg) Phase 1 MVP 시그널링 서버 패키지.

본 패키지는 WebRTC Offer/Answer/ICE candidate 교환만 담당하는 aiohttp
WebSocket 시그널링 서버다. 실제 메시지·이미지·파일 데이터는 일절 통과시키지
않으며, 모든 페이로드는 클라이언트 사이 WebRTC DataChannel 직결로 운반한다.

계층 분리 (정본 §E):
    - Router 계층:  ``signaling.py``  — WebSocket 핸들러, 외부 입력 라우팅
    - Service 계층: ``room.py``       — Room/Peer 비즈니스 로직
    - Model 계층:   ``protocol.py``   — 메시지 타입 정의 (TypedDict)

모든 IO 는 ``async def`` 비동기 전용이며, 설정값은 ``.env`` 환경변수로만
주입된다 (하드코딩 금지). 로그 형식은 ``[YYYY-mm-dd H:i:s]`` 고정.
"""

# 패키지 버전 — Phase 1 MVP 골격 단계
__version__ = "0.1.0"
