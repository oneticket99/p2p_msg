"""TooTalk WebRTC DataChannel 계층 — aiortc 기반 P2P 데이터 전송.

본 서브패키지는 시그널링 계층(``app.net.signaling_client``) 위에 얹혀
실제 텍스트·이미지·파일을 운반하는 WebRTC PeerConnection / DataChannel
래퍼와 송수신 모듈을 제공한다. 모든 IO 는 비동기다 (정본 §E — 동기 IO
금지). 파일 디스크 IO 는 ``aiofiles`` 또는 ``asyncio.to_thread`` 경유.

구성 모듈:

- ``protocol``        : 파일 전송 프로토콜 5종 메시지 (FILE_META/CHUNK/ACK/END/DONE)
- ``peer``            : ``RTCPeerConnection`` 래퍼 (Offer/Answer/ICE + DataChannel)
- ``file_sender``     : 파일 송신기 — backpressure 적용 + progress signal
- ``file_receiver``   : 파일 수신기 — 청크 누적 + 주기적 ACK 송신
- ``image_processor`` : Pillow 기반 썸네일 생성 (CPU-bound → ``to_thread``)

본 패키지는 Phase 1 MVP 의 M4 마일스톤 (파일/이미지 송수신 + 양방향
ProgressBar) 핵심 코드 영역이다. UI 통합 (``main_window`` 의
``_on_send_clicked`` 슬롯과의 결선) 은 본 task 범위 외이며 별도 task
에서 진행한다.
"""
