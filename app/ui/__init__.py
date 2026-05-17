"""TooTalk UI 계층 — PyQt6 위젯/윈도우 모음.

본 서브패키지는 View 만 담당한다. 비즈니스 로직·시그널링 IO 는
``app.core`` 와 ``app.net`` 에 분리되며, 본 계층의 위젯은 단지 사용자
입력을 받아 Qt signal 을 발행하거나 외부 상태를 표시한다.

위젯 구성:

- ``main_window.MainWindow`` — 최상위 QMainWindow
- ``chat_view.ChatView``     — 메시지 리스트 스크롤 영역
- ``message_bubble.MessageBubble`` — 단일 메시지 버블
- ``status_bar.StatusBar``   — 시그널링 연결 상태 + peer 수 표시
"""
