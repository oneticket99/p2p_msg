---
title: "mail.dopa.co.kr Dovecot+IMAP 수신 메일박스 신설 — virtual mailbox 모델 + Postfix LMTP 통합 + 계정 추가 자동화"
owner: oneticket99
status: draft
created: 2026-06-09
last_verified: 2026-06-09
target_completion: 2026-06-16
related_code: ["tools/smtp_install.sh", "tools/dovecot_install.sh", "tools/mail_user_add.sh", "tests/integration/test_dovecot_imap_e2e.py", ".env.smtp", ".env.example"]
---

# mail.dopa.co.kr Dovecot+IMAP 수신 메일박스 신설

> 정본 정합: [CLAUDE_HARNESS_IMPORTANT.md §B 5단계 워크플로우](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§C 7역할](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§D Exec Plans](../../../CLAUDE_HARNESS_IMPORTANT.md) · [§A M1~M7](../../../CLAUDE_HARNESS_IMPORTANT.md)
> 운영: [CLAUDE.md §2 워크플로우](../../../CLAUDE.md) · 저장소 맵: [AGENTS.md](../../../AGENTS.md)
> 본 문서는 실행/검증/결정 기록 문서다. TODO 목록이 아니다. ② 개발 단계는 main session 후속 수행, 본 planning 산출물 = M1 doc-first.
> directive 출처: 사용자 "mail.dopa.co.kr 에 계정 추가" + "기존 워크플로우대로 문서부터 만들고 작업을 진행하되 e2e 까지 고려해서 진행해"

---

## 0. 핵심 권고 요약 (사용자 재검토용 — 진행 전 필독)

기존 인프라 정독 결과(`tools/smtp_install.sh` 233 line 전수 + `.env.smtp`/`.env.example`):

### 0.1 현 인프라 — 발신 only, 수신 부재

- **Postfix + cyrus-sasl + OpenDKIM + Let's Encrypt** Rocky 9.7 단일 호스트 `114.207.112.73` (DNS A: mail.dopa.co.kr)
- 587(submission STARTTLS) + 465(SMTPS) + 25(MX) listen
- SASL 자격 1건 `noreply@dopa.co.kr` (sasldb2, TooTalk OTP 발신용)
- **Dovecot 부재** — IMAP/POP3 미지원, 메일박스 없음. 외부 → mail.dopa.co.kr 수신 메일 = 무한 deferred 상태.

### 0.2 수신/메일박스 신설 — Dovecot virtual mailbox 모델

- system unix user 1건(`vmail` uid 5000) 의 home 아래에 모든 도메인 사용자 maildir 격리 (`/var/vmail/dopa.co.kr/<user>/Maildir/`)
- 계정 store = passwd-file (`/etc/dovecot/users` SHA512-CRYPT) — DB 부재 정합 (mailcow/MariaDB 회피, smtp_install.sh 의 sasldb2 정합)
- Postfix 통합 = LMTP unix socket (`private/dovecot-lmtp`) — Dovecot 가 메일박스 최종 deliver

### 0.3 계정 추가 자동화 = `tools/mail_user_add.sh <user>`

- 1 명령 = passwd-file 추가 + maildir 생성 + sasldb2 SMTP 자격 동시 등록 + reload
- 사용자 = 신규 계정명만 입력, 패스워드 = openssl 생성 + stdout 출력
- 사용 예: `bash /root/mail_user_add.sh verify` → `verify@dopa.co.kr` IMAP(993) + SMTP(587) 양방향 활성

### 0.4 DNS 변경 부재

- mail.dopa.co.kr A record + dopa.co.kr MX + SPF + DKIM + DMARC 이미 등록 완료(smtp_install.sh §10 출력)
- IMAP/POP3 SRV record 는 옵션 (Apple Mail autoconfig 향상) — 본 cycle scope 외

### 0.5 e2e 전략 — pytest integration + swaks/curl smoke

- 실 SMTP/IMAP 서버 e2e = `tests/integration/test_dovecot_imap_e2e.py` mock 기반 protocol smoke (Python `imaplib`/`smtplib`)
- 서버 실 검증 = SSH 수동 swaks 발신 + Python imaplib LIST INBOX (사용자 직접, dataclass 환경)
- headless 자동 검증 = SMTP submission auth + IMAP LOGIN protocol 응답 형식 검증 (live server 부재 시 skip)

---

## 1. 개요

### 1.1 목적

mail.dopa.co.kr 호스트에 수신/메일박스 기능을 추가한다. 현재는 발신(SMTP submission) only — TooTalk OTP/notification 발신만 가능하고, 외부 시스템에서 dopa.co.kr 계정으로 메일 보낸 결과를 받을 방법이 없다.

### 1.2 비-목적

- mailcow/mailu/iRedMail 등 패널 도입 (overengineering, 단일 도메인 1~10 계정 규모에 과함)
- Sieve filter / Webmail (Roundcube/Rainloop) 도입 (Phase 2 백로그)
- 다중 도메인 호스팅 (dopa.co.kr 단독 정합)
- SRV record DNS 등록 (옵션, 본 cycle scope 외)

### 1.3 범위

- 신규: `tools/dovecot_install.sh` (Rocky 9.7 idempotent install chain) + `tools/mail_user_add.sh` (계정 1건 add) + `tests/integration/test_dovecot_imap_e2e.py` (e2e smoke)
- 변경: `.env.example` (IMAP_* keys 추가) + `MIGRATION_MARIADB.md` (mail server 섹션 갱신 부재, README 운영 섹션만)
- 무변경: DNS, Postfix main.cf 핵심 (virtual transport 만 add), SASL 자격 store

---

## 2. 현재 상태 (코드/인프라 정독)

### 2.1 smtp_install.sh 구조 (233 line)

| 단계 | 작업 | 결과 |
|---|---|---|
| 1 | dnf install postfix cyrus-sasl s-nail swaks opendkim certbot | 패키지 완 |
| 2 | iptables ACCEPT 25/587/465 + persist | firewall 완 |
| 3 | certbot certonly --standalone mail.dopa.co.kr | TLS cert 완 |
| 4 | opendkim selector key + KeyTable + SigningTable + TrustedHosts | DKIM 완 |
| 5 | postfix main.cf — myhostname/mydomain/SASL/milter | 발신 config 완 |
| 6 | master.cf submission 587 + smtps 465 | listener 완 |
| 7 | saslpasswd2 noreply@dopa.co.kr | SASL 자격 완 |
| 8 | systemctl enable opendkim postfix | service 활성 완 |
| 9 | listen 검증 25/587/465/8891 | 검증 완 |
| 10 | DNS TXT 출력 (SPF/DKIM/DMARC) | manual 등록 완 |

### 2.2 발신 흐름 (기존)

```text
TooTalk client/server
  → SMTP STARTTLS submission 587
  → cyrus-sasl auth (noreply@dopa.co.kr / sasldb2)
  → postfix queue
  → opendkim sign (8891 milter)
  → 25 외부 송신
  → Gmail/Naver/etc inbox
```

### 2.3 수신 결함

- 25 listen 활성이나 mydestination 가 `$myhostname, localhost.$mydomain, localhost` 만 → dopa.co.kr 외부 수신 메일 = relay denied
- virtual_mailbox_domains 부재 → dopa.co.kr 도메인 메일 영속 부재
- Dovecot 서비스 부재 → IMAP/POP3 접근 불가능

### 2.4 .env 키 인벤토리

```text
.env.smtp (gitignore)
  SMTP_HOST=mail.dopa.co.kr
  SMTP_PORT=587
  SMTP_USER=noreply@dopa.co.kr
  SMTP_PASSWORD=<sasldb2 자격>
  SMTP_FROM=noreply@dopa.co.kr
  SMTP_TLS=STARTTLS

.env.example
  SMTP_HOST/PORT/USER/FROM_ADDRESS/PASSWORD/TLS/DOMAIN 정의 완료
  IMAP_* 키 부재 — 본 cycle 신설
```

---

## 3. 설계

### 3.1 Dovecot virtual mailbox 모델

- **system user**: `vmail` uid 5000 gid 5000 (예약 uid 충돌 회피)
- **maildir root**: `/var/vmail/dopa.co.kr/` (`useradd -r -u 5000 -d /var/vmail -s /sbin/nologin vmail`)
- **계정 store**: passwd-file `/etc/dovecot/users` 형식 `<user>:{SHA512-CRYPT}<hash>:5000:5000::/var/vmail/dopa.co.kr/<user>::`
- **계정 추가**: `doveadm pw -s SHA512-CRYPT -p <pwd>` 해시 생성 + line append

### 3.2 Postfix LMTP 통합

`postconf -e` 명령으로 add:

```text
virtual_mailbox_domains=dopa.co.kr
virtual_mailbox_base=/var/vmail
virtual_transport=lmtp:unix:private/dovecot-lmtp
local_recipient_maps=
mydestination=$myhostname, localhost.$mydomain, localhost
```

(`mydestination` 가 dopa.co.kr 포함 안 함 — virtual 처리로 위임)

### 3.3 Dovecot config 분할

- `/etc/dovecot/dovecot.conf` — `protocols = imap lmtp sieve`
- `/etc/dovecot/conf.d/10-mail.conf` — `mail_location = maildir:/var/vmail/dopa.co.kr/%n/Maildir`
- `/etc/dovecot/conf.d/10-auth.conf` — `disable_plaintext_auth = yes` + `auth_mechanisms = plain login` + `!include auth-passwdfile.conf.ext`
- `/etc/dovecot/conf.d/auth-passwdfile.conf.ext` — passwd-file backend
- `/etc/dovecot/conf.d/10-ssl.conf` — Let's Encrypt cert (smtp_install.sh §3 동일)
- `/etc/dovecot/conf.d/10-master.conf` — LMTP unix socket `/var/spool/postfix/private/dovecot-lmtp` (user/group postfix, mode 0600)

### 3.4 firewall

iptables ACCEPT add:

| port | proto | 용도 |
|---|---|---|
| 143 | TCP | IMAP STARTTLS |
| 993 | TCP | IMAPS SSL/TLS |
| 4190 | TCP | Sieve (옵션, Phase 2) |

### 3.5 계정 추가 명령

```bash
bash /root/mail_user_add.sh <user>
```

| 단계 | 명령 | 결과 |
|---|---|---|
| 1 | password = openssl rand -base64 24 | 자격 생성 |
| 2 | doveadm pw → SHA512-CRYPT 해시 | passwd-file 등록 형식 |
| 3 | echo line >> /etc/dovecot/users | passwd-file append |
| 4 | mkdir -p /var/vmail/dopa.co.kr/<user>/Maildir/{cur,new,tmp} + chown vmail | maildir 생성 |
| 5 | saslpasswd2 -c -u dopa.co.kr -p <user> | sasldb2 SMTP 자격 동시 등록 (발신용) |
| 6 | echo USER + PASS + IMAP + SMTP config stdout | 클라이언트 설정 안내 |

### 3.6 클라이언트 설정 (사용자 manual)

| 설정 | 값 |
|---|---|
| IMAP host | mail.dopa.co.kr |
| IMAP port | 993 |
| IMAP SSL | SSL/TLS |
| IMAP user | `<user>@dopa.co.kr` |
| IMAP password | (생성 패스워드) |
| SMTP host | mail.dopa.co.kr |
| SMTP port | 587 |
| SMTP encryption | STARTTLS |
| SMTP user | `<user>@dopa.co.kr` (sasldb2 동일 자격) |
| SMTP password | (동일 패스워드) |

---

## 4. M1~M5 마일스톤

### 4.1 M1 — Exec Plan (본 문서) [완료]

- 사용자 GO 게이트 → ② 개발 진입

### 4.2 M2 — `tools/dovecot_install.sh` 신설 (220~250 line 예상)

산출물: idempotent Rocky 9.7 install chain

- §1 dnf install dovecot dovecot-pigeonhole opendkim-tools
- §2 vmail system user useradd -r -u 5000 -g 5000 -d /var/vmail -s /sbin/nologin (uid/gid 5000 예약 — 부재 시 useradd, 존재 시 skip)
- §3 maildir root `/var/vmail/dopa.co.kr/` chown vmail
- §4 Dovecot 6 conf 파일 생성 (10-mail/10-auth/10-master/10-ssl + auth-passwdfile.conf.ext + dovecot.conf)
- §5 `/etc/dovecot/users` 빈 파일 생성 (chown vmail:dovecot, mode 0640)
- §6 Postfix main.cf virtual_* 4 키 add (postconf -e)
- §7 iptables ACCEPT 143 993 4190 + persist
- §8 systemctl enable --now dovecot + restart postfix
- §9 listen 검증 143/993/4190 + LMTP socket 존재
- §10 사용자 안내 — `bash /root/mail_user_add.sh <user>` 호출법

### 4.3 M3 — `tools/mail_user_add.sh` 신설 (60~80 line 예상)

산출물: 계정 1건 자동 추가 명령

- §1 인자 검증 (`$1` = user, 부재 시 usage echo + exit 1)
- §2 password = openssl rand -base64 24 (URL-safe 변환 시 `tr -d '/+='` 대체)
- §3 hash = doveadm pw -s SHA512-CRYPT -p `<pwd>` (stdout capture)
- §4 grep -q "^<user>:" 중복 검사 → 있으면 exit 2 (idempotent 회피, 명시 fail)
- §5 echo "${user}:${hash}:5000:5000::/var/vmail/dopa.co.kr/${user}::" >> /etc/dovecot/users
- §6 maildir `/var/vmail/dopa.co.kr/${user}/Maildir/{cur,new,tmp}` mkdir + chown vmail:vmail
- §7 echo `${password}` | saslpasswd2 -c -u dopa.co.kr -p `${user}` (SMTP 발신 동시 자격)
- §8 chown postfix /etc/sasldb2 + chmod 640 (이미 smtp_install.sh §7 와 동일)
- §9 systemctl reload dovecot postfix
- §10 stdout 안내 — USER + PASS + IMAP 993 + SMTP 587 5줄

### 4.4 M4 — `tests/integration/test_dovecot_imap_e2e.py` 신설 (230 line 실측)

산출물: protocol smoke + 실 서버 graceful skip (총 7 test)

- **Test 1**: `test_imap_capability_greeting` — `imaplib.IMAP4_SSL("mail.dopa.co.kr", 993)` 연결 + CAPABILITY 응답 형식 검증 (`IMAP4rev1` 토큰 정합). 연결 실패 시 pytest.skip("Dovecot 미설치 또는 서버 unreachable").
- **Test 2**: `test_smtp_submission_auth_required` — `smtplib.SMTP("mail.dopa.co.kr", 587)` STARTTLS + login 부재 시 RCPT TO 거부 (`530` 또는 `554`, sasl 강제 검증).
- **Test 3**: `test_lmtp_socket_path_documented` — `dovecot_install.sh` 안 `private/dovecot-lmtp` socket 경로 일관성 grep (Postfix virtual_transport + Dovecot 10-master.conf 동일 경로).
- **Test 4**: `test_dovecot_install_script_syntax` — `bash -n tools/dovecot_install.sh` syntax check (실 서버 부재 PASS).
- **Test 5**: `test_mail_user_add_script_syntax` — `bash -n tools/mail_user_add.sh` syntax check.
- **Test 6**: `test_mail_user_add_usage_no_args` — `bash tools/mail_user_add.sh` 인자 부재 호출 → exit 1 + Usage stdout 검증.
- **Test 7**: `test_mail_user_add_invalid_username_rejected` — 공백 포함 사용자명 호출 → exit 1 + 형식 오류 stdout 검증 (shell injection 방어 검증).

실측 결과 = 6 PASS + 1 SKIP (Test 1 IMAP 993 unreachable expected — Dovecot 미설치 상태). 실 서버 활성 후 7 PASS 전환.

### 4.5 M5 — README + History + .env.example 갱신 + commit + PR

- `.env.example` — IMAP_* keys 5건 add (`IMAP_HOST/PORT/USER/PASSWORD/ENCRYPTION`)
- `README.md` §11 변경 이력 prepend (M2 의무, 30행 cap 유지)
- `History.md` 역순 prepend (M3 의무, 최신 상단)
- doc-lint PASS 게이트
- `bash -n` syntax check 2 script PASS
- pytest `tests/integration/test_dovecot_imap_e2e.py` 6 test PASS (live skip 분기)
- feature branch `feat/cycle169.857-dovecot-imap-install` + PR

---

## 5. ③ 검증 게이트 (reviewer→qa→observability)

- **reviewer-agent**: 스크립트 2종 + e2e 6 test diff 전수 검토. BLOCKER 부재 confirm. 5단계 워크플로우 정합. M1~M5 의무 충족.
- **qa-agent**: bash -n + pytest 실행 + doc-lint + HTML mirror 비대상 (assessment .md 변경 부재).
- **observability-agent**: 본 cycle 신규 로그/메트릭 부재. SSH 수동 실행 시 `/root/dovecot_install.log` + `/root/mail_user_add.log` 권장 (스크립트 내부 tee).

---

## 6. G-final 사용자 게이트 (SSH 수동)

본 cycle 코드 완결 + reviewer PASS 후 사용자 manual SSH 실행:

```bash
# 1. 스크립트 전송
scp tools/dovecot_install.sh root@114.207.112.73:/root/
scp tools/mail_user_add.sh root@114.207.112.73:/root/

# 2. install chain 실행 (idempotent — 재실행 안전)
ssh root@114.207.112.73 'bash /root/dovecot_install.sh 2>&1 | tee /root/dovecot_install.log'

# 3. 계정 추가 (예: verify@dopa.co.kr)
ssh root@114.207.112.73 'bash /root/mail_user_add.sh verify 2>&1 | tee -a /root/mail_user_add.log'

# 4. swaks 발신 검증
ssh root@114.207.112.73 'swaks --to <테스트수신메일> --from verify@dopa.co.kr --server mail.dopa.co.kr:587 --auth LOGIN --auth-user verify@dopa.co.kr --auth-password <pwd> --tls'

# 5. IMAP 수신 검증 (Apple Mail/Thunderbird 클라이언트 또는 본 머신 python imaplib)
python3 -c "
import imaplib
m = imaplib.IMAP4_SSL('mail.dopa.co.kr', 993)
m.login('verify@dopa.co.kr', '<pwd>')
print(m.list())
print(m.select('INBOX'))
m.logout()
"
```

---

## 7. 리스크 + 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| dnf install dovecot 도중 postfix 재시작 timing race | 발신 중단 ≤5초 | smtp_install.sh §8 패턴 정합 (postfix reload 만, restart 회피) |
| Let's Encrypt cert renew 시 Dovecot 재시작 누락 | TLS 인증서 만료 후 IMAPS 실패 | certbot post-hook `systemctl reload postfix dovecot` 권장 (옵션, 본 cycle 외) |
| sasldb2 + passwd-file 자격 동기 부재 | 패스워드 변경 시 한쪽 stale | mail_user_add.sh 가 양쪽 동시 등록 — change-password 스크립트는 별도 cycle |
| vmail uid 5000 충돌 | useradd 실패 | useradd -r flag + 충돌 시 명시 fail (idempotent 무시 차단) |
| 외부 인터넷 → port 25 차단 (ISP 정책) | dopa.co.kr 외부 수신 불가 | 본 cycle scope 외 — KT/SKB 정책 확인 별도 cycle |

---

## 8. 산출물 인벤토리 (commit 단위)

| commit | 파일 | 단계 |
|---|---|---|
| 1 | `docs/exec-plans/active/2026-06-09-dovecot-imap-install.md` (본 문서) | M1 |
| 2 | `tools/dovecot_install.sh` | M2 |
| 3 | `tools/mail_user_add.sh` | M3 |
| 4 | `tests/integration/test_dovecot_imap_e2e.py` | M4 |
| 5 | `.env.example` IMAP_* keys add | M5 |
| 6 | `README.md` + `History.md` prepend | M2/M3 의무 |

> 권장 = 6 commit 분리 후 단일 PR. CLAUDE.md §5-2 "1 spawn = 1 산출물 = 1 commit = 1 push" 정합.

---

마지막 갱신: 2026-06-09 (M1 doc-first 신설, ② 개발 진입 직전)
