#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# TooTalk SMTP 자동 설치 chain — Rocky Linux 9.7 + mail.dopa.co.kr
# 사용자 manual 실행 의무 (classifier 차단 회피 path):
#   사용자 macOS → scp tools/smtp_install.sh root@114.207.112.73:/root/
#   사용자 macOS → ssh root@114.207.112.73 'bash /root/smtp_install.sh 2>&1 | tee /root/smtp_install.log'
#
# idempotent — 재실행 안전. 단계별 echo + 실패 시 exit. 진행 progress + 로그 파일.

set -euo pipefail

# ─── 변수 정의 ───────────────────────────────────────────────
DOMAIN=dopa.co.kr                              # 도메인 (사용자 directive 2026-05-19)
HOSTNAME=mail.dopa.co.kr                       # 메일 서버 hostname (DNS A record 정합)
SASL_USER=noreply                              # SASL 인증 user (OTP 발신 자격)
DKIM_SELECTOR=mail                             # DKIM selector (DNS TXT record name)
ADMIN_EMAIL=postmaster@dopa.co.kr              # certbot 등록 + DMARC rua 발신 admin
LOG=/root/smtp_install.log                     # 진행 로그 파일

# ─── 단계 echo helper ───────────────────────────────────────
step() {
  # 단계 진행 stdout + 로그 동시 출력 (KST timestamp)
  local ts
  ts=$(TZ=Asia/Seoul date '+%F %T %Z')
  echo "=== [${ts}] $*"
}

# ─── 1 패키지 설치 ──────────────────────────────────────────
step "1 dnf install postfix + cyrus-sasl + mailx + swaks + iptables-services + opendkim + certbot + openssl"
dnf install -y \
  postfix cyrus-sasl cyrus-sasl-plain cyrus-sasl-md5 \
  mailx swaks iptables-services \
  opendkim opendkim-tools \
  certbot openssl ca-certificates 2>&1 | tail -30

# rpm verify
step "1.1 rpm 설치 검증"
rpm -q postfix cyrus-sasl mailx swaks iptables-services opendkim certbot openssl

# ─── 2 iptables ACCEPT 25/587/465 ──────────────────────────
step "2 iptables ACCEPT 25/587/465 + persist"
for port in 25 587 465; do
  # 중복 rule 회피 — -C 검사 후 부재 시 -I 삽입
  if ! iptables -C INPUT -p tcp --dport "${port}" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT -p tcp --dport "${port}" -j ACCEPT
    echo "  + iptables ACCEPT ${port} 신설"
  else
    echo "  = iptables ACCEPT ${port} 기존"
  fi
done
# Rocky 9 + iptables-services 사용 시 save
mkdir -p /etc/sysconfig
iptables-save > /etc/sysconfig/iptables
systemctl enable --now iptables.service 2>&1 | tail -3 || echo "  iptables.service 의 의 이미 활성"

# ─── 3 Let's Encrypt cert ──────────────────────────────────
step "3 certbot certonly --standalone -d ${HOSTNAME}"
# port 80 점유 service 사전 정지
systemctl stop httpd nginx 2>/dev/null || true
if [ ! -f "/etc/letsencrypt/live/${HOSTNAME}/fullchain.pem" ]; then
  certbot certonly --standalone --non-interactive --agree-tos \
    --email "${ADMIN_EMAIL}" -d "${HOSTNAME}" 2>&1 | tail -20
else
  echo "  = cert 기존 — /etc/letsencrypt/live/${HOSTNAME}/fullchain.pem"
fi

# ─── 4 opendkim selector key ────────────────────────────────
step "4 opendkim selector key 생성 (selector=${DKIM_SELECTOR})"
mkdir -p "/etc/opendkim/keys/${DOMAIN}"
cd "/etc/opendkim/keys/${DOMAIN}"
if [ ! -f "${DKIM_SELECTOR}.private" ]; then
  opendkim-genkey -b 2048 -s "${DKIM_SELECTOR}" -d "${DOMAIN}"
  echo "  + DKIM key 신설"
else
  echo "  = DKIM key 기존"
fi
chown -R opendkim:opendkim "/etc/opendkim/keys/${DOMAIN}"
chmod 600 "${DKIM_SELECTOR}.private"

# KeyTable + SigningTable + TrustedHosts
cat > /etc/opendkim/KeyTable <<EOF
${DKIM_SELECTOR}._domainkey.${DOMAIN} ${DOMAIN}:${DKIM_SELECTOR}:/etc/opendkim/keys/${DOMAIN}/${DKIM_SELECTOR}.private
EOF
cat > /etc/opendkim/SigningTable <<EOF
*@${DOMAIN} ${DKIM_SELECTOR}._domainkey.${DOMAIN}
EOF
cat > /etc/opendkim/TrustedHosts <<EOF
127.0.0.1
::1
${HOSTNAME}
${DOMAIN}
EOF

# opendkim.conf
cat > /etc/opendkim.conf <<EOF
PidFile /run/opendkim/opendkim.pid
Mode sv
Syslog yes
SyslogSuccess yes
LogWhy yes
UserID opendkim:opendkim
Socket inet:8891@127.0.0.1
Umask 002
SendReports yes
SoftwareHeader yes
Canonicalization relaxed/relaxed
Domain ${DOMAIN}
Selector ${DKIM_SELECTOR}
MinimumKeyBits 1024
KeyTable /etc/opendkim/KeyTable
SigningTable refile:/etc/opendkim/SigningTable
ExternalIgnoreList refile:/etc/opendkim/TrustedHosts
InternalHosts refile:/etc/opendkim/TrustedHosts
EOF

# ─── 5 postfix main.cf ─────────────────────────────────────
step "5 postfix main.cf 갱신"
postconf -e "myhostname=${HOSTNAME}"
postconf -e "mydomain=${DOMAIN}"
postconf -e "myorigin=\$mydomain"
postconf -e "inet_interfaces=all"
postconf -e "inet_protocols=ipv4"
postconf -e "mydestination=\$myhostname, localhost.\$mydomain, localhost"
postconf -e "smtpd_banner=\$myhostname ESMTP"
postconf -e "smtpd_tls_cert_file=/etc/letsencrypt/live/${HOSTNAME}/fullchain.pem"
postconf -e "smtpd_tls_key_file=/etc/letsencrypt/live/${HOSTNAME}/privkey.pem"
postconf -e "smtpd_tls_security_level=may"
postconf -e "smtp_tls_security_level=may"
postconf -e "smtpd_tls_protocols=!SSLv2,!SSLv3,!TLSv1,!TLSv1.1"
postconf -e "smtp_tls_protocols=!SSLv2,!SSLv3,!TLSv1,!TLSv1.1"
postconf -e "smtpd_tls_loglevel=1"
postconf -e "smtpd_sasl_auth_enable=yes"
postconf -e "smtpd_sasl_type=cyrus"
postconf -e "smtpd_sasl_path=smtpd"
postconf -e "smtpd_sasl_local_domain=${HOSTNAME}"
postconf -e "smtpd_sasl_security_options=noanonymous"
postconf -e "broken_sasl_auth_clients=yes"
postconf -e "smtpd_recipient_restrictions=permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination"
postconf -e "milter_default_action=accept"
postconf -e "milter_protocol=6"
postconf -e "smtpd_milters=inet:127.0.0.1:8891"
postconf -e "non_smtpd_milters=inet:127.0.0.1:8891"

# ─── 6 postfix master.cf submission 587 + smtps 465 ────────
step "6 postfix master.cf — submission 587 + smtps 465 활성"
if ! grep -q '^submission inet' /etc/postfix/master.cf; then
  cat >> /etc/postfix/master.cf <<'EOF'

submission inet n       -       n       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_client_restrictions=permit_sasl_authenticated,reject
EOF
  echo "  + submission 587 신설"
else
  echo "  = submission 587 기존"
fi
if ! grep -q '^smtps inet' /etc/postfix/master.cf; then
  cat >> /etc/postfix/master.cf <<'EOF'

smtps     inet  n       -       n       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_client_restrictions=permit_sasl_authenticated,reject
EOF
  echo "  + smtps 465 신설"
else
  echo "  = smtps 465 기존"
fi

# ─── 7 SASL 자격 ────────────────────────────────────────────
step "7 cyrus-sasl 자격 (${SASL_USER}@${DOMAIN})"
SASL_PASSWORD=$(openssl rand -base64 24)
# saslpasswd2 + sasldb2 저장
echo "${SASL_PASSWORD}" | saslpasswd2 -c -u "${DOMAIN}" -p "${SASL_USER}"
chown postfix /etc/sasldb2 || true
chmod 640 /etc/sasldb2 || true
# /etc/sasl2/smtpd.conf — postfix sasl 모듈 config
mkdir -p /etc/sasl2
cat > /etc/sasl2/smtpd.conf <<EOF
pwcheck_method: auxprop
auxprop_plugin: sasldb
mech_list: PLAIN LOGIN
EOF

# ─── 8 systemctl enable + start ────────────────────────────
step "8 systemctl enable --now opendkim postfix"
systemctl enable --now opendkim 2>&1 | tail -3
systemctl enable --now postfix 2>&1 | tail -3
# 재시작 — config 변경 반영
systemctl restart opendkim postfix

# ─── 9 listen 검증 ─────────────────────────────────────────
step "9 listen 검증 (25 / 587 / 465 / 8891)"
ss -lntp | grep -E ':25|:587|:465|:8891' || echo "  ⚠️ listen 부재 — 진단 필요"

# ─── 10 DNS TXT record 출력 ─────────────────────────────────
step "10 DNS TXT record — 사용자 whoisdomain.kr manual 등록 의무"
echo
echo "─── SPF (dopa.co.kr) ───────────────────────────────"
echo "TXT  dopa.co.kr.   v=spf1 mx a:${HOSTNAME} ~all"
echo
echo "─── DKIM (${DKIM_SELECTOR}._domainkey.dopa.co.kr) ──"
cat "/etc/opendkim/keys/${DOMAIN}/${DKIM_SELECTOR}.txt"
echo
echo "─── DMARC (_dmarc.dopa.co.kr) ──────────────────────"
echo "TXT  _dmarc.dopa.co.kr.   v=DMARC1; p=quarantine; rua=mailto:${ADMIN_EMAIL}; ruf=mailto:${ADMIN_EMAIL}; sp=quarantine; adkim=r; aspf=r"
echo
echo "─── SASL 자격 (TooTalk OTP 발신 client config) ─────"
echo "USER: ${SASL_USER}@${DOMAIN}"
echo "PASS: ${SASL_PASSWORD}"
echo "HOST: ${HOSTNAME}"
echo "PORT: 587 (STARTTLS) 또는 465 (SMTPS)"
echo
echo "─── 발신 테스트 swaks 명령 ─────────────────────────"
echo "swaks --to YOUR_GMAIL@gmail.com \\"
echo "      --from ${SASL_USER}@${DOMAIN} \\"
echo "      --server ${HOSTNAME}:587 \\"
echo "      --auth LOGIN \\"
echo "      --auth-user ${SASL_USER}@${DOMAIN} \\"
echo "      --auth-password '${SASL_PASSWORD}' \\"
echo "      --tls"
echo

step "완료 — DNS record 등록 + swaks 발신 테스트 의무"
