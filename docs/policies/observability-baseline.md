---
title: "TooTalk Observability Baseline (Phase 1)"
owner: oneticket99
last_verified: 2026-05-17
status: active
authoritative_for:
  - logging instrumentation 정합 규약
  - metric baseline 정본 (환경변수 default 값)
  - 회귀 검증 절차 (Phase 1 dogfooding 시점)
---

# Observability Baseline (Phase 1)

> 본 문서는 observability-agent 사이클 15 의 권고 산출물이다.
> Phase 1 MVP 의 logging·metric 정합 의 단일 정본 — 회귀 판정 기준.

## 1. 본 문서 운영 규약

1. **정본 채택 원칙**: 환경변수 baseline = **코드 default + README §13 환경변수 표 + ARCHITECTURE.md §7** 3 위치 의 동시 일치값.
2. **drift 차단**: directive 본문·prompt 본문·sub-agent 설정 의 baseline 가정값 이 본 정본 과 불일치 시 → 본 정본 우선. 추정값 갱신 금지.
3. **갱신 절차**: 코드 default 변경 시 본 문서 + README §13 + ARCHITECTURE.md §7 + `app/rtc/*.py` 4 위치 동시 갱신. 한 위치 단독 갱신 금지.

## 2. logging instrumentation 정합 표

| 파일 | logger 명 | level 분포 | 메시지 prefix | 정합 상태 |
|---|---|---|---|---|
| `app/main.py` | `app.main` | INFO 1 | n/a (root 핸들러 설치만) | PASS — 중복 제거 가드 정합 |
| `app/rtc/protocol.py` | (없음) | n/a | n/a | PASS — 순수 데이터 모델, IO 의도적 부재 |
| `app/rtc/peer.py` | `app.rtc.peer` | INFO 8 · DEBUG 4 · WARNING 1 · EXCEPTION 6 | `[Peer]` 일관 | PASS — 상태 머신 INFO + ICE 노이즈 DEBUG 분할 |
| `app/rtc/file_sender.py` | `app.rtc.file_sender` | INFO 5 · DEBUG 3 · WARNING 2 · ERROR 1 · EXCEPTION 1 | `[FileSender]` 일관 | PASS — backpressure 폴링 DEBUG 적정 |
| `app/rtc/file_receiver.py` | `app.rtc.file_receiver` | INFO 4 · DEBUG 3 · WARNING 7 · ERROR 1 · EXCEPTION 4 | `[FileReceiver]` 일관 | PASS — 청크 노이즈 DEBUG + 프로토콜 위반 WARNING 분할 |
| `app/rtc/image_processor.py` | `app.rtc.image_processor` | DEBUG 1 · WARNING 2 | (prefix 미사용 — 자연 한국어) | CONDITIONAL — Phase 2 시점 `[ImageProcessor]` prefix 보강 권장 |
| `app/ui/file_progress_widget.py` | `app.ui.file_progress_widget` | WARNING 1 | `[FileProgressWidget]` 일관 | PASS — Qt slot 호출 빈도 고려 최소 로깅 적정 |

**format 정본**: `[%(asctime)s] %(levelname)s %(name)s — %(message)s` (asctime = `%Y-%m-%d %H:%M:%S`, 정본 §E 정합).

## 3. metric baseline 정본 표

| 지표 | 정본 위치 | baseline 값 | 변경 가능성 |
|---|---|---|---|
| `FILE_CHUNK_SIZE` | `app/rtc/file_sender.py:62` + README §13 | **16384 B (16 KiB)** | 고정 (SCTP MTU 정합) |
| `FILE_BUFFER_HIGH` | `app/rtc/file_sender.py:63` | **16777216 B (16 MiB)** | 환경변수 override 허용 (aiortc SCTP 권장 큐 깊이) |
| `FILE_BUFFER_LOW` | `app/rtc/file_sender.py:64` | **4194304 B (4 MiB)** | 환경변수 override 허용 (HIGH 의 1/4 정합) |
| `FILE_ACK_INTERVAL_BYTES` | `app/rtc/file_receiver.py:56` | **262144 B (256 KiB)** | 환경변수 override 허용 (RTT/throughput trade-off) |
| `FILE_BACKPRESSURE_POLL_MS` | `app/rtc/file_sender.py:65` | **50 ms** | 환경변수 override 허용 (대기 응답성 우선) |
| `FILE_RECEIVE_DIR` | `app/rtc/file_receiver.py` | **`~/Downloads/TooTalk`** | 환경변수 override 허용 |
| `THUMB_MAX_PX` | `app/rtc/image_processor.py:36` | **200 px** | 고정 (UI 디자인 시스템 정합) |
| `THUMB_QUALITY` | `app/rtc/image_processor.py:37` | **JPEG 80** | 고정 |
| 청크 헤더 크기 | `app/rtc/protocol.py:58` | **20 B** | 불변식 (assert 강제) |
| SHA-256 산출 청크 | `app/rtc/file_sender.py:439` | **65536 B (64 KiB)** | 고정 (디스크 IO 최적화) |
| 진행률 정규화 해상도 | `app/ui/file_progress_widget.py:61` | **100000 (100K 분해능)** | 고정 (int32 overflow 회피) |

### 3.1 drift 회수 이력

- **2026-05-17 사이클 15**: release-agent prompt 본문 의 가정값 3종 (`FILE_BUFFER_HIGH` 262144 · `FILE_BUFFER_LOW` 65536 · `FILE_BACKPRESSURE_POLL_MS` 100) 이 코드 default 와 불일치 detect (observability-agent). 본 정본 채택 = 코드 default 우선 + ARCHITECTURE.md §7 + README §13 일치.
- **2026-05-17 사이클 13**: `FILE_ACK_INTERVAL_BYTES` 524288 (문서) vs 262144 (코드) drift — qa-agent detect + 옵션 B 채택 (코드 우선) + ARCHITECTURE.md L201 정정 완료.

## 4. 회귀 위험 평가

| 항목 | 현황 | 회귀 위험 | 비고 |
|---|---|---|---|
| Phase 1 MVP DoD #1 (RTT < 500ms) | 미측정 | **검출 불가** | M5 dogfooding 시점 최초 측정 의무 |
| TD-4 (aiortc 약 5Mbps throughput) | 미측정 | **검출 불가** | Phase 1 후반 의무 task |
| SHA-256 round-trip 무결성 | 코드 검증 정합 | 낮음 | 단위 테스트 추가 권장 |
| backpressure 진입 빈도 | DEBUG 노이즈 분리됨 | 낮음 | INFO 운용 시 로그 부풀 위험 무 |
| ACK 송신 빈도 | 256 KiB / 16 KiB = 16 chunk 마다 1 ACK | 낮음 | 100 MB 파일 = 약 400 ACK + 400 progress emit |
| 임시 파일 disk leak | `_fail` + `_discard_context` 의 `unlink(missing_ok=True)` 정합 | 낮음 | 비정상 종료 시 `.partial` 잔존 가능 — Phase 2 cleanup |
| logger format 정합 | `main.py:46` 의 `%Y-%m-%d %H:%M:%S` 정본 §E 일관 | 무 | M4 일관 |
| 로그 BPE U+CE21 단독 | 0건 검출 | 무 | M4 일관 |

## 5. 회귀 검증 절차 (Phase 1 dogfooding 시점)

### 5.1 로그 회수

```bash
mkdir -p logs
python -m app.main 2>&1 | tee logs/$(date +%Y%m%d-%H%M%S).log
```

stderr 의 root 핸들러 출력을 timestamped 파일로 보존.

### 5.2 신규 ERROR/WARN 패턴 grep

```bash
grep -E "ERROR|WARNING|EXCEPTION" logs/*.log | sort -u
```

baseline 대비 신규 패턴 비교.

### 5.3 RTT 측정 (M4 DoD #1)

`Peer.text_message_received` 의 round-trip 시각 차이 — Phase 1 dogfooding 시점 최초 측정.

### 5.4 throughput 측정 (TD-4)

```bash
head -c 100M /dev/urandom > /tmp/big.bin
```

100 MB 더미 파일 송수신 + `FILE_END` ~ `FILE_DONE` 의 wall-clock 차이.

### 5.5 메모리 사용량

`psutil.Process(os.getpid()).memory_info().rss` — sender + receiver 각 100 MB transfer 동안 peak RSS 측정.

### 5.6 임시 파일 잔존

```bash
find $FILE_RECEIVE_DIR -name "*.partial" -mmin +60
```

1시간 이상 된 partial 파일 자동 cleanup 권장 (Phase 2 정책).

## 6. Phase 2 진입 전 의무 task

1. `app/observability/` 디렉토리 신설 + `logging_adapter.py` (logger prefix 일관 강제 + level 동적 갱신)
2. `FILE_RECV_TIMEOUT_S` 도입 결정 (reliability 강화)
3. `.partial` 임시 파일 자동 cleanup hook (storage 정책)
4. `image_processor` 의 `[ImageProcessor]` prefix 정정 (minor)

## 7. 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md) §E (12-factor 환경변수)
- 환경변수 표: [ARCHITECTURE.md](../../ARCHITECTURE.md) §7
- README env knob: [README.md](../../README.md) §13
- 코드: `app/rtc/file_sender.py` · `file_receiver.py` · `image_processor.py` · `protocol.py` · `app/ui/file_progress_widget.py` · `app/main.py`
- observability-agent 정의: [.claude/agents/observability-agent.md](../../.claude/agents/observability-agent.md)
- 사이클 15 평가: handoff §8.39 (`docs/exec-plans/active/2026-05-17-session-handoff.md`)

---

마지막 갱신: 2026-05-17 — observability-agent 사이클 15 정본 신설 (Phase 1 dogfooding 진입 직전 의무)
