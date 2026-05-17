# TooTalk Desktop Client (app/)

> TooTalk(코드명 `p2p_msg`) Phase 1 MVP — PyQt6 + qasync 기반 데스크탑
> P2P 메신저 클라이언트. 시그널링 서버 하나만 거치고 실 데이터는 WebRTC
> DataChannel 직결로 운반한다 (본 Phase 스켈레톤은 UI 골격 + 시그널링
> 클라이언트까지. WebRTC 본체는 Task #16 에서 결합).

저장소 맵: [AGENTS.md](../AGENTS.md) · 시그널링 프로토콜: [server/README.md](../server/README.md)

---

## 1. 빠른 시작

### 1.1 의존성 설치

```bash
# 저장소 루트에서
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
```

### 1.2 실행

```bash
# 저장소 루트에서 (app 패키지를 모듈로 호출)
python -m app.main
```

윈도우 타이틀 "TooTalk" 가 뜨고, StatusBar 가 `DISCONNECTED · peers: 0`
상태로 시작한다. 메뉴바 "설정 → 방 입장" 으로 room/peer_id 를 입력하면
`AppState` 가 갱신되고 ChatView 에 시스템 메시지가 한 줄 추가된다.

> 본 스켈레톤은 시그널링 서버에 자동 연결하지 않는다. 실 연결 활성화는
> Task #16 (`@backend-agent` 가 `app.net.webrtc` 추가 후) 에서 진행한다.

---

## 2. 환경변수

값은 모두 저장소 루트의 `.env` 또는 `.env.local` 에서 주입된다. 하드코딩
금지 (정본 §E). 예시는 `.env.example` 참조.

| 키 | 기본값 | 설명 |
|---|---|---|
| `SIGNAL_SERVER_HOST` | `114.207.112.73` | 시그널링 서버 호스트 |
| `SIGNAL_SERVER_WS_PORT` | `8765` | WebSocket TCP 포트 |
| `SIGNAL_SERVER_WS_SCHEME` | `ws` | `ws` 또는 `wss` (Phase 1 은 `ws` 만) |
| `STUN_URL` | `stun:stun.l.google.com:19302` | WebRTC ICE 수집용 STUN URL |
| `TURN_URL` | (비움) | 선택. 비어 있으면 TURN 미사용 |
| `TURN_USERNAME` | (비움) | TURN 인증 사용자명 |
| `TURN_CREDENTIAL` | (비움) | TURN 인증 비밀번호 |
| `USER_NICKNAME` | `guest` | 클라이언트 표시명 (Phase 1 데모) |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `DB_HOST` | `127.0.0.1` | MariaDB 호스트 (사용자 directive 2026-05-17) |
| `DB_PORT` | `3306` | MariaDB TCP 포트 |
| `DB_USER` | `tootalk` | MariaDB 접속 사용자 |
| `DB_PASS` | (비움) | MariaDB 비밀번호 — `.env.local` 주입 |
| `DB_NAME` | `tootalk` | MariaDB 데이터베이스 명 |
| `MEDIA_CACHE_DIR` | `./media_cache` | 이미지/파일 캐시 디렉토리 |

무효 값(빈 문자열·잘못된 정수)은 자동으로 기본값으로 폴백한다
(`app/core/config.py` 참조).

---

## 3. 모듈 구조 (View ↔ State ↔ Network)

```text
app/
├── __init__.py             # 패키지 docstring + __version__
├── main.py                 # 진입점 — QApplication + qasync.QEventLoop
├── requirements.txt        # PyQt6 + qasync + aiohttp + python-dotenv
├── README.md               # 본 문서
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # QMainWindow — 채팅 뷰 + 입력 + 메뉴 + StatusBar
│   ├── chat_view.py       # QScrollArea + QVBoxLayout — 메시지 리스트
│   ├── message_bubble.py  # QFrame — 단일 메시지 (텍스트 + 타임스탬프)
│   └── status_bar.py      # QStatusBar — 연결 상태 + peer 수
├── core/
│   ├── __init__.py
│   ├── app_state.py       # AppState 싱글톤 (room/peer/연결 상태/peer 목록)
│   └── config.py          # .env 로딩 + Config dataclass
└── net/
    ├── __init__.py
    └── signaling_client.py  # SignalingClient — aiohttp WebSocket + Qt 신호
```

의존 방향 (단방향, 정본 §E):

```text
ui  ──→ core  ←──  net
        ↑          ↑
        └── main ──┘
```

- `ui.*` 는 `core.*` 만 import 한다 — net 으로 직접 호출하지 않는다.
- `net.*` 는 `core.*` 만 import 한다 — ui 위젯을 직접 다루지 않는다.
- 두 계층의 결합은 `main.py` 또는 `MainWindow` 가 시그널/슬롯 결선으로 수행.

---

## 4. qasync 통합 — Qt × asyncio 단일 스레드

`app/main.py` 는 다음 순서로 부트스트랩한다.

1. `app.core.config.load_config()` 로 환경변수 → `Config` dataclass
2. `logging.Formatter` 를 정본 §E 형식 `[YYYY-mm-dd H:i:s]` 로 설정
3. `QApplication(sys.argv)` 생성
4. `qasync.QEventLoop(qt_app)` 을 `asyncio.set_event_loop()` 로 등록
5. `MainWindow(config=config)` 표시 후 `loop.run_forever()` 진입

비동기 호출 규약 (정본 §E):

- **Qt slot 안의 동기 코드는 허용**.
- **IO 가 필요한 경우** 반드시 `asyncio.create_task(coro)` 또는
  `asyncio.ensure_future(coro)` 로 코루틴을 예약한다.
- `time.sleep`, `requests.get` 등 블로킹 IO 사용 금지.

예시:

```python
from PyQt6.QtCore import pyqtSlot
import asyncio

class MainWindow(QMainWindow):
    @pyqtSlot()
    def _on_connect_clicked(self) -> None:
        # Qt slot 안은 동기 OK — 내부 IO 는 asyncio.create_task
        asyncio.create_task(self._signaling.connect())
```

---

## 5. 시그널링 클라이언트 (`app.net.signaling_client`)

`SignalingClient` 는 `QObject` 상속 + `pyqtSignal` 8 종 노출.

| 신호 | 페이로드 | 발행 시점 |
|---|---|---|
| `connection_state_changed(str)` | DISCONNECTED/CONNECTING/CONNECTED/ERROR | 상태 전이 시점 |
| `peers_received(list)` | `list[str]` | `PEERS` 수신 (JOIN 응답) |
| `peer_joined(str)` | `peer_id` | `PEER_JOINED` 수신 |
| `peer_left(str)` | `peer_id` | `PEER_LEFT` 수신 |
| `offer_received(str, str)` | `(from, sdp)` | `OFFER` 수신 |
| `answer_received(str, str)` | `(from, sdp)` | `ANSWER` 수신 |
| `ice_received(str, dict)` | `(from, candidate)` | `ICE` 수신 |
| `error_received(str, str)` | `(code, message)` | `ERROR` 수신 |

비동기 메서드: `connect()`, `disconnect()`, `join(room, peer_id)`,
`leave(room, peer_id)`, `send_offer(to, sdp)`, `send_answer(to, sdp)`,
`send_ice(to, candidate)`.

본 스켈레톤은 위 신호의 정의만 보유하며, 실제 슬롯 결선과 WebRTC
PeerConnection 연동은 Task #16 에서 추가된다.

---

## 6. 플랫폼별 주의사항

### 6.1 macOS

- Apple Silicon (arm64) 에서 PyQt6 휠은 `pip install PyQt6` 로 정상 설치.
- 처음 실행 시 macOS Gatekeeper 가 "Python.app" 의 접근 권한을 묻는
  다이얼로그를 띄울 수 있다. "허용" 클릭.
- Qt 플랫폼 플러그인 "cocoa" 가 없다는 오류가 나는 경우:
  - 가상환경 안에서 `pip install --force-reinstall PyQt6` 로 재설치.
  - 또는 환경변수 `QT_QPA_PLATFORM=cocoa` 명시.
- HiDPI 디스플레이에서 위젯이 흐리게 보이면 `main()` 진입 전에
  `os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")` 권장 (본
  스켈레톤에는 추가하지 않음 — 사용자 환경 차이가 커 Phase 1 후반에
  결정).

### 6.2 Windows

- Python 3.13 + 64bit 권장. `python -m venv .venv` 후 `\.venv\Scripts\activate`.
- PyQt6 휠은 wheel 캐시가 큼 — 첫 설치 시 시간이 걸린다.
- Windows Defender 가 첫 실행 시 차단할 수 있음 → "추가 정보 → 실행" 클릭.
- 콘솔에 한글 깨짐이 나타나면 `chcp 65001` 로 UTF-8 코드페이지 전환.
- 시그널링 데모 호스트(`114.207.112.73:8765`) 접속이 방화벽에 막히는 경우,
  Windows Defender 방화벽 → "앱 또는 기능이 통과하도록 허용" 에서 Python
  실행파일을 허용 목록에 추가.

### 6.3 Linux (참고)

- 본 Phase 1 공식 배포는 macOS + Windows 만 (정본 AGENTS.md §1). Linux 는
  개발용 임시 환경으로만 사용.

---

## 7. 변경 이력 (app/ 영역)

- [2026-05-17 10:30:00] app/ 디렉토리 신설 — Phase 1 MVP PyQt6 클라이언트 스켈레톤 12 파일 (`__init__.py` · `main.py` · `ui/{main_window,chat_view,message_bubble,status_bar}.py` · `core/{app_state,config}.py` · `net/signaling_client.py` · `requirements.txt` · `README.md`)
