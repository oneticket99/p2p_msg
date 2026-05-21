# TooTalk Deploy — Phase 4 Docker Stack

본 디렉토리 = Phase 4 production 진입 의 Docker Compose stack 정본. 정합 = [docs/exec-plans/active/2026-05-22-phase4-infra-setup.md §2](../docs/exec-plans/active/2026-05-22-phase4-infra-setup.md).

## 구조

```text
deploy/
├── docker-compose.yml             # 6 컴포넌트 통합 stack (base)
├── docker-compose.local.yml       # local override (mariadb + postfix 만)
├── docker-compose.production.yml  # production override (전체 + secrets)
├── README.md                      # 본 문서
├── mariadb/
│   ├── my.cnf                     # utf8mb4_unicode_ci + max_connections
│   └── init/                      # bootstrap SQL (host volume mount)
├── postfix/
│   ├── Dockerfile                 # postfix + opendkim 통합 image
│   ├── main.cf                    # SPF + DKIM + DMARC 정합
│   └── dkim/                      # opendkim keys (gitignore)
├── web/
│   └── Dockerfile                 # python:3.13-slim + server/requirements.txt
├── nginx/
│   ├── nginx.conf                 # base http + worker 설정
│   └── conf.d/                    # virtual host + rate limit zone (Item 3)
├── scripts/                       # bootstrap / migration / smoke 헬퍼
└── secrets/                       # FCM service-account.json 등 (gitignore)
```

## 6 서비스 매핑

| 서비스 | 역할 | image | 노출 포트 |
|---|---|---|---|
| `mariadb` | 영속 DB (8 + 2 신규 = 10 테이블) | `mariadb:11` | internal only |
| `postfix` | OTP 발송 + SPF/DKIM/DMARC | 자체 build | 25 / 587 |
| `web` | aiohttp REST (`/api/auth/*` + `/api/devices` + `/api/messages` + `/api/bot/chat` + `/api/push/*`) | `python:3.13-slim` | internal 8080 |
| `ws` | 시그널링 WebSocket | `python:3.13-slim` | internal 8765 |
| `nginx` | TLS + reverse proxy + rate limit | `nginx:1.27-alpine` | 80 / 443 |
| (별개) `firebase-fcm` | push 알림 (cycle 103~104 신규 의무) | google-services credentials JSON 의 외부 서비스 | n/a |

## 시작

```bash
# 1) 사전 의존성 install (cycle 100 정합) — local .venv
.venv/bin/pip install -r server/requirements.txt
# 2) .env.production 의 환경 변수 설정 — MARIADB_PASSWORD + ANTHROPIC_API_KEY 등
cp .env.example .env.production
$EDITOR .env.production
# 3) secrets 디렉토리 의 FCM service-account.json 배치 (cycle 103~104)
mkdir -p deploy/secrets
cp ~/Downloads/fcm-service-account.json deploy/secrets/fcm_service_account.json
chmod 600 deploy/secrets/fcm_service_account.json
# 4) production stack 기동
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.production.yml --env-file .env up -d
# 5) DB migration 확인
docker compose exec mariadb mariadb -u tootalk -p tootalk -e "SHOW TABLES;"
```

## 보안 의무

1. `.env*` + `secrets/` 디렉토리 = git ignore 의무 (root `.gitignore` 정합).
2. `MARIADB_ROOT_PASSWORD` + `MARIADB_PASSWORD` + `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` + `FCM_*` = 절대 평문 commit 금지.
3. `postfix/dkim/` 의 private key = gitignore + chmod 600.
4. `letsencrypt/` 의 TLS 인증서 = volume mount 만 (image 외부).
5. `tootalk-internal` 네트워크 = nginx 외 의 모든 service 통신 격리.

## Bot LLM provider 설정 (cycle 169.210 사용자 directive — OpenAI 우선)

투네이션 고객센터 봇 + 기타 LLM 응답 chain 활성 의무.

### provider 우선순위 (server/main.py)

1. **OpenAI** (`OPENAI_API_KEY` 설정 시점) — 사용자 directive 우선 GO
2. **Anthropic** (`ANTHROPIC_API_KEY` 설정 + OpenAI 부재 시점) — fallback
3. **Mock** (모두 부재 시점) — deterministic echo (개발 전용, production 안 실 답변 부재)

### 환경 변수 설정 chain

```bash
# 1) .env.production 안 OPENAI_API_KEY 직접 입력
echo "OPENAI_API_KEY=sk-..." >> .env.production
# 2) docker compose stack 재기동 (env 반영)
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.production.yml --env-file .env up -d --force-recreate server
# 3) provider 활성 verify
docker compose logs server | grep "Bot LLM provider"
# expected: "Bot LLM provider = OpenAIProvider (OPENAI_API_KEY 활성, 사용자 directive cycle 169.210)"
```

### bot smoke test (HTTP 401 차단 후 사용자 manual)

cycle 169.228 `self._session_token` chain 회수 직후 manual verify 의무:

1. TooTalk client 실행 → 로그인
2. sidebar 안 "투네이션 고객센터" entry click
3. 질문 입력 (예: "후원 이용 방법") + Enter
4. 200 응답 retain 확인 (이전 cycle 169.228 fix 직전 = HTTP 401 차단)

응답 부재 시점 server 로그 inspect:

```bash
docker compose logs server | grep -E "Bot LLM|HTTP 401|provider"
```

## 참조

- [Phase 4 infra setup plan](../docs/exec-plans/active/2026-05-22-phase4-infra-setup.md)
- [bot framework 정책](../docs/policies/bot-framework.md)
- [DB schema 정본](../server/db/migrations/)
- SMTP 데모 서버 memory — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_smtp_demo_server.md` (local 자격 memory)
