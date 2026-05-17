"""TooTalk 데스크탑 클라이언트 패키지 (코드명 p2p_msg).

Phase 1 MVP PyQt6 + qasync 기반 — Qt UI 와 asyncio 이벤트 루프를 단일
스레드에서 통합 실행한다. 본 패키지는 아래 4 계층으로 구성된다.

- ``app.ui``    : PyQt6 위젯·윈도우·레이아웃 (View 계층)
- ``app.core``  : 애플리케이션 상태·환경변수 로딩 (State 계층)
- ``app.net``   : 시그널링 WebSocket 클라이언트 (Network 계층)
- ``app.main``  : QApplication + qasync.QEventLoop 진입점

본 Phase 1 스켈레톤은 UI 골격과 시그널링 클라이언트 구조만 제공하며
WebRTC DataChannel 연동·이미지/파일 송수신·SQLite 영속화 등 실 데이터
경로는 후속 task (#16 등) 에서 별도 추가한다.
"""

__version__ = "0.1.0"
