---
title: "SMTP 서버 데모 호스트 설치 절차"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# SMTP 서버 데모 호스트 설치 절차

> 본 문서는 사용자 directive 2026-05-17 ("smtp 서버는 사전에 명시했던 테스트서버에 설치해")
> 정합. TooTalk 회원가입 OTP 발신 SMTP 서버 = 데모 서버 (`114.207.112.73`) 안
> postfix 자체 설치 + Let's Encrypt + SPF/DKIM/DMARC hardening.
>
> 관련 정책:
> [SECURITY.md §9-2](../../SECURITY.md) · 영구 메모리
> `project_smtp_demo_server.md` + `project_auth_email_otp_required.md`.

---

## 1. 용도 명세

| 항목 | 값 |
|---|---|
| host | `114.207.112.73` (데모 서버 = 시그널링 서버 + SMTP 통합) |
| 도메인 (사용자 DNS) | `mail.<tootalk-domain>` (Phase 1 후반 확정 — A + MX + PTR record 의무) |
| port (submission) | 587 (STARTTLS) |
| port (inbound) | 25 (외부 → 본 서버 = block, 본 서버 → 외부 = allow) |
| 용도 | OTP 6 자리 발신 + 비밀번호 reset link 발신 (send-only) |
| 수신 의무 | 없음 (외부 → 본 서버 mail 0) |
| 보내는 from | `noreply@<tootalk-domain>` |
| Reply-To | `support@<tootalk-domain>` 또는 미설정 |

---

## 2. 사전 의존성 (Ubuntu 가정)

```bash
# 사용자 직접 SSH 의무 — 자체 환경 (main session) 의 SSH 차단 상태 확인
ssh root@114.207.112.73

# OS 정보 확인
lsb_release -a
uname -a

# 사전 패키지 갱신
apt update && apt upgrade -y

# 도구 설치
apt install -y postfix opendkim opendkim-tools certbot mailutils
```

> `postfix` apt 설치 시 prompt: **Internet Site** 선택 + System mail name = `<tootalk-domain>`.

---

## 3. DNS record 의무 (사용자 직접 — 사용자 보유 DNS provider UI)

| record | 값 | 의무 |
|---|---|---|
| **A** | `mail.<tootalk-domain>` → `114.207.112.73` | 본 서버 IP 매핑 |
| **MX** | `<tootalk-domain>` → `mail.<tootalk-domain>` (priority 10) | mail 라우팅 |
| **PTR (reverse)** | `114.207.112.73` → `mail.<tootalk-domain>` (ISP UI 의무) | rDNS 의 매치 — spam reputation 의무 |
| **SPF TXT** | `<tootalk-domain>` → `v=spf1 ip4:114.207.112.73 -all` | 발신 IP 인증 |
| **DKIM TXT** | `default._domainkey.<tootalk-domain>` → `v=DKIM1; k=rsa; p=<public_key>` | RSA signature 의 발신자 인증 |
| **DMARC TXT** | `_dmarc.<tootalk-domain>` → `v=DMARC1; p=quarantine; rua=mailto:dmarc@<tootalk-domain>` | SPF + DKIM fail 정책 |

> PTR record = ISP 의 직접 의무. residential IP 의 PTR 설정 불가능 시 = SendGrid relay 의 fallback 검토 의무.

---

## 4. Let's Encrypt TLS 인증서 발급

```bash
# port 80 의 단발 open 의무 (certbot --standalone)
certbot certonly --standalone \
  -d mail.<tootalk-domain> \
  --email admin@<tootalk-domain> \
  --agree-tos \
  --no-eff-email

# 산출물 위치
# /etc/letsencrypt/live/mail.<tootalk-domain>/fullchain.pem
# /etc/letsencrypt/live/mail.<tootalk-domain>/privkey.pem

# 자동 갱신 cron (90일 cycle)
systemctl enable --now certbot.timer
```

---

## 5. postfix 설정

```bash
# /etc/postfix/main.cf 의 핵심 영역
postconf -e "myhostname = mail.<tootalk-domain>"
postconf -e "mydomain = <tootalk-domain>"
postconf -e "myorigin = \$mydomain"
postconf -e "inet_interfaces = all"
postconf -e "mydestination = \$myhostname, localhost.\$mydomain, localhost"
postconf -e "mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128"
postconf -e "smtpd_banner = \$myhostname ESMTP"

# TLS 강제 설정
postconf -e "smtpd_tls_cert_file = /etc/letsencrypt/live/mail.<tootalk-domain>/fullchain.pem"
postconf -e "smtpd_tls_key_file = /etc/letsencrypt/live/mail.<tootalk-domain>/privkey.pem"
postconf -e "smtpd_tls_security_level = may"
postconf -e "smtp_tls_security_level = encrypt"
postconf -e "smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1"

# submission port 587 활성 (STARTTLS)
# /etc/postfix/master.cf 의 submission inet n - y - - smtpd 영역 의 주석 해제
# + -o smtpd_tls_security_level=encrypt
# + -o smtpd_sasl_auth_enable=yes
# + -o smtpd_relay_restrictions=permit_sasl_authenticated,reject

# 재시작
systemctl restart postfix
systemctl status postfix
```

---

## 6. OpenDKIM 설정

```bash
# 키 디렉토리
mkdir -p /etc/opendkim/keys/<tootalk-domain>
cd /etc/opendkim/keys/<tootalk-domain>

# RSA 2048 키 생성
opendkim-genkey -s default -d <tootalk-domain> -b 2048
chown opendkim:opendkim default.private
chmod 600 default.private

# default.txt 의 public key = DNS TXT 등록 의무 (§3 의 DKIM record)
cat default.txt

# /etc/opendkim.conf 의 핵심 영역
cat <<EOF >> /etc/opendkim.conf
Domain                  <tootalk-domain>
KeyFile                 /etc/opendkim/keys/<tootalk-domain>/default.private
Selector                default
Socket                  inet:8891@localhost
EOF

# postfix milter 등록
postconf -e "milter_protocol = 6"
postconf -e "milter_default_action = accept"
postconf -e "smtpd_milters = inet:localhost:8891"
postconf -e "non_smtpd_milters = inet:localhost:8891"

systemctl restart opendkim postfix
```

---

## 7. 발신 인증 + SASL 설정 (TooTalk client 의 인증)

```bash
# Cyrus SASL 설치
apt install -y libsasl2-modules sasl2-bin

# SASL 사용자 추가 (예: tootalk-otp)
saslpasswd2 -c -u <tootalk-domain> tootalk-otp
# 비밀번호 입력 — TooTalk app 의 .env.local 안 SMTP_PASSWORD 저장

# postfix 의 SASL 연동
postconf -e "smtpd_sasl_auth_enable = yes"
postconf -e "smtpd_sasl_type = cyrus"
postconf -e "smtpd_sasl_path = smtpd"
postconf -e "smtpd_sasl_security_options = noanonymous"
postconf -e "broken_sasl_auth_clients = yes"

# postfix 의 sasldb access 권한
adduser postfix sasl
systemctl restart postfix saslauthd
```

---

## 8. 검증

### 8.1 본 서버 안 self-test

```bash
# 로컬 mail 발신 테스트
echo "Test body" | mail -s "Test subject" -r noreply@<tootalk-domain> <사용자 의 외부 메일>

# postfix queue 확인
mailq

# 로그 확인
tail -f /var/log/mail.log
```

### 8.2 외부 검증 도구

- <https://www.mail-tester.com> — score 7+ 의무 (10 만점)
- <https://mxtoolbox.com/SuperTool.aspx> — SPF + DKIM + DMARC + blacklist 검사
- <https://www.dmarcanalyzer.com> — DMARC alignment 검증

### 8.3 client (TooTalk app) 의 의무 검증

```python
# app/auth/email.py (Phase 1 후반 신설)
import aiosmtplib
from email.message import EmailMessage

async def send_otp(to: str, otp: str) -> None:
    """OTP 6 자리 발신 — TooTalk 회원가입 + 비밀번호 reset 의무."""
    msg = EmailMessage()
    msg["From"] = "noreply@<tootalk-domain>"
    msg["To"] = to
    msg["Subject"] = "TooTalk 인증 번호"
    msg.set_content(f"인증 번호: {otp}\n3분 안 입력 의무.")

    await aiosmtplib.send(
        msg,
        hostname="114.207.112.73",
        port=587,
        username="tootalk-otp@<tootalk-domain>",
        password=os.environ["SMTP_PASSWORD"],
        start_tls=True,
    )
```

---

## 9. 보안 hardening

### 9.1 fail2ban 설치

```bash
apt install -y fail2ban
# /etc/fail2ban/jail.d/postfix.conf
cat <<EOF > /etc/fail2ban/jail.d/postfix.conf
[postfix]
enabled = true
port = smtp,submission
filter = postfix
logpath = /var/log/mail.log
maxretry = 3
findtime = 600
bantime = 3600
EOF
systemctl restart fail2ban
```

### 9.2 rate-limit (사용자 가드레일 [[project-auth-email-otp-required]] 정합)

- OTP 5회/30분 = 본 서버 의 IP + email 의 누계 제한 의무 (TooTalk app 의 의무 — DB redis 검토)
- 60초 재발송 = 직전 발송 timestamp 의 검증 의무 (TooTalk app 의 의무)
- postfix 자체 rate-limit = `anvil_rate_time_unit` + `smtpd_client_message_rate_limit`

### 9.3 spam reputation 의 점진 빌드

- 첫 발신 7일 = 본 서버 IP 의 warm-up 의무 — 적은 발신 + 점진 증가
- mail-tester score 7+ 도달 의무 (DKIM + SPF + DMARC + PTR 모두 PASS 시 도달)
- Gmail + Outlook 의 첫 spam 분류 가능성 = warm-up 이후 점진 개선

---

## 10. fallback — SendGrid relay (spam reputation 부족 시)

본 자체 SMTP 의 spam reputation 부족 시 (mail-tester score < 7 또는 Gmail 의 spam 분류) → SendGrid + AWS SES + Mailgun 의 relay 의 의무 검토.

### 10.1 SendGrid (free 100/day)

```bash
# /etc/postfix/sasl_passwd
echo "[smtp.sendgrid.net]:587 apikey:<SENDGRID_API_KEY>" > /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd
chmod 600 /etc/postfix/sasl_passwd*

# postfix 의 relay 설정
postconf -e "relayhost = [smtp.sendgrid.net]:587"
postconf -e "smtp_sasl_auth_enable = yes"
postconf -e "smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd"
postconf -e "smtp_sasl_security_options = noanonymous"
postconf -e "smtp_tls_security_level = encrypt"
systemctl restart postfix
```

### 10.2 비교

| relay | free quota | 비용 (paid) | reputation |
|---|---|---|---|
| 자체 postfix | 무제한 | $0 | 직접 build (warm-up 의무) |
| SendGrid | 100/day | $20/month (50K) | 자체 reputation 우위 |
| AWS SES | 200/day (EC2 외 free tier) | $0.10/1K | 자체 reputation 우위 |
| Mailgun | 5K/month (3개월 trial) | $35/month (50K) | 자체 reputation 우위 |

---

## 11. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 외부 mail 의 spam 분류 | PTR + SPF + DKIM 일부 미충족 | mail-tester 의 score 검사 + 누락 record 추가 |
| postfix queue 적체 | DNS 의 MX/A record 잘못 또는 외부 25 block (ISP) | DNS 검증 + 외부 outbound 25 port 의 ISP 확인 |
| TLS 인증서 만료 | certbot 의 자동 갱신 cron 부재 | `systemctl enable --now certbot.timer` |
| DKIM 검증 fail | DNS TXT 의 public key 의 base64 의 단일 line 의무 | `default.txt` 의 정확 copy + DNS 의 정합 |
| SASL 인증 fail | saslpasswd2 의 user@domain 의 mismatch | postfix 의 `smtpd_sasl_local_domain` 확인 |
| mail.log 안 `Connection refused` | fail2ban 의 ban 의 누계 | `fail2ban-client status postfix` + `fail2ban-client set postfix unbanip <IP>` |

---

## 12. 운영 체크리스트

- [ ] 도메인 (`<tootalk-domain>`) 확정 + 사용자 DNS provider 권한 확인
- [ ] DNS A + MX + PTR (ISP UI) + SPF + DKIM (key 생성 후) + DMARC TXT 등록
- [ ] postfix + opendkim + certbot + mailutils + fail2ban 설치
- [ ] Let's Encrypt 인증서 발급 + 자동 갱신 cron 활성
- [ ] postfix `/etc/postfix/main.cf` + submission port 587 활성
- [ ] OpenDKIM 의 RSA 2048 키 생성 + DNS TXT 등록 + milter 연동
- [ ] SASL user (`tootalk-otp@<domain>`) 생성 + 비밀번호 `.env.local` 저장
- [ ] mail-tester score 7+ 도달 검증
- [ ] TooTalk app 의 aiosmtplib client 의 연동 검증 (Phase 1 후반)
- [ ] fail2ban + rate-limit + spam reputation warm-up

---

## 13. 참조

- 영구 메모리: `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_smtp_demo_server.md`
- 영구 메모리: `~/.claude/projects/.../memory/project_auth_email_otp_required.md`
- [SECURITY.md §9-2](../../SECURITY.md) — 회원가입 + 이메일 OTP 보안
- [postfix Documentation](http://www.postfix.org/documentation.html)
- [OpenDKIM Documentation](http://opendkim.org/docs.html)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [SendGrid SMTP Relay](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)
- [mail-tester](https://www.mail-tester.com) — spam reputation 검증
