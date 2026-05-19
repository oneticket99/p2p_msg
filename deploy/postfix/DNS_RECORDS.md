# TooTalk SMTP DNS Records — SPF + DKIM + DMARC

본 문서 = Phase 4 postfix container 의 production 진입 시 DNS 등록 의무 record 정본.

## 1. SPF (Sender Policy Framework)

**TXT record** at `${MAILDOMAIN}` (root):

```dns
@   IN  TXT  "v=spf1 ip4:114.207.112.73 -all"
```

- `ip4:114.207.112.73` = 데모 서버 IP (사용자 directive — IP direct).
- `-all` = SPF 부합 무 IP = HARD FAIL (수신 server 의 reject 의무).

## 2. DKIM (DomainKeys Identified Mail)

**TXT record** at `${DKIM_SELECTOR}._domainkey.${MAILDOMAIN}`:

```dns
tootalk._domainkey   IN  TXT   "v=DKIM1; k=rsa; p=<base64-public-key>"
```

- public key 출처 = postfix container 의 `/etc/opendkim/keys/${DKIM_SELECTOR}.txt` (entrypoint.sh 가 자동 출력).
- 2048 bit RSA SHA-256 (NIST 권장).

**확인 명령** (container 안):

```bash
docker compose exec postfix cat /etc/opendkim/keys/tootalk.txt
```

## 3. DMARC (Domain-based Message Authentication, Reporting & Conformance)

**TXT record** at `_dmarc.${MAILDOMAIN}`:

```dns
_dmarc   IN  TXT   "v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@tootalk.demo; ruf=mailto:dmarc-forensic@tootalk.demo; fo=1; adkim=s; aspf=s"
```

- `p=quarantine` = SPF/DKIM 부합 무 메일 = 스팸함 분리 (초기 deploy 의 conservative).
- production 안정화 후 `p=reject` 전환.
- `adkim=s` + `aspf=s` = strict alignment (subdomain mismatch reject).

## 4. PTR (Reverse DNS, 의무)

- 데모 서버 ISP 에 `114.207.112.73 → mail.tootalk.demo` 의 PTR record 등록 요청.
- PTR 무 = Gmail / Outlook 등 의 reject 위험 큼.

## 5. MX (수신 부재, 발신 전용)

본 서버 = OTP 발신 전용. 수신 부재 의무. MX record 부재 정합.

## 6. 검증 명령

```bash
dig TXT tootalk.demo +short                                  # SPF
dig TXT tootalk._domainkey.tootalk.demo +short               # DKIM
dig TXT _dmarc.tootalk.demo +short                           # DMARC
dig -x 114.207.112.73 +short                                 # PTR

# 실 메일 발송 + 외부 검증 (mail-tester.com 의 score 8+ 의무)
echo "subject:test" | mail -s "tootalk smtp test" \
    -aFrom:noreply@tootalk.demo test-xxxxx@srv1.mail-tester.com
```

## 7. Let's Encrypt TLS 인증서 (mail.${MAILDOMAIN})

```bash
# Phase 4 nginx cycle 105 의 certbot 통합 정합
docker compose run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    -d mail.tootalk.demo \
    --email admin@tootalk.demo \
    --agree-tos --no-eff-email
```

## 참조

- `project_smtp_demo_server.md` path = `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_smtp_demo_server.md` — SMTP 데모 서버 memory (사용자 directive 2026-05-17)
- [postfix Dockerfile](Dockerfile)
- [opendkim.conf](opendkim.conf)
- [Phase 4 infra setup §2.6 보안 의무](../../docs/exec-plans/active/2026-05-22-phase4-infra-setup.md)
