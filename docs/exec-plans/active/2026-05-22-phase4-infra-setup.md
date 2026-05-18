---
title: "TooTalk Phase 4 — 원격 서버 인프라 초기 구축 실행 계획"
owner: oneticket99
last_verified: 2026-05-22
status: active
authoritative_for:
  - Phase 4 진입 의 4 단계 인프라 구축 순서
  - docker compose stack 의 정본 (mariadb + smtp + web + ws + nginx + FCM)
  - .env 환경 스위칭 의 정본 (local / staging / production)
  - nginx reverse proxy 의 routing + rate limit + TLS 정본
  - Python server logging 의 KST + JSON + sensitive redact 정본
---

# Phase 4 — 원격 서버 인프라 초기 구축 실행 계획

> 본 문서 = 사용자 directive 2026-05-22 (4 item 누계) 의 본문 정본. Phase 3
> bot framework chain (사이클 65~87) 의 종결 직전 + Phase 4 진입 의 초기
> infra setup 의 4 단계 의 순서 + 의무 + 산출물 명문화.

---

## 1. 본 계획 개요

### 1.1 범위

Phase 4 = TooTalk 의 **production 진입** 단계. Phase 1~3 의 클라이언트 +
시그널링 서버 + bot framework + E2EE + 원격 데스크탑 base 완성 후 의 **원격
데모 서버 (`114.207.112.73`) 의 production-ready 인프라 구축** 의 초기 4 단계.

### 1.2 사용자 directive 누계 (2026-05-22)

1. **원격 서버 docker 환경 구축** — mariadb + SMTP + web (api) + ws + Firebase FCM
2. **.env 설정 통합** — local 환경 + 원격 환경 스위칭 가능
3. **nginx reverse proxy** — TLS + WebSocket upgrade + rate limit + routing
4. **Python server logging 추가** — KST + JSON + request_id + sensitive redact

### 1.3 본 계획 의 의무

- 4 item 순서 logical sequence (Item 1 → 2 → 3 → 4) — infra base 우선 + config 통합 + proxy frontend + log 마지막 instrumentation
- 각 item 의 commit 단위 = 1 cycle 1 commit (M5 정합)
- 각 cycle 의 직후 의 reviewer-agent + qa-agent + observability-agent 의 ③ 단계 chain 의 의무
- 사용자 의 의 manual test 의무 항목 (MANUAL_TESTS.md §2 의 의 갱신 의무)

---

## 2. Item 1 — 원격 서버 docker 환경 구축

### 2.1 컴포넌트 (6종)

| 컴포넌트 | 역할 | image / config |
|---|---|---|
| **mariadb** | 영속 DB (8 테이블 — users + email_verification + password_reset + rooms + peers + file_meta + messages + devices) | `mariadb:11` + named volume + root password env + `my.cnf utf8mb4_unicode_ci` |
| **postfix (SMTP)** | OTP 발송 + Let's Encrypt + SPF + DKIM + DMARC | `boky/postfix:latest` 또는 자체 build + opendkim sidecar |
| **web (api)** | aiohttp REST endpoint 통합 (`/api/auth/*` + `/api/devices` + `/api/messages` + `/api/bot/chat` + `/api/push/*`) | `python:3.13-slim` + `pip install -r server/requirements.txt` + asyncmy + bcrypt + aiosmtplib + httpx + firebase-admin |
| **ws (signaling)** | WebSocket signaling (room/peer routing + WebRTC SDP/ICE 중계) | web 와 동일 image + ENV `SIGNAL_SERVER_WS_PORT=8765` + endpoint `/ws` |
| **firebase-fcm** | push 알림 (Phase 2 사이클 47 push.py 의 실 binding) | google-services credentials JSON + firebase-admin SDK + Cloud Messaging API v1 enable |
| **nginx (reverse proxy)** | TLS + routing + rate limit (Item 3 의 본문) | `nginx:1.27-alpine` 또는 `caddy:2-alpine` |

### 2.2 docker-compose 구조

```text
deploy/
├── docker-compose.yml           # 6 컴포넌트 통합 stack
├── docker-compose.local.yml     # local override (mariadb + smtp 만)
├── docker-compose.production.yml # production override (모든 컴포넌트)
├── mariadb/
│   ├── my.cnf                   # utf8mb4_unicode_ci + max_connections
│   └── init/01_create_db.sql    # 8 테이블 의 base migration
├── postfix/
│   ├── main.cf                  # SPF + DKIM + DMARC 의 정합
│   └── dkim/                    # opendkim keys (gitignore)
├── web/
│   └── Dockerfile               # python:3.13-slim + requirements
├── nginx/                       # Item 3 의 본문 참조
│   ├── nginx.conf
│   └── conf.d/
└── firebase/
    └── credentials.json.example # placeholder (실 file gitignore)
```

### 2.3 networks + volumes + secrets

```yaml
networks:
  backend:                       # mariadb + postfix + firebase-fcm 의 내부 only
    driver: bridge
  public:                        # web + ws + nginx 의 외부 expose
    driver: bridge

volumes:
  mariadb_data:                  # /var/lib/mysql
  postfix_spool:                 # /var/spool/postfix
  letsencrypt:                   # TLS cert (Item 3 + Caddy 의 자동 갱신)
  firebase_creds:                # credentials JSON 의 read-only mount

secrets:
  db_root_password:              # mariadb root
  db_app_password:               # tootalk_app user
  anthropic_api_key:             # bot LLM proxy (cycle 76+)
  openai_api_key:                # OpenAI provider (cycle 84+)
  firebase_credentials:          # FCM SDK
  smtp_password:                 # postfix 의 의 outbound auth (SendGrid fallback)
```

### 2.4 commit + cycle 매핑

| cycle | 작업 | 산출물 |
|---|---|---|
| Phase 4 cycle 100 | docker-compose.yml 의 의 6 컴포넌트 stack skeleton + mariadb init + my.cnf | `deploy/docker-compose.yml` + `deploy/mariadb/` |
| cycle 101 | postfix 통합 + SPF/DKIM/DMARC + opendkim sidecar | `deploy/postfix/` + 정책 `docs/references/smtp-setup.md` 갱신 |
| cycle 102 | web + ws 통합 (aiohttp + signaling dual server 또는 single process 결정) | `deploy/web/Dockerfile` + `deploy/web/entrypoint.sh` |
| cycle 103 | firebase-admin 의 의 통합 + FCM credentials mount + push.py 의 의 실 binding | `app/notifications/fcm_client.py` + 테스트 |
| cycle 104 | nginx (Item 3 의 본문 — 별개 cycle 의 routing 의 의 진입) | `deploy/nginx/` |

### 2.5 manual test 의무 (사용자)

- [ ] 데모 서버 (`114.207.112.73`) SSH 접근 + `docker compose up -d` 의 의 6 컴포넌트 의 의 起動 확인
- [ ] `docker compose ps` 의 의 모든 container 의 의 `running` 상태 확인
- [ ] mariadb 의 의 base migration 의 의 실행 (`/docker-entrypoint-initdb.d/01_create_db.sql`)
- [ ] postfix 의 의 SPF/DKIM/DMARC 의 실 verify (`mail-tester.com` 의 의 점수 ≥ 9/10)
- [ ] FCM credentials JSON 의 실 file 의 의 production secret 의 의 mount
- [ ] Anthropic API key + OpenAI API key + DB password 의 secret 의 production 의 의 host 의 의 직접 inject

### 2.6 보안 의무

- secrets 의 git history 의 의 미포함 의 검증 (git log + GitGuardian 또는 trufflehog 의 의 scan)
- credentials 의 docker secrets 또는 systemd EnvironmentFile 의 production 의 의 우선 (env 의 평문 미사용)
- mariadb 의 external port (3306) 의 expose 부재 — backend network only
- postfix 의 submit 의 의 587 만 expose (의 의 25 의 inbound 차단 — relay 차단)
- nginx 의 80 / 443 만 host port mapping (Item 3 의 의 본문)

---

## 3. Item 2 — .env 설정 통합 + 환경 스위칭

### 3.1 파일 분류

| 파일 | 용도 | git 정합 |
|---|---|---|
| `.env.example` | 모든 키 + placeholder + 주석 (single source of truth) | **commit** (root 의 의 정합) |
| `.env` | local dev default + `ENVIRONMENT=local` | gitignore (현 정합) |
| `.env.local` | local override (개발자 personal) | gitignore |
| `.env.production` | 데모 서버 production | gitignore + 서버 host 의 직접 배치 |
| `.env.staging` | (옵션) Phase 4+ pre-prod | gitignore |

### 3.2 load 순서 (Config 클래스)

```text
1. os.environ                # 최우선 — docker secrets + systemd EnvironmentFile
2. .env.{ENVIRONMENT}        # production / staging / local
3. .env.local                # local override
4. .env                      # default fallback
5. .env.example              # key 존재 검증 only (값 사용 부재)
```

### 3.3 env 키 분류 (.env.example 의 정본)

| 분류 | 키 누계 | 비고 |
|---|---|---|
| 시그널링 | `SIGNAL_SERVER_HOST` + `SIGNAL_SERVER_WS_PORT` + `SIGNAL_SERVER_WS_SCHEME` | 현 3종 + Phase 2 wss 진입 시 cert path 추가 |
| DB | `DB_ENABLED` + `DB_HOST` + `DB_PORT` + `DB_USER` + `DB_PASSWORD` + `DB_NAME` + `DB_POOL_MIN` + `DB_POOL_MAX` | 현 8 환경 변수 |
| Auth | `OTP_TTL_SECONDS` + `OTP_RESEND_COOLDOWN_SECONDS` + `BCRYPT_ROUNDS` + `SESSION_TTL_SECONDS` | Phase 1 cycle 20 |
| SMTP | `SMTP_HOST` + `SMTP_PORT` + `SMTP_USER` + `SMTP_PASSWORD` + `SMTP_FROM` + `SMTP_TLS` + `SMTP_FALLBACK_PROVIDER` | postfix + SendGrid fallback |
| Bot LLM | `BOT_ENABLED` + `BOT_RATE_PER_MINUTE` + `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` | cycle 76 + cycle 84 |
| Push FCM | `FCM_ENABLED` + `FCM_CREDENTIALS_PATH` + `FCM_PROJECT_ID` | Phase 4 신설 (Item 1 정합) |
| 로깅 | `LOG_LEVEL` + `LOG_FORMAT` (text/json) + `LOG_TIMEZONE` (KST) | Item 4 정합 |
| **신규 Phase 4** | `ENVIRONMENT` (local/staging/production) + `APP_BASE_URL` + `FRONTEND_BASE_URL` + `REQUEST_ID_HEADER` | switch + proxy URL + Item 4 |

### 3.4 Config 변경 의무

- `app/core/config.py` + `server/config.py` (신규 또는 기존 통합)
- `Config.load()` 의 우선순위 chain 명시
- `Config.is_production()` / `is_local()` / `is_staging()` helper
- production 진입 시 의 의 sanity:
  - `DB_PASSWORD` 빈 차단
  - `ANTHROPIC_API_KEY` 의 의 `BOT_ENABLED=1` 조건부 강제
  - `SIGNAL_SERVER_WS_SCHEME` 의 의 production 의 의 `wss` 강제
  - `FCM_CREDENTIALS_PATH` 의 의 `FCM_ENABLED=1` 조건부 강제

### 3.5 commit + cycle 매핑

| cycle | 작업 |
|---|---|
| Phase 4 cycle 105 | `.env.example` 의 의 전수 key 누계 + 분류 주석 (Item 2 의 의 §3.3 정합) |
| cycle 106 | `app/core/config.py` + `server/config.py` 의 의 load 순서 chain + helper + sanity check |
| cycle 107 | `tests/app/core/test_config_switching.py` — local default + production override + staging 의 3 환경 회귀 |

### 3.6 manual test 의무

- [ ] 데모 서버 의 `.env.production` 의 의 직접 배치 + permission 600 의 의 확인
- [ ] `ENVIRONMENT=production` 의 의 `is_production()` 의 True 확인
- [ ] sanity check 의 실 환경 의 의 실행 (DB_PASSWORD 부재 시 의 의 fail-fast 검증)
- [ ] git history 의 의 `.env.production` 의 미포함 검증 (`git log -p | grep ANTHROPIC_API_KEY`)

### 3.7 보안 의무

- `.env.production` 의 git history 의 의 미포함 (이미 gitignore 의 의 정합)
- secret rotation 의 의 정책 — 분기 1회 의 의 rotation 권장
- LICENSE GPLv3 의 의 정합 — env 파일 자체 의 비공개 (라이선스 부재)

---

## 4. Item 3 — nginx reverse proxy

### 4.1 routing 표

| location | upstream | 설명 |
|---|---|---|
| `/api/auth/*` | `web:8080` | 회원가입 + OTP + 로그인 + 비번 재설정 |
| `/api/devices*` | `web:8080` | multi-device sync (Phase 2 cycle 43) |
| `/api/messages*` | `web:8080` | ChatView lazy load (cycle 60) |
| `/api/bot/chat` | `web:8080` | LLM proxy (cycle 74) |
| `/api/push/*` | `web:8080` | FCM 트리거 (Phase 4) |
| `/ws` | `ws:8765` | WebSocket signaling + `Upgrade: websocket` |
| `/health` | `web:8080` | aiohttp health-check |
| `/` (root) | static 또는 404 | fallback |

### 4.2 WebSocket upgrade 의 의 필수 directive

```nginx
location /ws {
    proxy_pass http://ws:8765;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
}
```

### 4.3 TLS 의무 (Let's Encrypt)

- **권장**: Caddy 의 의 자동 갱신 (운영 부담 절감)
- **대안**: certbot sidecar container + nginx + cron renewal
- HSTS header — `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### 4.4 rate limit zone (5종)

| zone | 적용 | 한도 |
|---|---|---|
| `api_login` | `/api/auth/login` | 분당 10 / IP (brute force 차단) |
| `api_otp` | `/api/auth/register` + `/api/auth/reset/request` | 분당 5 / IP (OTP spam 차단) |
| `api_bot` | `/api/bot/chat` | 분당 30 / IP (LLM cost 의 의 1차 방어) |
| `api_general` | 그 외 `/api/*` | 분당 120 / IP |
| `ws_connect` | `/ws` | 분당 30 connection / IP (signaling spam 차단) |

### 4.5 보안 header

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- `Content-Security-Policy` — Phase 4 frontend 결정 후 정합

### 4.6 config 파일 구조

```text
nginx/
├── nginx.conf              # 메인 (worker + events + http block)
├── conf.d/
│   ├── upstream.conf       # upstream web + ws + postfix 정의
│   ├── tootalk.conf        # server_name + location routing
│   ├── rate-limit.conf     # limit_req_zone 5종
│   └── security-headers.conf
└── ssl/                    # Let's Encrypt mount target
```

### 4.7 commit + cycle 매핑

| cycle | 작업 |
|---|---|
| Phase 4 cycle 108 | nginx.conf + upstream.conf + tootalk.conf 의 base routing |
| cycle 109 | rate-limit.conf 5 zone + security-headers.conf |
| cycle 110 | Let's Encrypt (certbot 또는 Caddy 결정) + TLS 자동 갱신 |
| cycle 111 | docker-compose.yml 의 nginx 통합 + host port 80/443 + volume mount |

### 4.8 manual test 의무

- [ ] `https://demo.toonation.io/health` 또는 `https://114.207.112.73/health` 의 의 200 응답
- [ ] `https://*/ws` 의 WebSocket handshake 의 101 응답
- [ ] `https://*/api/auth/login` 의 의 brute force 의 10회 의 11회 의 의 429 차단
- [ ] TLS 의 의 SSL Labs 의 점수 A+ (HSTS + TLS 1.3 + strong cipher)
- [ ] HTTP → HTTPS redirect 의 301 확인

### 4.9 Caddy 대안 정합

운영 부담 절감 권장 — Caddyfile 단일 파일 + 자동 TLS + WebSocket auto-upgrade:

```text
demo.toonation.io {
    handle /ws* {
        reverse_proxy ws:8765
    }
    handle /api/* {
        rate_limit /api/auth/login 10r/m
        rate_limit /api/bot/chat 30r/m
        reverse_proxy web:8080
    }
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options DENY
        X-Content-Type-Options nosniff
    }
}
```

---

## 5. Item 4 — Python server logging 강화

### 5.1 변경 표

| 항목 | 현 상태 | Phase 4 의무 |
|---|---|---|
| 형식 | `[YYYY-mm-dd H:i:s] LEVEL logger: message` (정본 §E + cycle 22) | JSON structured log + 호환 dual mode (env switch) |
| level | LOG_LEVEL env (default INFO) | 동일 + per-module override (예: `LOG_LEVEL_BOT=DEBUG`) |
| handler | StreamHandler (stdout 단일) | stdout (container) + 옵션 file rotation + 옵션 syslog |
| timezone | UTC | **KST 의무** (memory `feedback_timezone_kst`) |
| request_id | 부재 | aiohttp middleware 의 `X-Request-ID` 의 contextvars 자동 주입 |

### 5.2 모듈 구조

```text
server/logging/
├── __init__.py
├── config.py              # configure_logging(env, level) — JSON / text switch
├── middleware.py          # request_id + user_id + IP 의 의 contextvars 주입
├── formatters.py          # KSTFormatter + JsonFormatter (python-json-logger)
└── filters.py             # SensitiveFilter — API key + password + OTP redact
```

### 5.3 JSON 형식 (production)

```json
{
  "ts": "2026-05-22T14:30:00+09:00",
  "level": "INFO",
  "logger": "server.api.bot_handlers",
  "msg": "bot chat reply",
  "request_id": "01HKQX...",
  "user_id": 42,
  "method": "POST",
  "path": "/api/bot/chat",
  "status": 200,
  "duration_ms": 1240,
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-latest"
}
```

### 5.4 sensitive redact 패턴

| pattern | redact |
|---|---|
| `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` + `Bearer sk-*` | `***REDACTED***` |
| password + password_hash | `***REDACTED***` |
| OTP 6자리 숫자 | `***OTP***` |
| email local-part | `u***@example.com` (옵션 GDPR) |
| 카드번호 + 주민번호 + 전화번호 | `***REDACTED***` (feedback_db_schema_field_comments 의 민감도 정합) |

### 5.5 aiohttp middleware

```python
@web.middleware
async def logging_middleware(request, handler):
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    request["request_id"] = request_id
    request_id_ctx.set(request_id)
    user_id_ctx.set(request.get("user_id"))
    start = time.perf_counter()
    try:
        response = await handler(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        log.info(
            "request",
            extra={"method": request.method, "path": request.path,
                   "status": response.status, "duration_ms": duration_ms},
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        log.exception("request failed", extra={"method": request.method, "path": request.path})
        raise
```

### 5.6 KST Formatter (feedback_timezone_kst 정합)

```python
import logging
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

class KSTFormatter(logging.Formatter):
    def converter(self, ts):
        return datetime.fromtimestamp(ts, tz=KST).timetuple()
    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03d"
```

### 5.7 logger 분류

| logger | level | 용도 |
|---|---|---|
| `server.main` | INFO | 부트스트랩 + 종료 |
| `server.signaling` | INFO + DEBUG (envelope detail) | WebRTC SDP/ICE 중계 |
| `server.auth.*` | INFO + WARNING (brute force) | 회원가입 + OTP + 로그인 |
| `server.api.bot_handlers` | INFO + WARNING (jailbreak BLOCKED) | LLM proxy |
| `server.api.messages_handlers` | INFO | ChatView lazy load |
| `server.db.*` | WARNING (pool exhaustion) + ERROR | asyncmy SQL 오류 |
| `aiohttp.access` | INFO | request log (middleware 통합 의 의 dedup) |
| `app.bot.*` | INFO + WARNING (rate limit / jailbreak) | client-side bot framework |

### 5.8 commit + cycle 매핑

| cycle | 작업 |
|---|---|
| Phase 4 cycle 112 | `server/logging/formatters.py` (KSTFormatter + JsonFormatter) + 테스트 |
| cycle 113 | `server/logging/filters.py` (SensitiveFilter 5 패턴) + 테스트 |
| cycle 114 | `server/logging/middleware.py` (request_id + contextvars + duration_ms) + 테스트 |
| cycle 115 | `server/logging/config.py` (configure_logging) + `server/main.py` 의 통합 + 회귀 |
| cycle 116 | `app/bot/*` + `app/rtc/*` 의 의 client-side logger 의 통합 (KST + sensitive redact) |
| cycle 117 | `docs/policies/observability-baseline.md` 갱신 (Phase 4 metric/log baseline 신설) |

### 5.9 manual test 의무

- [ ] `LOG_FORMAT=json` + `ENVIRONMENT=production` 의 의 JSON log 출력 확인
- [ ] `LOG_FORMAT=text` + `LOG_TIMEZONE=KST` 의 의 KST timestamp 확인
- [ ] 의도된 의 의 `ANTHROPIC_API_KEY` 의 log 의 `***REDACTED***` 의 회귀 검증
- [ ] aiohttp middleware 의 X-Request-ID header 의 of round-trip 의 확인
- [ ] Promtail / Loki 의 integration (별개 cycle 의 observability stack)

### 5.10 Phase 4+ 의 추가 의무

- **observability stack 의 진입 base** — Promtail / Loki / Grafana + Prometheus metrics (별개 cycle 118+)
- **docker logging driver** — `json-file` + `max-size=100m` + `max-file=5`
- **alert base** — ERROR + WARNING 누적 의 의 Slack / 텔레그램 webhook (별개 cycle)
- **performance** — sync I/O 의 `aiologger` 의 의 async 평가 (별개 cycle)

---

## 6. 4 item 의 의 시퀀스 + 누적 cycle 매핑

```text
Item 1 (cycle 100~104) → Item 2 (cycle 105~107) → Item 3 (cycle 108~111) → Item 4 (cycle 112~117)
   docker stack            .env switching            nginx + TLS              logging + observability
```

**병렬 가능 항목** (memory feedback_parallel_execution_mandatory 정합):
- Item 1 의 mariadb + postfix + web + ws 의 의 4 sub-cycle 의 의 동시 진행 가능 (각각 독립 docker service)
- Item 2 의 .env.example + Config 클래스 + 테스트 의 의 3 sub-cycle 의 의 동시 진행 가능
- Item 3 의 nginx config 파일 5종 의 동시 진행 가능
- Item 4 의 formatters + filters + middleware 의 3 sub-cycle 의 의 동시 진행 가능

---

## 7. 누적 cycle 의 예상 + 의무 의 cycle 의 의 사이클

| Item | cycle 범위 | 신규 PASS 의 의 추정 | 산출물 의 file 수 |
|---|---|---:|---:|
| 1 docker stack | 100~104 (5 cycle) | ~40 (compose validate + healthcheck + migration smoke) | docker-compose.yml + mariadb/ + postfix/ + web/Dockerfile + firebase/ |
| 2 .env switching | 105~107 (3 cycle) | ~25 (Config switching) | .env.example + app/core/config.py + server/config.py + 테스트 |
| 3 nginx | 108~111 (4 cycle) | ~20 (config validate + rate limit smoke) | nginx/nginx.conf + nginx/conf.d/ × 4 |
| 4 logging | 112~117 (6 cycle) | ~50 (formatters + filters + middleware + integration) | server/logging/ × 4 + tests |
| **누계** | **100~117 (18 cycle)** | **~135 신규 PASS** | **~30 신규 파일** |

---

## 8. reviewer-agent + qa-agent 의 의 종합 검증 cycle (③ 단계 의 의 매 cycle 의 의 자동)

- 매 cycle 직후 의 reviewer-agent (M1~M7 + 보안 + 정본 정합 검토)
- 매 cycle 직후 의 qa-agent (회귀 + 5 hook + performance smoke)
- 매 5 cycle 의 의 observability-agent (logs + metrics + baseline drift)
- Phase 4 cycle 117 종료 의 의 release-agent (CI 3종 GREEN + v0.4.0-phase4-infra tag)

---

## 9. 본 계획 의 의무 (M5 + memory feedback 정합)

1. **1 cycle 1 commit + 즉시 push** (M5 + `feedback_per_file_immediate_push` + `feedback_skip_prepush_permanent_approval`)
2. **매 cycle 의 직후 의 평가 snapshot 의 의 전수 rewrite** (`feedback_assessment_full_rewrite`)
3. **HTML 6 mirror 동시 갱신** (CLAUDE.md §10-6)
4. **doc consistency hook + html mirror hook + post-write inspect hook 의 의 GREEN 의무** (`feedback_lint_before_push_guardrail`)
5. **KST timezone 의 모든 timestamp** (`feedback_timezone_kst`)
6. **GPLv3 SPDX header 의 의 모든 신규 .py 의 첫 줄** (memory `project_license_gpl`)
7. **DB schema 의 의 모든 필드 의 5요소 comment** (`feedback_db_schema_field_comments` — Item 1 의 의 mariadb init.sql 정합)
8. **병렬 작업 의무** (`feedback_parallel_execution_mandatory` — §6 의 의 sub-cycle 의 의 동시 진행)

---

## 10. 참조

- [`CLAUDE.md`](../../../CLAUDE.md) — 세션 내 서브에이전트 호출 규약
- [`CLAUDE_HARNESS_IMPORTANT.md`](../../../CLAUDE_HARNESS_IMPORTANT.md) — Watcher 정본
- [`docs/policies/bot-framework.md`](../../policies/bot-framework.md) — Phase 3 bot framework 정본 (cycle 80)
- [`docs/exec-plans/active/MANUAL_TESTS.md`](MANUAL_TESTS.md) — 사용자 manual test 항목 분리
- [`docs/exec-plans/active/2026-05-17-session-handoff.md`](2026-05-17-session-handoff.md) — 세션 인계 본문
- [`docs/references/smtp-setup.md`](../../references/smtp-setup.md) — postfix 설치 절차 (Item 1 의 의 postfix 정합)
- [`docs/references/ci-self-hosted-setup.md`](../../references/ci-self-hosted-setup.md) — self-hosted runner 등록 절차
- 가드레일 인덱스 — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md`

---

마지막 갱신: 2026-05-22 10:00 KST (Phase 4 plan 신설 — 사용자 directive 4 item 누계)
