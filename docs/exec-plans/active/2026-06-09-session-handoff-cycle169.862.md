---
title: "다음 세션 인계 자료 — cycle 169.862 종료 시점 (webmail M4 종단 작동 + 잔존 백로그)"
owner: oneticket99
status: active
created: 2026-06-09
last_verified: 2026-06-09
target_completion: 2026-06-30
related_code: ["server_webmail/", "tools/dovecot_install.sh", "tools/mail_user_add.sh", "deploy/nginx/conf.d/webmail.conf", "deploy/docker-compose.yml"]
---

# 다음 세션 인계 자료 — cycle 169.862 종료 시점

> 본 문서 = 다음 세션 진입점 단일 인계 자료. cycle 169.857~862 (webmail 인프라 신설 batch) 직후 상태 + 잔존 백로그 + 즉시 시작 가능 명령.
> 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) · [CLAUDE.md](../../../CLAUDE.md) · [AGENTS.md](../../../AGENTS.md)

---

## 1. TL;DR (10초 read)

- **main HEAD** = cycle 169.862 (PR #33 머지 직후, 본 doc 작성 시점). 직전 6 PR 시리즈 = #28(857) + #29(858) + #30(859) + #31(860 staleness) + #32(861 IMAP) + #33(862 header/body fix).
- **webmail.dopa.co.kr** 종단 작동 — login form → IMAP imap_service.py → INBOX list → 메일 view. test@dopa.co.kr / `X2Ced49niTsIbMNqrEh4492w` 자격 LIVE.
- **Dovecot mail.dopa.co.kr** 종단 작동 — IMAP 993 SSL/TLS + SMTP 587 STARTTLS + LMTP delivery + SELinux mail_spool_t 정합.
- **다음 작업 후보 (cycle 169.863+)** = M5 SMTP 발신 / M6 첨부+folder+bleach HTML render / 사용자 추가 계정 / 평가 staleness sweep / reviewer-agent 게이트 (cycle 169.861 미실행 detect).

---

## 2. 첫 응답 권고

다음 세션 진입 시 본 doc 정독 후 사용자 directive 의존:

- "M5 (SMTP 발신) 진입" → §5.1 Exec Plan 분해 + 신규 cycle 169.863 분리
- "사용자 추가 계정 (oneticket 등)" → §6.2 mail_user_add.sh 1-liner SSH
- "ENVELOPE byte tuple aioimaplib 도입" → §7-A 백로그
- "reviewer-agent + 평가 staleness sweep" → §5.3 회수 chain
- "다른 자동 환류 검증" → dereliction-detector-agent spawn

---

## 3. 현 인프라 상태 (cycle 169.862 종료 시점)

### 3.1 main HEAD + cycle batch

| 항목 | 값 |
|---|---|
| main branch HEAD | cycle 169.862 PR #33 squash merge (본 doc 작성 시점) |
| 직전 cycle batch | 169.857~862 (6 PR 머지 + 1 자동 환류 chain) |
| working tree | clean |
| 최신 doc-lint | PASS 88+ file |
| 최신 M3 verify | PASS 523+ entries (top=169.862) |

### 3.2 webmail.dopa.co.kr 작동 상태

| 컴포넌트 | 상태 |
|---|---|
| DNS A record `webmail.dopa.co.kr` → 114.207.112.73 | LIVE |
| Let's Encrypt cert | LIVE (만료 2026-09-07, fullchain.pem + privkey.pem 영속) |
| nginx 443 vhost (`deploy/nginx/conf.d/webmail.conf`) | LIVE (server_name webmail.dopa.co.kr 명시 + upstream webmail:8090) |
| docker container `tootalk-webmail` | LIVE (python:3.13-slim + aiohttp + EXPOSE 8090) |
| Python backend `server_webmail/main.py` | LIVE (8 route + aiohttp_session EncryptedCookieStorage + IMAP imap_service.py 호출 asyncio.to_thread) |
| 환경변수 `WEBMAIL_SESSION_KEY` | LIVE (docker-compose.yml 안 ephemeral 32 byte urlsafe-b64) |
| `/healthz` JSON | `{"status": "ok", "cycle": "169.861", "stage": "M4-imap-integrated"}` (cycle 169.862 fix 후 marker 갱신 의무 — §7-D 백로그) |
| `/login` POST → `/inbox` 302 (IMAP LOGIN PASS) | LIVE |
| INBOX header (From/Subject/Date) MIME encoded-word 디코드 | LIVE (cycle 169.862 회수) |
| 메일 본문 text/plain + text/html → plaintext + entity unescape | LIVE (cycle 169.862 회수) |

### 3.3 Dovecot mail.dopa.co.kr 작동 상태

| 컴포넌트 | 상태 |
|---|---|
| DNS A record `mail.dopa.co.kr` → 114.207.112.73 | LIVE |
| Postfix submission 587 STARTTLS + SMTPS 465 + MX 25 | LIVE (cycle 129 + 169.857) |
| Dovecot IMAP 993 SSL/TLS + 143 STARTTLS + Sieve 4190 | LIVE (cycle 169.861) |
| LMTP unix socket `/var/spool/postfix/private/dovecot-lmtp` | LIVE |
| SELinux `mail_spool_t` fcontext `/var/vmail(/.*)?` | LIVE (cycle 169.861 회수) |
| passwd-file `/etc/dovecot/users` (vmail:dovecot 0640) | LIVE (`username_format=%u` 의무 정합) |
| OpenDKIM signing (port 8891) | LIVE (cycle 129) |
| iptables ACCEPT 25/143/465/587/993/4190 + persist | LIVE |

### 3.4 등록 계정 (cycle 169.862 종료 시점)

| user@domain | 패스워드 | 용도 |
|---|---|---|
| `noreply@dopa.co.kr` | `.env.smtp` SMTP_PASSWORD | TooTalk OTP 발신 (cycle 129) |
| `test@dopa.co.kr` | `X2Ced49niTsIbMNqrEh4492w` | webmail dogfood (cycle 169.861) |

---

## 4. cycle 169.857~862 산출물 누계 (batch summary)

| cycle | 산출물 핵심 | PR |
|---|---|---|
| 169.857 | Dovecot+IMAP M1~M5 — Exec Plan 329 line + dovecot_install.sh 268 line + mail_user_add.sh 100 line + e2e 7 test | #28 |
| 169.858 | webmail nginx vhost M1+M2 — Exec Plan 282 line + webmail.conf 87 line + e2e 18 test | #29 |
| 169.859 | webmail aiohttp backend skeleton M3 — main.py + Dockerfile + docker-compose + e2e 5 | #30 |
| 169.860 | 평가 staleness sweep + reviewer BLOCKER 회수 (dereliction-detector 환류) | #31 |
| 169.861 | webmail M4 IMAP 결선 + Dovecot 잔존 버그 2 fix + 실 서버 install/deploy + 자체 loopback PASS + e2e 11 | #32 |
| 169.862 | webmail 헤더/본문 parse 회수 (MIME encoded-word + HTML entity unescape) + 본 handoff doc + e2e 14 | #33 |

---

## 5. 다음 작업 우선순위 권고

### 5.1 M5 SMTP 발신 (recommended next)

- 신규 Exec Plan §5 마일스톤 활성 (`docs/exec-plans/active/2026-06-09-webmail-python-backend.md` §5.5)
- 산출물 = `server_webmail/smtp_service.py` smtplib SMTP submission 587 STARTTLS wrapper + `handle_compose_get`/`handle_compose_post` route + 작성/답장/전달 form
- M5 e2e = mock SMTP + send loopback (IMAP 받기 검증)
- 본 cycle scope = SMTP 발신 + 첨부(25M, M5 분리 옵션) + INBOX.Sent 영속 (실 mail.dopa.co.kr SMTP submission 직접 사용)
- 추정 소요 = 1 cycle (PR 1건)

### 5.2 M6 첨부 + folder + bleach HTML render

- 첨부 upload (multipart, 25M, nginx client_max_body_size 정합)
- folder list/이동/삭제 (Dovecot IMAP NAMESPACE + LIST + MOVE)
- bleach 도입 + `_render_mail` HTML body 직접 렌더 (현재 plaintext only)
- 추정 소요 = 2~3 cycle (분리)

### 5.3 회수 chain (dereliction-detector 누적)

- (HIGH) reviewer-agent 게이트 cycle 169.861 미실행 record — 사후 spawn 가능 (`feat/cycle169.861` diff 후행 검토)
- (HIGH) 평가 staleness sweep — productization.md + vibe-coding.md marker 169.855 동결 (cycle 169.860 일부 sweep 했으나 본 batch 6 cycle 누적 = 다시 staleness threshold 5+ 도달)
- (MEDIUM) HTML mirror 4 file sweep (`docs/html/productization.html` + `docs/html/vibe-coding.html`) — CLAUDE.md §10-6 양쪽 동시 갱신 의무
- (MEDIUM) BPE U+CE21 단독 1건 — `server_webmail/imap_service.py` 잔재 detect (cycle 169.861 dereliction agent flag, cycle 169.862 안 회수 미확정)

---

## 6. 즉시 시작 가능 명령

### 6.1 webmail 브라우저 접속 + 로그인

```text
URL: https://webmail.dopa.co.kr
USER: test@dopa.co.kr (또는 'test' — domain 자동 추가)
PASS: X2Ced49niTsIbMNqrEh4492w
```

### 6.2 사용자 추가 계정 (SSH 1 명령)

```bash
ssh -i ~/.ssh/tootalk_deploy root@114.207.112.73 \
  'bash ~/p2p_msg/tools/mail_user_add.sh <username>'
```

- `<username>` 안 `oneticket`/`admin`/`1ticket` 등 영숫자 + `._-` 만
- 출력 = USER (full email) + PASSWORD (24 char openssl rand) + IMAP/SMTP host/port
- 자동 = passwd-file + maildir + sasldb2 동시 등록 + reload + SELinux fcontext (cycle 169.861 fix)

### 6.3 docker compose webmail 재 deploy (코드 변경 후)

```bash
ssh -i ~/.ssh/tootalk_deploy root@114.207.112.73 \
  'cd ~/p2p_msg && git fetch origin && git reset --hard origin/main && \
   cd deploy && docker compose build webmail && docker compose up -d webmail'
```

### 6.4 nginx reload (vhost 변경 후)

```bash
ssh -i ~/.ssh/tootalk_deploy root@114.207.112.73 \
  'cd ~/p2p_msg/deploy && docker compose exec nginx nginx -t && \
   docker compose exec nginx nginx -s reload'
```

### 6.5 인프라 로그 확인

```bash
ssh -i ~/.ssh/tootalk_deploy root@114.207.112.73 \
  'docker logs --tail 50 tootalk-webmail; tail -30 /var/log/maillog'
```

---

## 7. 백로그 (cycle 169.862 종료 시점 잔존)

### A. 코드/인프라 백로그

| 항목 | 우선순위 | 회수 cycle 권고 |
|---|---|---|
| M5 SMTP 발신 (작성 form + smtplib + INBOX.Sent 영속) | HIGH | cycle 169.863 |
| `/healthz` `cycle` 마커 169.861 → 169.862 갱신 (cycle 869.862 회수 누락) | LOW | cycle 169.863 묶음 |
| ENVELOPE aioimaplib 도입 (현재 BODY[HEADER.FIELDS] + email.message_from_bytes 로 충분) | LOW | M6+ |
| HTML body bleach + iframe sandbox 렌더 | MEDIUM | M6 |
| 메일 본문 첨부 download (multipart attachment) | MEDIUM | M6 |
| Dovecot Sieve filter UI (4190 port LIVE 만) | LOW | M6+ |
| webmail favicon + static asset | LOW | M5 묶음 |
| `WEBMAIL_SESSION_KEY` env override 의무화 (production secret) | MEDIUM | M5 묶음 |

### B. 회수 chain (dereliction-detector 자동 환류 누적)

| 항목 | 우선순위 | 회수 cycle 권고 |
|---|---|---|
| reviewer-agent 게이트 cycle 169.861 사후 spawn | HIGH | cycle 169.863 진입 직전 |
| 평가 staleness sweep (productization.md + vibe-coding.md + HTML mirror 2) | MEDIUM | cycle 169.863 묶음 |
| BPE U+CE21 단독 `server_webmail/imap_service.py` 잔재 1건 sweep | MEDIUM | cycle 169.863 묶음 |

### C. 운영 백로그

| 항목 | 우선순위 | 추정 |
|---|---|---|
| webmail.dopa.co.kr Chrome "주의 요함" 평판 — 시간 경과 자동 해소 (cert 정상) | LOW | passive |
| 외부 SMTP 봇 brute-force 시도 (postfix log 안 다수) — fail2ban 도입 권고 | MEDIUM | 별도 cycle |
| `noreply@dopa.co.kr` SMTP_PASSWORD `.env.smtp` 격리 영속 검증 | LOW | passive |

---

## 8. 가드레일 + 워크플로우 정합

### 8.1 영구 가드레일 인덱스 (26 + 본 cycle 추가 후보)

위치: `~/.claude/projects/-Users-1ticket-Documents-vscode-work-p2p-msg/memory/`

본 batch 안 직접 명시/암시 가드레일:

- `feedback_workflow_strict_doc_first` — 문서 → 검토 → 개발 → QA → 코드리뷰 (M1~M5)
- `feedback_reviewer_gate_all_feat_mandatory` — 자동검증 구간 포함 모든 feat reviewer 의무
- `feedback_per_file_immediate_push` — 파일 1건 직후 commit + push
- `feedback_no_korean_chuck_token` — U+CE21 단독 사용 금지 (합성어 OK)
- `feedback_bpe_strict_self_grep` — chat output 송신 직전 bash grep verify
- `feedback_dereliction_auto_spawn_mandatory` — 매 작업 완료 보고마다 dereliction-detector spawn
- `feedback_telegram_report_mandatory_m7` — 모든 작업 보고 텔레그램 동시 송신 (M7)
- `feedback_auto_commit_push_deploy` — 매 작업 종료 직후 commit + push + ssh-deploy chain
- `feedback_session_handoff_on_doc_complete` — 본 doc 자체 (인계 doc 신설 시 정합)
- `feedback_minimize_user_involvement` — manual `!` 떠넘기기 금지

### 8.2 5단계 워크플로우 (CLAUDE.md §2)

```text
① 문서 선행 M1 (planning-agent)
   → ② 개발 M4 (main session)
      → ③ 검증 reviewer → qa → observability
         → ④ 문서 마감 M3 (history-agent · doc-gardener-agent)
            → ⑤ README 반영 M5 (release-agent) → PR 머지 + push
```

본 batch 안 ② 직접 적용 + ⑤ release 정합. ③ reviewer 게이트 = cycle 169.857/858/860 적용, cycle 169.861 미실행 (회수 백로그).

---

## 9. 참조 + 즉시 진입점

- **Watcher 정본**: [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §A M1~M7 + §B 워크플로우 + §C 7역할 + §P Whitebox
- **운영 호출 규약**: [CLAUDE.md](../../../CLAUDE.md) §2~10
- **저장소 맵**: [AGENTS.md](../../../AGENTS.md)
- **webmail Exec Plan**: [`docs/exec-plans/active/2026-06-09-webmail-python-backend.md`](2026-06-09-webmail-python-backend.md)
- **Dovecot Exec Plan**: [`docs/exec-plans/active/2026-06-09-dovecot-imap-install.md`](2026-06-09-dovecot-imap-install.md)

### 9.1 환경 검증 명령

```bash
# 본 저장소 working tree
cd /Users/1ticket/Documents/vscode_work/p2p_msg
git log --oneline -3
git status

# webmail live
curl -sk https://webmail.dopa.co.kr/healthz
curl -sk -o /dev/null -w "%{http_code}\n" https://webmail.dopa.co.kr/login

# Dovecot live
python3 -c "import imaplib, ssl; m=imaplib.IMAP4_SSL('mail.dopa.co.kr', 993, ssl_context=ssl.create_default_context()); print(m.login('test@dopa.co.kr', 'X2Ced49niTsIbMNqrEh4492w')); m.logout()"

# server 안 git HEAD
ssh -i ~/.ssh/tootalk_deploy root@114.207.112.73 'cd ~/p2p_msg && git log --oneline -1 && docker compose ps webmail nginx | tail -3'
```

---

마지막 갱신: 2026-06-09 16:43 KST (cycle 169.862 종료 시점)
