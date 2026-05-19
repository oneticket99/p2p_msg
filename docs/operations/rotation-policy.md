---
title: TooTalk 자격 + cert rotation 정책
owner: oneticket99
last_verified: 2026-05-19
status: active
---

# TooTalk 자격 + cert rotation 정책

TooTalk SMTP infra + DB + JWT 의 자격 + cert 의 주기 rotation 정책 정본. cycle 132 (Let's Encrypt + DKIM + SASL + DB password + JWT secret rotation chain) 산출물.

---

## 1. 개요

### 1-1. rotation 대상 5종

| 항목 | 주기 | 자동/수동 | tool |
| --- | --- | --- | --- |
| Let's Encrypt cert | 90일 (60일 갱신) | 자동 (certbot + cron) | `tools/cert_renew_check.sh` + `tools/crontab.txt` |
| DKIM key | 1년 권장 | 수동 (selector stamp 변경) | `opendkim-genkey` + DNS publish |
| SASL password | 3개월 권장 | 수동 (.env.smtp 갱신) | `saslpasswd2` + postfix reload |
| DB password (MariaDB) | 6개월 권장 | 수동 (.env.production 갱신) | `ALTER USER` + 서버 restart |
| JWT secret | 6개월 권장 | 수동 (.env.production 갱신) | `openssl rand -hex 32` + 서버 restart |

### 1-2. Phase 1 자동화 chain 정합

- Phase 1 회원가입 + 이메일 OTP 발신 chain → mail.dopa.co.kr SMTP 의무
- 자격 누출 + cert 만료 → OTP 발신 실패 → 회원가입 차단 risk
- 본 문서 = rotation 주기 단일 정본 (각 절차 의 step-by-step 손쉽 실행)

---

## 2. Let's Encrypt cert 자동 갱신

### 2-1. 주기

- Let's Encrypt 발급 cert 의 유효기간 = 90일
- certbot 의 권장 갱신 시점 = 만료 30일 전 (60일 시점)
- TooTalk infra 의 cron = 매월 3일 02:00 KST + 매일 03:00 KST 알람

### 2-2. 자동 갱신 script

`tools/cert_renew_check.sh` 의 cron 등록 (사용자 manual SSH 의무):

```bash
ssh root@114.207.112.73
crontab -e

# 추가:
0 3 * * * /root/cert_renew_check.sh /etc/letsencrypt/live/mail.dopa.co.kr/fullchain.pem 30
0 2 3 * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload postfix nginx 2>/dev/null"
```

### 2-3. 만료 30일 알람

- `cert_renew_check.sh` 의 `$2` 인수 = 임계일 (기본 30일)
- 30일 미만 + certbot 설치 시 → `certbot renew --dry-run` 자동 실행
- 30일 미만 + certbot 미설치 시 → stderr 메시지 + 사용자 manual 갱신 안내

### 2-4. 수동 갱신

```bash
# dry-run 검증
certbot renew --dry-run

# 실 갱신
certbot renew --quiet

# postfix + nginx reload
systemctl reload postfix nginx
```

---

## 3. DKIM key rotation

### 3-1. 주기

- 권장 = 1년 (NIST SP 800-57 의 권장 + 외부 노출 시 즉시)
- TooTalk 의 selector = `mail` (cycle 129 초기 설치)
- 1년 후 selector stamp = `mail2027`, `mail2028` 등 연도 기반

### 3-2. rotation chain

```bash
# 1. 새 selector key 발급 (예: mail2027)
ssh root@114.207.112.73
mkdir -p /etc/opendkim/keys/dopa.co.kr
cd /etc/opendkim/keys/dopa.co.kr
opendkim-genkey -b 2048 -d dopa.co.kr -s mail2027 -v

# 2. 권한 설정
chown -R opendkim:opendkim /etc/opendkim/keys/dopa.co.kr
chmod 600 /etc/opendkim/keys/dopa.co.kr/mail2027.private

# 3. DNS publish (whoisdomain.kr 콘솔)
#    mail2027._domainkey.dopa.co.kr TXT "v=DKIM1; k=rsa; p=<base64>"
cat /etc/opendkim/keys/dopa.co.kr/mail2027.txt

# 4. opendkim KeyTable + SigningTable 갱신
# /etc/opendkim/KeyTable:
#   mail2027._domainkey.dopa.co.kr dopa.co.kr:mail2027:/etc/opendkim/keys/dopa.co.kr/mail2027.private
# /etc/opendkim/SigningTable:
#   *@dopa.co.kr mail2027._domainkey.dopa.co.kr

# 5. opendkim 재시작 + 검증
systemctl restart opendkim
opendkim-testkey -d dopa.co.kr -s mail2027 -vvv

# 6. 구 selector (mail) 의 7일 grace period 후 DNS TXT 제거
```

### 3-3. 검증

```bash
# 메일 발신 후 헤더 의 DKIM-Signature 의 d= + s= 검증
mail-tester.com 또는 dkimvalidator.com 외부 테스트
```

---

## 4. SASL password rotation

### 4-1. 주기

- 권장 = 3개월 (90일)
- 외부 노출 + 직원 퇴사 + .env.smtp git history 누출 시 즉시
- TooTalk 의 SASL user = `tootalk_smtp@dopa.co.kr`

### 4-2. rotation chain

```bash
# 1. 신규 password 발급 (강도 32 chars 이상)
NEW_PASS=$(openssl rand -base64 24)

# 2. saslpasswd2 갱신
ssh root@114.207.112.73
echo "$NEW_PASS" | saslpasswd2 -p -c -u dopa.co.kr tootalk_smtp

# 3. sasldb2 권한 확인
chown postfix:sasl /etc/sasldb2
chmod 640 /etc/sasldb2

# 4. .env.smtp 갱신 (개발자 local + 서버)
#    SMTP_PASSWORD=<NEW_PASS>

# 5. postfix reload (sasldb2 reload)
systemctl reload postfix

# 6. server 의 .env.production 의 SMTP_PASSWORD 갱신 + restart
```

### 4-3. 검증

```bash
# server/mail/smtp_client.py 의 send_otp 의 sanity check
python -m server.mail.smtp_client --to 1ticket@toonation.co.kr --code 123456
```

---

## 5. DB password + JWT secret rotation

### 5-1. DB password (MariaDB)

- 권장 = 6개월
- DB user = `tootalk_app` (server/db/connection.py 정합)

```sql
-- MariaDB 콘솔
ALTER USER 'tootalk_app'@'%' IDENTIFIED BY '<NEW_PASS>';
FLUSH PRIVILEGES;
```

```bash
# .env.production 갱신
# DB_PASSWORD=<NEW_PASS>

# server restart chain
systemctl restart tootalk-signaling tootalk-auth
```

- bcrypt password hash schema (`users.password_hash`) 호환 (DB user password ≠ 회원 password)

### 5-2. JWT secret

- 권장 = 6개월
- 신규 secret 발급 → 기존 access_token 의 7일 grace period 후 invalidate

```bash
# 신규 secret 발급 (32 byte hex)
openssl rand -hex 32

# .env.production 갱신
# JWT_SECRET=<NEW_SECRET>

# server restart
systemctl restart tootalk-auth

# 기존 token 의 invalidate (7일 후)
# refresh_token 의 TTL 14일 의 grace period 활용
```

### 5-3. 위반 시 즉시 rotation 의무

- git history 의 .env.* 누출 → 즉시 rotation + git filter-branch (또는 BFG)
- CI log 의 secret echo → 즉시 rotation + GitHub Actions log 의 purge

---

## 6. cron 등록 요약

| cron 라인 | 주기 | 대상 |
| --- | --- | --- |
| `0 3 * * * /root/cert_renew_check.sh` | 매일 03:00 KST | cert 만료 30일 알람 |
| `0 2 3 * * /usr/bin/certbot renew --quiet` | 매월 3일 02:00 KST | cert 자동 갱신 |
| `0 0 * * * postqueue -p` 적체 alarm | 매일 00:00 KST | postfix queue 100+ 적체 |
| `*/5 * * * * pgrep -x opendkim` 헬스체크 | 5분 | opendkim 비정상 종료 시 restart |

전체 cron 정본 = `tools/crontab.txt` (root 의 등록 의무 안내).

---

## 7. 위반 + 알람 응답

- `cert_renew_check.sh` 의 알람 stderr 시 → 사용자 SSH 의 즉시 검증 + 수동 renew 의무
- DKIM signing 실패 (외부 메일 의 SPF + DKIM 검증 fail) → opendkim 재시작 + selector DNS publish 검증
- SASL auth 실패 (`535 5.7.8`) → saslpasswd2 갱신 + .env.smtp 동기 + postfix reload
- DB connection refused → MariaDB password 동기 + bcrypt schema 검증
- JWT decode 실패 → secret 동기 + token 재발급

---

마지막 갱신: 2026-05-19 — cycle 132 신설 (Let's Encrypt cert 자동 갱신 cron + DKIM + SASL + DB + JWT rotation 5종 정본)
