# TooTalk Signaling Server (server/)

> TooTalk(코드명 `p2p_msg`) Phase 1 MVP — WebRTC Offer/Answer/ICE candidate
> 교환만 담당하는 aiohttp WebSocket 시그널링 서버. 실 메시지·이미지·파일
> 데이터는 본 서버를 일절 통과하지 않으며, 클라이언트 사이 WebRTC
> DataChannel 직결로 운반된다.

저장소 맵: [AGENTS.md](../AGENTS.md) · 실행계획: [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](../docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) §2 In Scope

---

## 1. 빠른 시작

### 1.1 의존성 설치

```bash
cd server
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.2 실행

```bash
# 저장소 루트에서 실행 (server 패키지를 모듈로 호출)
python -m server.main
```

기본 바인딩: `ws://0.0.0.0:8765/ws` · health-check: `http://0.0.0.0:8765/health`

### 1.3 로컬 테스트 (websocat)

```bash
# 단말 A
websocat ws://localhost:8765/ws
{"type":"JOIN","room":"demo","peer_id":"alice"}

# 단말 B (별도 터미널)
websocat ws://localhost:8765/ws
{"type":"JOIN","room":"demo","peer_id":"bob"}
{"type":"OFFER","from":"bob","to":"alice","sdp":"v=0..."}
```

---

## 2. 환경변수

값은 모두 저장소 루트의 `.env` 또는 운영 환경의 systemd `EnvironmentFile`
에서 주입된다. 하드코딩 금지 (정본 §E).

| 키                          | 기본값         | 설명                                                                  |
|-----------------------------|----------------|-----------------------------------------------------------------------|
| `SIGNAL_SERVER_HOST`        | `0.0.0.0`      | 바인딩 호스트 (모든 인터페이스 listen)                                |
| `SIGNAL_SERVER_WS_PORT`     | `8765`         | WebSocket TCP 포트                                                    |
| `SIGNAL_SERVER_WS_SCHEME`   | `ws`           | `ws` 또는 `wss`. **Phase 1 은 `ws` 만** — `wss` 는 Phase 2 (TD-1)     |
| `LOG_LEVEL`                 | `INFO`         | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`                   |

> **TLS 후크**: `SIGNAL_SERVER_WS_SCHEME=wss` 지정 시 경고 로그를 남긴 채
> `ws` 로 폴백한다. 실제 wss 핸들링은 Phase 2 진입과 함께 SSL context 주입
> 코드를 활성화한다 (`server/main.py::_serve`).

---

## 3. 프로토콜 명세 (5 + 4)

모든 메시지는 UTF-8 JSON object envelope. 줄바꿈/스페이스 자유. 알 수 없는
필드는 무시된다 (forward-compat).

### 3.1 클라이언트 → 서버 (5종)

| 타입     | 필수 필드                                       | 의미                                                  |
|----------|-------------------------------------------------|-------------------------------------------------------|
| `JOIN`   | `room` (str), `peer_id` (str)                   | 방에 합류. 서버가 `PEERS` 응답 + `PEER_JOINED` 알림    |
| `LEAVE`  | `room` (str), `peer_id` (str)                   | 방에서 이탈. 서버가 `PEER_LEFT` 브로드캐스트            |
| `OFFER`  | `from` (str), `to` (str), `sdp` (str)           | SDP Offer 1:1 중계 (서버는 본문 미파싱)                |
| `ANSWER` | `from` (str), `to` (str), `sdp` (str)           | SDP Answer 1:1 중계                                    |
| `ICE`    | `from` (str), `to` (str), `candidate` (object)  | ICE candidate 1:1 중계                                 |

> 보안 노트: 서버는 수신 envelope 의 `from` 필드를 **신뢰하지 않는다** —
> JOIN 시점에 확정된 peer_id 로 덮어쓴 뒤 중계한다 (클라이언트 위변조 방어).

### 3.2 서버 → 클라이언트 (4종)

| 타입          | 필드                                       | 의미                                                  |
|---------------|--------------------------------------------|-------------------------------------------------------|
| `PEERS`       | `room` (str), `peers` (str[])              | JOIN 응답 — 동일 방의 기존 peer_id 목록 (본인 제외)    |
| `PEER_JOINED` | `peer_id` (str)                            | 동일 방에 신규 peer 합류 알림                          |
| `PEER_LEFT`   | `peer_id` (str)                            | 동일 방의 peer 이탈 알림 (LEAVE 또는 연결 종료)        |
| `ERROR`       | `code` (str), `message` (str)              | 프로토콜 위반·라우팅 실패 응답                          |

### 3.3 에러 코드

| 코드               | 발생 조건                                                  |
|--------------------|-----------------------------------------------------------|
| `BAD_JSON`         | 텍스트 프레임이 유효한 JSON object 가 아님                  |
| `UNKNOWN_TYPE`     | `type` 필드가 화이트리스트 5종 밖이거나 누락                |
| `MISSING_FIELD`    | 필수 필드 (`room`/`peer_id`/`to`/`sdp`/`candidate`) 누락    |
| `NOT_JOINED`       | JOIN 이전에 LEAVE/OFFER/ANSWER/ICE 전송 시도                |
| `PEER_NOT_FOUND`   | `to` 대상 peer 가 동일 방에 존재하지 않음                   |
| `ROOM_NOT_FOUND`   | 방 자체가 존재하지 않음 (드물게 race 시 발생)               |
| `SERVER_SHUTDOWN`  | 서버 종료 직전 모든 클라이언트에게 브로드캐스트              |

### 3.4 시퀀스 예시 (1:1 연결 수립)

```text
Alice → Server : {"type":"JOIN","room":"demo","peer_id":"alice"}
Server → Alice : {"type":"PEERS","room":"demo","peers":[]}

Bob   → Server : {"type":"JOIN","room":"demo","peer_id":"bob"}
Server → Bob   : {"type":"PEERS","room":"demo","peers":["alice"]}
Server → Alice : {"type":"PEER_JOINED","peer_id":"bob"}

Bob   → Server : {"type":"OFFER","from":"bob","to":"alice","sdp":"v=0..."}
Server → Alice : {"type":"OFFER","from":"bob","to":"alice","sdp":"v=0..."}

Alice → Server : {"type":"ANSWER","from":"alice","to":"bob","sdp":"v=0..."}
Server → Bob   : {"type":"ANSWER","from":"alice","to":"bob","sdp":"v=0..."}

(ICE candidate 양방향 교환 — 반복)
Alice → Server : {"type":"ICE","from":"alice","to":"bob","candidate":{...}}
Server → Bob   : {"type":"ICE","from":"alice","to":"bob","candidate":{...}}
```

이후 DataChannel 이 OPEN 되면 본 서버는 더 이상 트래픽에 관여하지 않는다.

---

## 4. 모듈 구조 (Router → Service → Model)

```text
server/
├── __init__.py         # 패키지 docstring + __version__
├── main.py             # entry point — env 로딩, logging, AppRunner
├── signaling.py        # Router 계층 — WebSocket 핸들러, 5종 메시지 라우팅
├── room.py             # Service 계층 — Peer/Room/RoomRegistry
├── protocol.py         # Model 계층 — TypedDict 메시지 정의 + 상수
├── requirements.txt    # aiohttp + python-dotenv
└── README.md           # 본 문서
```

정본 §E 코딩 불변 규칙: **Router → Service → Model 단방향 의존**.
`signaling.py` 가 `room.py` 와 `protocol.py` 를 import 하고, `room.py` 가
`protocol.py` 만 import 한다. 역방향 import 금지.

---

## 5. 데모 서버 배포

| 항목           | 값                                                   |
|----------------|------------------------------------------------------|
| 호스트         | `114.207.112.73`                                     |
| 포트           | `8765` (`ws://`) — Phase 1 TLS 미적용                |
| 배포 방식      | systemd 또는 Docker 단일 컨테이너 (task #17 에서 확정) |
| 인증           | 없음 (Phase 1 데모, TD-1 보류)                       |
| rate limit     | 없음 (Phase 1 데모, TD-1 보류)                       |

> **보안 경고**: 본 데모 서버는 공개 노출되며 인증·rate limit·TLS 가 없다.
> 악성 클라이언트의 DoS 또는 peer 식별자 충돌 시도 가능. 실서비스 전환
> 이전에 TD-1 (시그널링 서버 hardening) 해소 필수.
> 출처: [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](../docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) §8.

---

## 6. 변경 이력 (server/ 영역)

- [2026-05-17 00:00:00] 시그널링 서버 스켈레톤 신설 (`__init__.py` · `main.py` · `signaling.py` · `room.py` · `protocol.py` · `requirements.txt` · `README.md`)
