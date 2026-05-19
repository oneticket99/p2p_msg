---
title: TooTalk SMTP 운영 가이드
owner: oneticket99
last_verified: 2026-05-19
status: active
---

# TooTalk SMTP 운영 가이드

TooTalk 메신저 (TooTalk) 회원가입 이메일 OTP 발신용 SMTP 서버 `mail.dopa.co.kr` (114.207.112.73) 일상 운영 + 장애 대응 + 자격 rotation + 발신 검증 절차 정본. cycle 129 (smtp_install.sh + ssh_exec.py + .env.smtp 자동 설치) + cycle 130 (server/config.py SMTPConfig + server/mail/smtp_client.py + .env.example) 산출물 정합.

---

## 1. 개요

### 1-1. infra 구성

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 호스트명 | `mail.dopa.co.kr` | A record → 114.207.112.73 |
| 공인 IP | 114.207.112.73 | KT 회선 고정 IP |
| OS | Rocky Linux 9.7 | minimal 설치 |
| MTA | postfix 3.5+ | TLS + SASL + opendkim milter |
| MSA | submission 587 / smtps 465 | STARTTLS + implicit TLS 병행 |
| SASL | cyrus-sasl + saslauthd | sasldb2 hash store |
| DKIM | opendkim 2.11+ | selector `mail` |
| Cert | Let's Encrypt (certbot) | RSA 2048 + 90일 자동 갱신 |
| anti-spam | DNS SPF + DKIM + DMARC | whoisdomain.kr DNS 콘솔 |

### 1-2. 도메인 + DNS

- 도메인 등록기관 — whoisdomain.kr (Toonation 사업자 명의)
- 메일 도메인 — `dopa.co.kr` (회원 OTP 발신 from `noreply@dopa.co.kr`)
- MX record — `mail.dopa.co.kr` priority 10
- SPF — `v=spf1 ip4:114.207.112.73 -all`
- DKIM — selector `mail`, RSA 2048-bit public key TXT
- DMARC — `v=DMARC1; p=quarantine; rua=mailto:dmarc@dopa.co.kr; pct=100`

### 1-3. 발신 모델

- TooTalk 서버 (aiohttp) → aiosmtplib client → mail.dopa.co.kr (submission 587, STARTTLS)
- SASL 인증 — `tootalk` user + .env.smtp `SMTP_PASSWORD`
- 일일 발신량 — Phase 1 회원가입 OTP 한정 (예상 100~1000 통/일)

### 1-4. 정합 산출물

| cycle | 산출물 | 역할 |
| --- | --- | --- |
| 129 | `tools/smtp_install.sh` | postfix + opendkim + certbot 자동 설치 |
| 129 | `tools/ssh_exec.py` | root@114.207.112.73 명령 원격 실행 + log 회수 |
| 129 | `.env.smtp` | SSH host + SASL password (gitignore `.env.*`) |
| 130 | `server/config.py` SMTPConfig | aiohttp 환경 변수 binding |
| 130 | `server/mail/smtp_client.py` | aiosmtplib 발신 client |
| 130 | `.env.example` | 자격 placeholder template |

---

## 2. 자격 관리

### 2-1. `.env.smtp` schema

```bash
# SSH 접속용 (smtp_install.sh + ssh_exec.py 정합)
SMTP_SSH_HOST=114.207.112.73
SMTP_SSH_PORT=22
SMTP_SSH_USER=root
SMTP_SSH_KEY=~/.ssh/dopa_smtp_ed25519

# SMTP 발신용 (server/mail/smtp_client.py binding)
SMTP_HOST=mail.dopa.co.kr
SMTP_PORT=587
SMTP_USER=tootalk
SMTP_PASSWORD=<placeholder — 실 값 별도 보관>
SMTP_FROM=noreply@dopa.co.kr
SMTP_STARTTLS=true
```

### 2-2. gitignore 정합

- `.gitignore` 패턴 `.env.*` + `!.env.example` 으로 격리.
- `.env.smtp` git tracking 차단 검증 — `git check-ignore -v .env.smtp` 반환 PASS.
- pre-commit hook `tools/hook_post_write_inspect.sh` 가 평문 password regex 검출 시 commit 차단.

### 2-3. SASL password rotation (3개월 권장)

```bash
# 1) 신 password 생성 (32 char URL-safe)
NEW_PWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

# 2) ssh_exec.py 로 원격 saslpasswd2 갱신
python3 tools/ssh_exec.py --cmd "echo '${NEW_PWD}' | saslpasswd2 -p -c -u dopa.co.kr tootalk"

# 3) postfix reload
python3 tools/ssh_exec.py --cmd "systemctl reload postfix"

# 4) 로컬 .env.smtp 의 SMTP_PASSWORD 갱신
sed -i.bak "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${NEW_PWD}|" .env.smtp
rm .env.smtp.bak

# 5) 발신 검증 (§3-1 swaks)
```

- rotation 시점 — 분기 1회 (3개월 주기) + 외부 노출 의심 즉시.
- 회수 절차 — 이전 password 의 60초 grace period 유지 후 sasldb2 제거.

### 2-4. SSH 키 관리

- `~/.ssh/dopa_smtp_ed25519` — ed25519 키페어 (passphrase 보호 의무).
- 공개키 `dopa_smtp_ed25519.pub` → `root@114.207.112.73:/root/.ssh/authorized_keys`.
- 키 rotation — 6개월 주기 + 운영자 변경 시 즉시.

---

## 3. 발신 검증

### 3-1. swaks 발신 test

```bash
swaks \
  --to dmarc@dopa.co.kr \
  --from noreply@dopa.co.kr \
  --server mail.dopa.co.kr \
  --port 587 \
  --tls \
  --auth-user tootalk \
  --auth-password "${SMTP_PASSWORD}" \
  --header "Subject: TooTalk SMTP smoke test $(date +%Y%m%d-%H%M%S)" \
  --body "swaks smoke test — KST $(TZ=Asia/Seoul date)"
```

- 응답 `250 2.0.0 Ok: queued as ...` PASS.
- 로컬 maillog 확인 — `python3 tools/ssh_exec.py --cmd "tail -50 /var/log/maillog"`.

### 3-2. Bizmeka anti-spam (Toonation 사내)

- 발신 대상 — `1ticket@toonation.co.kr` (사용자 메일)
- 검증 — Toonation 사내 Bizmeka 메일함 도착 + 정상 분류 (스팸함 미진입).
- 실패 시 — §4 mail-tester 진단 + §5 PTR 갱신 신청.

### 3-3. Gmail Authentication-Results 검증

- 발신 대상 — 임의 Gmail 계정.
- Gmail 안 "메시지 원본 보기" → `Authentication-Results` header 의 3 항목 PASS 의무.

```text
Authentication-Results: mx.google.com;
       dkim=pass header.i=@dopa.co.kr header.s=mail header.b=...;
       spf=pass (google.com: domain of noreply@dopa.co.kr designates 114.207.112.73 as permitted sender);
       dmarc=pass (p=QUARANTINE sp=NONE dis=NONE) header.from=dopa.co.kr
```

- `dkim=fail` → opendkim 키 동기 확인 (§6-2).
- `spf=fail` → SPF record IP 변경 확인 (§6-1).
- `dmarc=fail` → SPF + DKIM 의 alignment 점검.

### 3-4. Naver 검증

- 발신 대상 — 임의 Naver 계정.
- Naver 의 스팸 정책 보수적 → 정상 INBOX 진입 시 PASS.
- 스팸함 진입 시 — PTR (§5) + DMARC (§6-3) 강화.

---

## 4. spam score 검증 (mail-tester.com)

### 4-1. 절차

1. 브라우저 → <https://www.mail-tester.com> 접속.
2. 페이지 안 임의 1회용 주소 capture (예 `test-abc123@srv1.mail-tester.com`).
3. swaks 명령 (§3-1 base) `--to` 만 capture 주소 교체 후 발신.
4. mail-tester 페이지 "Then check your score" 클릭 → 10점 만점 score 확인.

### 4-2. 목표 + 감점 항목

- 목표 — 10/10 (Phase 1 ship 의무 기준).
- 일반 감점 항목 → 대응:
  - PTR 불일치 (KT default `tongkni.co.kr`) → §5 갱신 신청.
  - DKIM signature 누락 → §6-2 opendkim 점검.
  - SPF -all 미적용 → §6-1 SPF strict 갱신.
  - DMARC p=none → §6-3 p=quarantine 갱신.
  - HELO hostname mismatch → postfix `myhostname = mail.dopa.co.kr` 점검.

### 4-3. 정기 점검 주기

- 분기 1회 (3개월) — DNS record drift + Let's Encrypt 갱신 직후.
- DKIM key rotation 직후 (§6-2).

---

## 5. KT PTR reverse DNS 갱신 신청 — **최후 또는 skip** ([[project-dopa-demo-only]])

### 5-0. 우선순위 directive (사용자 2026-05-19 cycle 132)

본 section = **최후 또는 skip** 의 nice-to-have. 사유:

- `dopa.co.kr` / `mail.dopa.co.kr` = **데몬스트레이션 전용 도메인** + 제품화 부재 ([[project-dopa-demo-only]]).
- 실 제품 도메인 = 사용자 별개 확정 의무 (Phase 5 마무리 직전 또는 종료 후 사용자 명시 GO directive).
- 현 spam reputation = Gmail / Naver / Toonation Bizmeka 발신 PASS 의 sufficient (Authentication-Results dkim/spf/dmarc pass).
- PTR 갱신 = 제품 도메인 확정 시점 의 진행 의무. 데모 단계 의 진행 부재.

### 5-1. 현황

- KT 회선 default PTR — `114.207.112.73` → `*.tongkni.co.kr` (가비아·DOPA 등 회선 기본값).
- 목표 PTR — `114.207.112.73` → `mail.dopa.co.kr` (forward + reverse alignment) — **데모 단계 진행 부재**.
- 미갱신 시 — Gmail / Naver / mail-tester spam score 1~2점 감점 (현재 spam reputation = sufficient 의 acceptable cost).

### 5-2. 신청 channel

- KT 기업 회선 담당 → 회선 계약 사업자 (Toonation) 의 KT B2B 영업 대표 channel 문의.
- 대안 channel — KT 100 (기업) → "역방향 DNS 갱신 요청" 안내 받기.

### 5-3. 필요 서류

| 서류 | 비고 |
| --- | --- |
| 사업자등록증 사본 | Toonation 명의 |
| 회선 계약자 명의 확인 | KT 회선 계약서 |
| 도메인 소유 증명 | whoisdomain.kr 등록자 정보 (Toonation 명의) |
| PTR 갱신 요청서 | IP + 신 PTR 호스트명 명시 (`114.207.112.73 → mail.dopa.co.kr`) |

### 5-4. 갱신 후 검증

```bash
dig -x 114.207.112.73 +short
# 기대 출력: mail.dopa.co.kr.
```

- forward + reverse alignment 검증 — `dig mail.dopa.co.kr +short` = `114.207.112.73` PASS.

### 5-5. 갱신 소요

- KT 의 처리 — 영업일 3~5일 소요 (사례 기반).
- 갱신 직후 § 3 + § 4 검증 재실행 의무.

---

## 6. DNS record 운영 (whoisdomain.kr)

### 6-1. SPF

```text
TXT  dopa.co.kr  v=spf1 ip4:114.207.112.73 -all
```

- `-all` (hard fail) — Phase 1 ship 기준.
- 다중 발신 서버 추가 시 — `ip4:114.207.112.73 ip4:<신IP> -all` 갱신.
- 검증 — `dig TXT dopa.co.kr +short | grep spf`.

### 6-2. DKIM

```text
TXT  mail._domainkey.dopa.co.kr  v=DKIM1; k=rsa; p=<base64 public key>
```

- selector — `mail` (기본).
- key rotation — 1년 권장.

#### DKIM key rotation 절차

```bash
# 1) 신 selector 명 결정 (예 mail2026)
NEW_SELECTOR=mail2026

# 2) 원격 opendkim-genkey 실행
python3 tools/ssh_exec.py --cmd "cd /etc/opendkim/keys/dopa.co.kr && opendkim-genkey -b 2048 -s ${NEW_SELECTOR} -d dopa.co.kr"

# 3) public key TXT 회수
python3 tools/ssh_exec.py --cmd "cat /etc/opendkim/keys/dopa.co.kr/${NEW_SELECTOR}.txt"

# 4) whoisdomain.kr 콘솔 → ${NEW_SELECTOR}._domainkey.dopa.co.kr TXT record 추가

# 5) opendkim KeyTable + SigningTable 갱신
python3 tools/ssh_exec.py --cmd "vi /etc/opendkim/KeyTable /etc/opendkim/SigningTable"

# 6) opendkim 재시작
python3 tools/ssh_exec.py --cmd "systemctl restart opendkim postfix"

# 7) §3-3 Gmail Authentication-Results 검증
# 8) 7일 grace period 후 구 selector 제거
```

### 6-3. DMARC

```text
TXT  _dmarc.dopa.co.kr  v=DMARC1; p=quarantine; rua=mailto:dmarc@dopa.co.kr; ruf=mailto:dmarc@dopa.co.kr; pct=100; sp=quarantine; aspf=s; adkim=s
```

- `p=quarantine` (Phase 1) → 6개월 운영 안정 검증 후 `p=reject` 승격.
- `rua` 보고 메일함 — `dmarc@dopa.co.kr` 주별 1회 점검.
- aggregate 보고 파서 — 향후 cycle 안 자동화 검토.

### 6-4. MX

```text
MX   dopa.co.kr  10 mail.dopa.co.kr
```

- priority 10 단일 record (Phase 1).
- secondary MX 추가 시 — priority 20 + 별개 호스트.

---

## 7. Let's Encrypt cert 자동 갱신

### 7-1. certbot 구성

- 설치 — `dnf install certbot python3-certbot-apache` (Rocky 9.7).
- 도메인 — `mail.dopa.co.kr` (postfix smtpd_tls_cert_file 정합).
- 발급 모드 — HTTP-01 challenge (port 80 임시 개방).

### 7-2. 자동 갱신 cron

```bash
# /etc/cron.d/certbot-renew (KST 03:00 매일)
0 3 * * * root /usr/bin/certbot renew --quiet --deploy-hook "systemctl reload postfix"
```

- KST timezone 의무 — `timedatectl set-timezone Asia/Seoul` 사전 적용.
- 만료 30일 이내 갱신 시도 + 0 변경.
- 갱신 PASS 시 — deploy-hook 가 postfix reload 자동 실행.

### 7-3. 만료 알람

- `cron.d/certbot-expire-check` — 매주 월요일 08:00 KST.

```bash
0 8 * * 1 root /usr/bin/openssl x509 -enddate -noout -in /etc/letsencrypt/live/mail.dopa.co.kr/fullchain.pem | awk -F= '{print $2}' | xargs -I{} date -d {} +%s | awk -v now=$(date +%s) '{ if (($1 - now) < 2592000) print "EXPIRY ALERT mail.dopa.co.kr" }' | mail -s "[TooTalk] SMTP cert expiry" oneticket99@toonation.co.kr
```

- 만료 30일 전 메일 알람 발신.

### 7-4. 수동 갱신

```bash
python3 tools/ssh_exec.py --cmd "certbot renew --force-renewal --deploy-hook 'systemctl reload postfix'"
```

- 강제 갱신 시 — rate limit (5회/주) 회피 의무.

---

## 8. 장애 대응

### 8-1. maillog 분석

```bash
# 최근 100 row 회수
python3 tools/ssh_exec.py --cmd "tail -100 /var/log/maillog"

# 발신 실패 grep
python3 tools/ssh_exec.py --cmd "grep -E 'status=(deferred|bounced)' /var/log/maillog | tail -50"

# SASL 인증 실패 grep
python3 tools/ssh_exec.py --cmd "grep 'SASL' /var/log/maillog | tail -50"
```

- 일반 status 코드:
  - `status=sent (250 2.0.0 Ok)` — PASS
  - `status=deferred (...)` — temporary 실패 (retry 대기)
  - `status=bounced (...)` — permanent 실패 (수신측 거부)

### 8-2. queue 적체 점검

```bash
# 대기 queue 길이
python3 tools/ssh_exec.py --cmd "postqueue -p | tail -1"

# queue 상세
python3 tools/ssh_exec.py --cmd "postqueue -p | head -50"
```

- 평시 queue length = 0~5.
- 50+ 적체 시 — DNS 장애 + 수신측 차단 + DKIM milter 장애 의심.

### 8-3. queue clear (긴급)

```bash
# 전체 queue 삭제 (긴급 + 대량 spam 차단)
python3 tools/ssh_exec.py --cmd "postsuper -d ALL"

# 특정 ID 만 삭제
python3 tools/ssh_exec.py --cmd "postsuper -d <QUEUE_ID>"
```

- queue clear 직전 — `postqueue -p > /tmp/queue_backup_$(date +%Y%m%d_%H%M%S).log` 백업 의무.

### 8-4. opendkim milter 장애

```bash
# 상태 점검
python3 tools/ssh_exec.py --cmd "systemctl status opendkim"

# 재시작
python3 tools/ssh_exec.py --cmd "systemctl restart opendkim"

# postfix milter 재연결 확인
python3 tools/ssh_exec.py --cmd "grep 'milter' /var/log/maillog | tail -20"
```

- opendkim down 시 — postfix `non_smtpd_milters` timeout → 발신 전체 deferred.

### 8-5. SELinux context 복구

```bash
# SELinux denial 점검
python3 tools/ssh_exec.py --cmd "ausearch -m AVC -ts recent | tail -50"

# postfix context 복원
python3 tools/ssh_exec.py --cmd "restorecon -Rv /etc/postfix /etc/opendkim /etc/letsencrypt"

# postfix 재시작
python3 tools/ssh_exec.py --cmd "systemctl restart postfix opendkim"
```

- Rocky 9 default — SELinux enforcing → context 손상 시 발신 거부.

### 8-6. 디스크 + inode 점검

```bash
python3 tools/ssh_exec.py --cmd "df -h /var/spool/postfix"
python3 tools/ssh_exec.py --cmd "df -i /var/spool/postfix"
```

- `/var/spool/postfix` 80% 초과 시 — queue clear (§8-3) + logrotate 점검.

### 8-7. 장애 escalation

| 증상 | 1차 대응 | 2차 escalation |
| --- | --- | --- |
| swaks 응답 timeout | §8-1 maillog + §8-4 opendkim | KT 회선 + firewall 점검 |
| 인증 실패 (SASL) | §2-3 password rotation 재실행 | §8-5 SELinux context |
| Gmail spam 진입 | §4 mail-tester + §5 PTR | §6 DKIM rotation |
| cert 만료 임박 | §7-4 수동 갱신 | DNS A record + port 80 점검 |

---

## 9. 보안

### 9-1. `.env.smtp` 격리

- 저장 위치 — 저장소 root `.env.smtp` (gitignore `.env.*` 정합).
- 권한 — `chmod 600 .env.smtp` 의무.
- 백업 — 운영자 개인 password manager (1Password / bitwarden) 안 SMTP_PASSWORD 별도 저장.
- 클라우드 sync 차단 — `.env.smtp` 가 iCloud / Dropbox 등 자동 sync 대상 디렉토리 안 위치 차단.

### 9-2. git pre-commit hook 평문 자격 검출

- 정합 hook — `tools/hook_post_write_inspect.sh` (cycle 117 신설) + `tools/hook_check_bpe_token_input.sh` (cycle 121).
- regex 패턴 — `SMTP_PASSWORD=[A-Za-z0-9_\-]{16,}` + `password\s*=\s*['\"][^'\"]{12,}['\"]` 등.
- 검출 시 — commit 차단 + `.env.smtp` 격리 안내 메시지 출력.
- 검증 — placeholder commit 시 hook 통과 + 실 password 시 hook 차단 PASS 의무.

### 9-3. 외부 노출 시 즉시 rotation

- 노출 trigger:
  - 실 password git history 진입 — `git log -p --all -S "${SMTP_PASSWORD}"` 검출.
  - `.env.smtp` 의 Slack / 이메일 / GitHub Issue 첨부.
  - 운영자 노트북 분실 / 도난.
- 즉시 절차:
  1. §2-3 SASL password rotation 실행 (5분 안 완료 의무).
  2. git history 노출 시 — `git filter-repo` 로 history rewrite + force push (사용자 명시 승인 의무).
  3. 노출된 source 송신 경로 (Slack 메시지 / 이메일) 즉시 삭제.
  4. 운영자 incident 보고 — `1ticket@toonation.co.kr` 의 1시간 안 알람.

### 9-4. 회수 절차

- rotation 후 — 이전 password 의 60초 grace period 후 sasldb2 제거.
- 회수 검증 — `python3 tools/ssh_exec.py --cmd "saslpasswd2 -d -u dopa.co.kr tootalk_old"` 실행 후 swaks (구 password) FAIL 확인.

### 9-5. audit log

- 발신 audit — `/var/log/maillog` 의 30일 retention (logrotate `/etc/logrotate.d/syslog` 정합).
- 접근 audit — `/var/log/secure` 의 SSH login + sudo 기록.
- 90일 retention cap (가드레일 `feedback_db_audit_timestamp_ip_activity` 정합).

---

## 10. 참조

- 가드레일:
  - `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_smtp_demo_server.md`
  - `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_auth_email_otp_required.md`
  - `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/feedback_db_audit_timestamp_ip_activity.md`
- 산출물:
  - `tools/smtp_install.sh` — cycle 129 자동 설치
  - `tools/ssh_exec.py` — cycle 129 원격 명령 실행
  - `.env.smtp` — cycle 129 자격 binding
  - `server/config.py` SMTPConfig — cycle 130 환경 변수 binding
  - `server/mail/smtp_client.py` — cycle 130 aiosmtplib client
  - `.env.example` — cycle 130 자격 placeholder
- 정본:
  - `CLAUDE.md` §3 (7 프로세스 에이전트 호출 표) + §10-2 (루트 마크다운 신규 금지)
  - `CLAUDE_HARNESS_IMPORTANT.md` §A (M1~M7) + §K (루트 18 동결)

---

마지막 갱신: 2026-05-19 (cycle 131 SMTP 운영 가이드 신설)
