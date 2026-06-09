---
title: "webmail.dopa.co.kr Python 웹메일 backend — aiohttp + IMAP + SMTP + nginx 서브도메인 vhost"
owner: oneticket99
status: draft
created: 2026-06-09
last_verified: 2026-06-09
target_completion: 2026-06-16
related_code: ["deploy/nginx/conf.d/webmail.conf", "deploy/docker-compose.yml", "server_webmail/", "tools/dovecot_install.sh", "tools/mail_user_add.sh"]
---

# webmail.dopa.co.kr Python 웹메일 backend

> 정본 정합: [CLAUDE_HARNESS_IMPORTANT.md §B 5단계 워크플로우](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§C 7역할](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§D Exec Plans](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§A M1~M7](../../../CLAUDE_HARNESS_IMPORTANT.md)
> 운영: [CLAUDE.md §2 워크플로우](../../../CLAUDE.md) · 저장소 맵: [AGENTS.md](../../../AGENTS.md)
> 본 문서는 실행/검증/결정 기록 문서다. TODO 목록이 아니다. ② 개발 단계는 main session 후속 수행, 본 planning 산출물 = M1 doc-first.
> directive 출처: 사용자 "이메일을 웹페이지에서 볼 수 있게끔 웹페이지화" + "php로 작업하지말고 python 웹페이지로 만들어 통일성이 없어" + "webmail.dopa.co.kr 서브도메인 신설" + "nginx 버추얼 호스트 만들어야 할꺼야"

---

## 0. 핵심 권고 요약

### 0.1 사용자 선택 (확정)

- **언어**: Python (PHP 거부 — TooTalk 정합 의무, 기존 server/ aiohttp stack 통일)
- **URL**: `webmail.dopa.co.kr` 서브도메인 신설 (mail.dopa.co.kr 와 분리)
- **의존성**: cycle 169.857 Dovecot+IMAP 활성 후 (G-final SSH 수동 완료)

### 0.2 기술 스택

- backend = **aiohttp** (server/ 와 동일 stack, 통일성 정합)
- IMAP = **imaplib** (stdlib, Dovecot 통신)
- SMTP = **smtplib** (stdlib, Postfix submission 587 통신)
- UI = **Jinja2** + **HTMX** (SPA 회피, server-side render 단순성)
- 세션 = aiohttp_session + secure cookie (CSRF token)
- 비밀번호 보관 = 부재 (사용자 로그인 시 세션 안 IMAP/SMTP password 만 보관, logout 시 폐기)

### 0.3 nginx vhost = 본 cycle (169.858) scope

- `deploy/nginx/conf.d/webmail.conf` 신설 — server_name webmail.dopa.co.kr 별도 server block
- TLS = `/etc/letsencrypt/live/webmail.dopa.co.kr/` (별도 cert, certbot --standalone 또는 webroot)
- upstream = `webmail:8090` (docker compose service, M3 에서 add)
- 본 cycle 안 nginx vhost 만 완결 — Python backend 코드는 M3+ 후속 cycle

### 0.4 마일스톤 분해

| M | scope | 본 cycle? |
|---|---|---|
| M1 | Exec Plan (본 문서) | ✅ 본 cycle 169.858 |
| M2 | nginx vhost `deploy/nginx/conf.d/webmail.conf` | ✅ 본 cycle 169.858 |
| M3 | docker-compose webmail 서비스 + Python backend skeleton | 후속 cycle 169.859 |
| M4 | IMAP 메일 list / read / 검색 | 후속 cycle 169.860 |
| M5 | SMTP 발신 (작성/답장/전달) | 후속 cycle 169.861 |
| M6 | 첨부 / 폴더 / sieve filter UI | 후속 cycle 169.862+ |
| G-final | DNS A + Let's Encrypt 발급 + nginx reload + 사용자 visual ack | 사용자 SSH |

---

## 1. 개요

### 1.1 목적

`mail.dopa.co.kr` Dovecot+IMAP(cycle 169.857) 이 활성된 후, 외부 사용자 브라우저에서 메일 송수신을 수행할 수 있는 웹 client 를 제공한다. 별도 Apple Mail / Thunderbird IMAP client 설치 없이 브라우저만으로 메일 접근.

### 1.2 비-목적

- PHP webmail (Roundcube / SnappyMail / Cypht) — 사용자 directive 거부, 통일성 의무
- Calendar / Contacts / CalDAV (Phase 2+ 백로그)
- Mobile push notification (PWA service worker, Phase 2+)
- Multi-account dashboard (단일 dopa.co.kr 도메인 정합)

### 1.3 범위

- 신규: `deploy/nginx/conf.d/webmail.conf` + `server_webmail/` Python module + `deploy/docker-compose.yml` webmail 서비스 add
- 변경: 없음 (Dovecot config 무변경, Postfix 무변경)
- 본 cycle 169.858 한정 = nginx vhost + Exec Plan 만

---

## 2. 현재 상태

### 2.1 Dovecot+IMAP 상태 (cycle 169.857 dependency)

- mail.dopa.co.kr 호스트 안 Dovecot 설치 완료 (SSH G-final 수동 후 활성)
- IMAP 993 SSL/TLS + 143 STARTTLS + LMTP 통합 + passwd-file backend
- 계정 추가 = `bash /root/mail_user_add.sh <user>` — passwd-file + maildir + sasldb2 동시 등록

### 2.2 nginx 현 상태

- `deploy/nginx/conf.d/tootalk.conf` — server_name `_` (catch-all default)
- 443 SSL termination + reverse proxy to `web:8080` (REST) + `ws:8765` (signaling)
- Let's Encrypt cert path = `/etc/letsencrypt/live/tootalk.demo/` (production 환경 변수 정합)

### 2.3 도메인 / DNS 상태

- `dopa.co.kr` zone — 사용자 whoisdomain.kr manual 등록
- 기존 record = A `mail.dopa.co.kr` → 114.207.112.73
- 신규 의무 record = A `webmail.dopa.co.kr` → 114.207.112.73 (G-final 사용자 manual)

---

## 3. 설계 — nginx vhost (M2)

### 3.1 server block 구조

- **HTTP (80)** — Let's Encrypt webroot challenge + 443 redirect (tootalk.conf 의 HTTP 블록 재사용, server_name `_` catch-all 이 처리)
- **HTTPS (443)** — `server_name webmail.dopa.co.kr;` 추가 server block (tootalk.conf 의 `_` 보다 명시적 server_name 매치 우선)

### 3.2 TLS

- cert path = `/etc/letsencrypt/live/webmail.dopa.co.kr/fullchain.pem`
- key path = `/etc/letsencrypt/live/webmail.dopa.co.kr/privkey.pem`
- 발급 명령 (G-final 사용자 SSH 수동):

  ```bash
  certbot certonly --standalone --non-interactive --agree-tos \
    --email postmaster@dopa.co.kr -d webmail.dopa.co.kr
  ```

- 또는 webroot 방식 (기존 nginx 무중단):

  ```bash
  certbot certonly --webroot -w /var/www/certbot \
    --email postmaster@dopa.co.kr -d webmail.dopa.co.kr
  ```

### 3.3 reverse proxy

- upstream = `webmail:8090` (docker compose service, M3 에서 add)
- 본 cycle 안 backend 부재 시 nginx config 만 존재 → reload 후 504 응답 (M3 완료 후 200)
- 본 cycle nginx vhost = forward-looking infrastructure, 실 routing 미동작 정상

### 3.4 보안 header

tootalk.conf 와 동일 5종 + 메일 HTML 안 이미지 표시 정합 CSP 완화:

- `Strict-Transport-Security` HSTS
- `X-Frame-Options "SAMEORIGIN"`
- `X-Content-Type-Options "nosniff"`
- `Referrer-Policy "strict-origin-when-cross-origin"`
- `Content-Security-Policy "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"`
  - HTMX 인라인 script 정합 + 메일 본문 HTML 외부 이미지 표시 (img-src https:)

### 3.5 location 단순화

본 cycle = SPA 부재 server-side render 정합으로 location 4종만:

- `/` — 모든 traffic 을 webmail backend forward (SPA pattern fallback 부재)
- `/static/` — 정적 자산 (CSS/JS/icon) alias `/usr/share/nginx/html/webmail-static/`
- `/healthz` — health check, access_log off
- `/api/` — 향후 REST API 분리 (M4+, 현재는 단순 forward)

### 3.6 client_max_body_size

- 첨부 upload 정합 = 25M (메일 첨부 표준 한도)
- tootalk.conf 의 file upload 100M 보다 낮음 (메일 첨부 사용자 기대 정합)

### 3.7 proxy timeout

- IMAP 검색 / 대용량 본문 load 정합 = 60s (tootalk.conf 와 동일)
- WebSocket 부재 시점 (현 cycle) — keep_alive 불필요

---

## 4. M2 산출물 = `deploy/nginx/conf.d/webmail.conf`

**위치**: `deploy/nginx/conf.d/webmail.conf` (신규)

**구성 (실측 87 line)**:

- HTTP 블록 부재 (기존 tootalk.conf 의 `_` HTTP server block 이 ACME challenge + redirect 모두 처리)
- HTTPS 443 server block 1개 — server_name `webmail.dopa.co.kr;`
- TLS cert path = webmail 별도
- proxy header 6종 (tootalk.conf 정합)
- location 4종 (3.5 정합)

**검증**:

- `nginx -t` syntax PASS
- include path 정합 (`/etc/nginx/conf.d/webmail.conf` mount 확인)
- 본 cycle 단계 시점 = `webmail:8090` upstream 부재 OK (forward-looking)

---

## 5. M1~M6 마일스톤 + 본 cycle scope

### 5.1 M1 — Exec Plan (본 문서) [완료]

### 5.2 M2 — `deploy/nginx/conf.d/webmail.conf` [본 cycle]

산출물 = nginx vhost file. M3 backend skeleton 가 아직 부재해도 nginx 의 conf parse + reload 는 통과 (upstream resolve 실패 시 502 가 정상 응답).

### 5.3 M3 — docker-compose webmail 서비스 + Python backend skeleton [후속 cycle 169.859]

- `deploy/docker-compose.yml` `webmail` 서비스 add
- `server_webmail/` directory 신설 — aiohttp app skeleton
- `webmail:8090` listen
- /healthz endpoint 200 반환
- 로그인 화면 (Jinja2 template)

### 5.4 M4 — IMAP 메일 list / read / 검색 [cycle 169.860]

- imaplib 연결 + LOGIN (사용자 IMAP 자격) + 세션 안 보관
- INBOX list 표시 (200 통 paginate)
- 메일 본문 read (HTML / plaintext 분기)
- 검색 (FROM / TO / SUBJECT / BODY)

### 5.5 M5 — SMTP 발신 [cycle 169.861]

- smtplib SMTP submission 587 STARTTLS
- 작성 / 답장 / 전달 form
- 첨부 (multipart, 25M 한도)
- 발신 후 INBOX.Sent 영속

### 5.6 M6 — 첨부 / 폴더 / sieve [cycle 169.862+]

- 폴더 list / 이동 / 삭제
- sieve filter UI (Dovecot Pigeonhole 통합)
- 검색 인덱스 (옵션)

### G-final — 사용자 SSH 수동 + visual ack

- DNS A record `webmail.dopa.co.kr → 114.207.112.73` 등록
- Let's Encrypt cert 발급 (certbot certonly)
- nginx reload + docker compose up -d webmail
- 브라우저 접속 + 로그인 + 메일 list / read / send visual ack

---

## 6. ③ 검증 게이트 (reviewer→qa→observability)

- **reviewer-agent**: nginx vhost file diff + Exec Plan 검토. server_name 정합 + TLS cert path 정합 + CSP 정합 + proxy header 정합.
- **qa-agent**: `nginx -t` 명령 syntax 검증 (docker run nginx 컨테이너 mount). `nginx -T` configtest dump.
- **observability-agent**: 본 cycle 신규 로그 부재 (backend 미존재). M3+ 에서 access_log / error_log 패턴 정합.

---

## 7. G-final 사용자 게이트 (SSH 수동, 본 cycle 외)

본 cycle 169.858 = nginx vhost + Exec Plan 만. 실 활성은 M3 docker-compose + Python backend 가 완성된 후속 cycle 마지막 G-final.

```bash
# 1. DNS A record 등록 (사용자 whoisdomain.kr manual)
#    Type=A · Name=webmail · Value=114.207.112.73

# 2. Let's Encrypt cert 발급 (포트 80 점유 service 사전 정지)
ssh root@114.207.112.73 'systemctl stop nginx httpd 2>/dev/null; \
  certbot certonly --standalone --non-interactive --agree-tos \
    --email postmaster@dopa.co.kr -d webmail.dopa.co.kr'

# 3. docker compose 재기동 (nginx + webmail service 추가)
ssh root@114.207.112.73 'cd ~/p2p_msg/deploy && \
  docker compose up -d nginx webmail && \
  curl -sk -o /dev/null -w "webmail/healthz=%{http_code}\n" https://webmail.dopa.co.kr/healthz'

# 4. 브라우저 접속 + 로그인 검증
#    https://webmail.dopa.co.kr/ → login form → IMAP 자격 입력 → INBOX 표시
```

---

## 8. 리스크 + 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| cycle 169.857 Dovecot G-final 미완료 시 webmail backend 부재 | webmail 로그인 실패 (IMAP 연결 부재) | 본 cycle 169.858 = nginx vhost 만, backend 부재 OK (forward-looking infrastructure) |
| webmail backend 부재 시 nginx 502 응답 | 사용자 혼란 | 본 cycle 직후 사용자 브라우저 접속 부재 — M3 후 G-final 시점에 함께 활성 |
| Let's Encrypt rate limit (week 5회) | cert 재발급 차단 | webmail.dopa.co.kr cert 1회만 발급 + auto-renew 정합 |
| CSP 안 HTMX inline script 'unsafe-inline' = XSS 표면 | 메일 본문 XSS 공격 | bleach 또는 lxml HTML sanitize (M3 backend 책임), nginx CSP 는 1차 방어 |
| nginx server_name `_` vs `webmail.dopa.co.kr` 매치 우선순위 | webmail traffic 이 tootalk catch-all 로 흘러감 | 명시 server_name 매치가 catch-all `_` 보다 우선 (nginx 표준 동작) |

---

## 9. 산출물 인벤토리 (commit 단위)

| commit | 파일 | 단계 |
|---|---|---|
| 1 | `docs/exec-plans/active/2026-06-09-webmail-python-backend.md` (본 문서) | M1 |
| 2 | `deploy/nginx/conf.d/webmail.conf` | M2 |
| 3 | README/History prepend | M2/M3 의무 |

> 본 cycle 169.858 = 3 commit 분리 후 단일 PR. M3+ 후속 cycle 분리.

---

마지막 갱신: 2026-06-09 (M1 doc-first 신설, nginx vhost M2 진입 직전)
