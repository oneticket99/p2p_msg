---
title: "Docker rebuild — cycle 152"
owner: oneticket99
last_verified: 2026-05-19
status: active
---

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Docker rebuild — cycle 152 (mobile cycle 181 prerequisite)

> 본 문서는 사용자 directive 2026-05-19 — "모바일 빌드전에 server docker 환경
> 현재까지 작업파일을 반영시켜서 다시 만들어" 절차서. cycle 100~117
> Phase 4 docker stack base 에 cycle 118~151 산출 통합 절차 + 검증 항목 +
> 사용자 manual 의무 명문화.

## 1. 본 사이클 변경 file 3종

| file | 변경 요지 |
| --- | --- |
| `server/requirements.txt` | `websockets>=12.0` + `Pillow>=10.0` + `pytesseract>=0.3.10` + `ImageHash>=4.3` 4 dependency 추가 (cycle 138~151 bot streaming + emoji moderation 의 graceful binding) |
| `deploy/web/Dockerfile` | apt 추가 — `tesseract-ocr` + `tesseract-ocr-kor` + `libjpeg62-turbo` + `libwebp7` + `libpng16-16` + `libmagic1` (Pillow + pytesseract 가 요구하는 system 의존) |
| `deploy/docker-compose.yml` | `web` service environment 확장 — `DEFAULT_LOCALE` + `AUTO_UPDATE_BASE_URL` + `CHZZK_CHANNEL_ID` + `TWITCH_OAUTH_TOKEN` + `KICK_CHANNEL_ID` + `YOUTUBE_API_KEY` + `OBS_WEBSOCKET_URL` + `OBS_WEBSOCKET_PASSWORD` + `TOONATION_API_KEY` 9 신규 env 주입 |

## 2. cycle 100~151 chain 반영 정합

### 2-1. MariaDB migration 0001~0007 자동 적용

`docker-compose.yml` 안 mariadb service —

```yaml
volumes:
  - ../server/db/migrations:/docker-entrypoint-initdb.d:ro
```

해당 mount 가 활성화하는 mariadb:11 image `/docker-entrypoint-initdb.d/`
자동 적용 chain — 첫 기동 시점 (volume `mariadb_data` empty) 알파벳 순
7 file 자동 실행.

| migration | cycle | 내용 |
| --- | --- | --- |
| `0001_init.sql` | 22 | users + email_otp + sessions (Phase 1 회원가입 base) |
| `0002_devices.sql` | 43 | user_devices (multi-device sync) |
| `0003_user_activity.sql` | 111 | user_activity_log + IP audit (marketing 통계 base) |
| `0004_emoji_packs.sql` | 138 | emoji_packs + emoji_items (Phase 3+ emoji pack share) |
| `0005_bot_escalations.sql` | 145 | bot_escalations + ticket flow |
| `0006_app_versions.sql` | 132 | app_versions (자동 업데이트 base) |
| `0007_friends.sql` | 144 | friends + user_activity_log ENUM 확장 (친구 관계) |

> 재 적용 시점에는 `docker compose down -v && docker compose up -d mariadb`
> (volume 삭제 → 빈 상태 → init.d 재 실행) 패턴 권장. production 환경에서는
> destructive 작업 — 데이터 손실 가능성 명시.

### 2-2. server/api/ handler 7종 chain (모두 lazy import + graceful)

`server/main.py` 안 `build_app()` 영역에서 try/except register 패턴 적용 —
모듈 부재 시 graceful skip (server 기동 영향 부재).

| handler file | endpoint | cycle |
| --- | --- | --- |
| `auth_handlers.py` | `/api/auth/*` | 22 (always-on) |
| `devices_handlers.py` | `/api/devices/*` | 43 (always-on) |
| `messages_handlers.py` | `/api/messages/*` | 60 (always-on) |
| `health_handlers.py` | `/healthz` + `/readyz` | 124 (always-on) |
| `version_handlers.py` | `/api/app/version/*` | 132 (lazy) |
| `remote_handlers.py` | `/api/remote/*` | 132 (lazy) |
| `rooms_handlers.py` | `/api/rooms/*` | 135 (lazy) |
| `friends_handlers.py` | `/api/friends/*` | 144 (lazy) |
| `bot_handlers.py` | `/api/bot/chat` | 74 (BOT_ENABLED=1 활성 시) |
| `emoji_handlers.py` | `/api/emoji/*` | 138 (always-on) |
| `emoji_moderation_handlers.py` | `/api/emoji/moderation/*` | 138 (always-on) |

### 2-3. Phase 5 i18n + app/bot/streaming chain

| module | role | dependency |
| --- | --- | --- |
| `app/i18n/` | locale resolve + catalog | 부재 (순수 Python) |
| `app/bot/streaming/chzzk_client.py` | CHZZK chat WebSocket | `websockets` (graceful) |
| `app/bot/streaming/twitch_client.py` | Twitch chat WebSocket | `websockets` (graceful) |
| `app/bot/streaming/kick_client.py` | Kick chat WebSocket | `websockets` (graceful) |
| `app/bot/streaming/youtube_client.py` | YouTube Live HTTP poll | `httpx` (graceful) |
| `app/bot/obs_websocket_client.py` | OBS Studio websocket | `websockets` (graceful) |
| `app/bot/toonation_client.py` | Toonation donation API | `httpx` (graceful) |
| `app/bot/emoji_dmca_check.py` | pHash 검사 | `Pillow` + `ImageHash` (graceful) |
| `app/bot/jailbreak_detector_ocr.py` | OCR jailbreak 탐지 | `Pillow` + `pytesseract` (graceful) |

> 모든 신규 module 은 미설치 환경에서 import-time graceful — `try: import X
> except ImportError: X = None` 패턴 + `is_available()` 반환 False 시 mock
> 폴백.

## 3. 사용자 manual `docker compose build` 의무 안내

> **Docker daemon 부재 graceful** — 본 cycle 환경 (macOS sandbox 안
> colima `/Users/.colima/default/docker.sock` 부재, Cannot connect to Docker
> daemon) 에서는 실 빌드 부재. 사용자 직접 manual 실행 의무.

### 3-1. 데모 서버 (114.207.112.73) manual 명령

```bash
# SSH 접근 후
cd ~/p2p_msg/deploy

# .env.production 존재 검증 — fcm_service_account.json + DB password 의무
ls -la secrets/fcm_service_account.json

# 빌드 (cache 갱신)
docker compose --env-file ../.env.production build --no-cache web ws

# 재 기동 (zero-downtime 패턴 권장)
docker compose --env-file ../.env.production \
  -f docker-compose.yml -f docker-compose.production.yml \
  up -d --force-recreate web ws nginx
```

### 3-2. 로컬 dev manual 명령

```bash
# Docker daemon 기동 (colima 권장)
colima start

cd deploy

# 로컬 override — mariadb + postfix 만 (web + ws = host venv 실행)
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d mariadb postfix

# 검증
docker compose logs -f mariadb | head -20
docker compose ps
```

## 4. smoke verify 의무 항목

> Docker daemon 부재 상태에서는 본 cycle 산출 = file 변경 + 사용자 manual
> 의무 명문화. 사용자 직접 실행 verify 의무 안내.

### 4-1. healthz + readyz 검증

```bash
# liveness probe — 항상 200 OK (외부 의존성 부재)
curl -fsS http://localhost:8080/healthz
# 응답: {"status":"ok"}

# readiness probe — db_pool + bot_provider + activity_tracker 검증
curl -fsS http://localhost:8080/readyz
# 응답: {"status":"ok","checks":{"db_pool":"ok","bot_provider":"absent","activity_tracker":"ok"}}
```

### 4-2. migration 적용 검증

```bash
docker compose exec mariadb mariadb -u tootalk -p"$MARIADB_PASSWORD" tootalk -e "SHOW TABLES;"
# 의무 출력 — users, email_otp, sessions, user_devices, user_activity_log,
#   user_sessions, emoji_packs, emoji_items, bot_escalations, app_versions, friends
```

### 4-3. 신규 endpoint 검증

```bash
# version handler (cycle 132)
curl -fsS http://localhost:8080/api/app/version/latest
# rooms handler (cycle 135)
curl -fsS http://localhost:8080/api/rooms
# friends handler (cycle 144) — 인증 필요 → 401 응답 = handler 활성 증거
curl -i http://localhost:8080/api/friends
```

### 4-4. log 검증

```bash
docker compose logs web | grep -E "(version_handlers|remote_handlers|rooms_handlers|friends_handlers)"
# 의무 출력 — register 성공 log 4종 (실패 시 "등록 실패 — skeleton skip" 라인)
```

## 5. mobile cycle 181 prerequisite 정합

본 docker rebuild 완료 →  `docs/operations/mobile-cycle-181-prereq.md` 안
"server endpoint → mobile client 호출 base" 항목 PASS 의무.

| prereq | 의무 endpoint | 검증 |
| --- | --- | --- |
| 인증 chain | `/api/auth/login` + `/api/auth/refresh` | 200 응답 |
| 메시지 lazy load | `/api/messages?room_id=X` | 200 + JSON list |
| 자동 업데이트 | `/api/app/version/latest?platform=android` | 200 + version JSON |
| 그룹 룸 | `/api/rooms` | 200 + list |
| 친구 검색 | `/api/friends/search?q=X` | 200 + 401 |

> cycle 152 산출 = server side actual binding base. mobile cycle 181
> 진입 시점에는 본 endpoint chain → Flutter mobile_client 호출 binding 실 작업
> 진행.

## 6. cycle 100~151 chain 반영 명문 정합 보고

- **cycle 100~117** — Phase 4 docker stack base (mariadb + postfix + web + ws + nginx + certbot) 변경 부재 (base 유지).
- **cycle 118~131** — bot escalation + RAG + jailbreak detector → server side 직접 영향 부재 (app/bot/ 하위 모듈은 web/Dockerfile COPY app 경로 자동 반영).
- **cycle 132** — 자동 업데이트 + remote_handlers + i18n + version_handlers → server/main.py lazy register chain 자동 반영.
- **cycle 133~143** — emoji moderation + Toonation + OBS websocket + bot streaming 4종 → app/bot/ 하위 + server/api/emoji_moderation_handlers.py 자동 반영. cycle 152 산출 = `websockets` + `Pillow` + `pytesseract` + `ImageHash` requirements 추가 → graceful 상태에서 production binding 전환.
- **cycle 144** — friends_handlers + 0007_friends.sql migration 자동 반영.
- **cycle 145** — bot_escalations 0005 migration + obs_websocket_client + emoji_moderation_dispatcher 자동 반영.
- **cycle 146~151** — remote coord transform + signaling rooms integration + Phase 5 i18n catalog 5 locale 자동 반영.

cycle 152 산출 = **신규 file 부재** + **기존 file 3종 갱신 만** + **사용자
manual 의무 명문화**. 다음 cycle 153~180 → mobile cycle 181 진입 prerequisite
base PASS.

마지막 갱신 — 2026-05-19 (cycle 152)
