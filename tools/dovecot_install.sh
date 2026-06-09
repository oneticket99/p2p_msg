#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# TooTalk Dovecot+IMAP 자동 설치 chain — Rocky Linux 9.7 + mail.dopa.co.kr
# 수신/메일박스 신설 — virtual mailbox 모델 + Postfix LMTP 통합
# Exec Plan: docs/exec-plans/active/2026-06-09-dovecot-imap-install.md (cycle 169.857 M2)
#
# 사용자 manual 실행 의무 (classifier 차단 회피 path):
#   사용자 macOS → scp tools/dovecot_install.sh root@114.207.112.73:/root/
#   사용자 macOS → ssh root@114.207.112.73 'bash /root/dovecot_install.sh 2>&1 | tee /root/dovecot_install.log'
#
# 사전 조건: tools/smtp_install.sh 가 이미 실행 완료 (Postfix + cyrus-sasl + Let's Encrypt cert 존재)
# idempotent — 재실행 안전. 단계별 echo + 실패 시 exit. 진행 progress + 로그 파일.

set -euo pipefail

# ─── 변수 정의 ───────────────────────────────────────────────
DOMAIN=dopa.co.kr                              # 도메인 (smtp_install.sh 정합)
HOSTNAME=mail.dopa.co.kr                       # 메일 서버 hostname (DNS A record 정합)
VMAIL_USER=vmail                               # virtual mailbox system user
VMAIL_UID=5000                                 # vmail uid (Rocky 9 예약 회피 — 5000~6000 사용자 범위)
VMAIL_GID=5000                                 # vmail gid
VMAIL_HOME=/var/vmail                          # maildir root parent
VMAIL_DOMAIN_DIR="${VMAIL_HOME}/${DOMAIN}"     # 도메인 maildir root
DOVECOT_USERS=/etc/dovecot/users               # passwd-file 계정 store
LOG=/root/dovecot_install.log                  # 진행 로그 파일

# ─── 단계 echo helper ───────────────────────────────────────
step() {
  # 단계 진행 stdout + 로그 동시 출력 (KST timestamp)
  local ts
  ts=$(TZ=Asia/Seoul date '+%F %T %Z')
  echo "=== [${ts}] $*"
}

# ─── 0 사전 조건 검증 ──────────────────────────────────────
step "0 사전 조건 검증 (smtp_install.sh 실행 완료 여부)"
# Postfix 서비스 활성 검증 — 부재 시 smtp_install.sh 우선 실행 안내
if ! systemctl is-active --quiet postfix; then
  echo "  ⚠️ postfix 서비스 비활성 — 먼저 tools/smtp_install.sh 실행 필요"
  exit 1
fi
# Let's Encrypt cert 존재 검증 — Dovecot SSL config 재사용
if [ ! -f "/etc/letsencrypt/live/${HOSTNAME}/fullchain.pem" ]; then
  echo "  ⚠️ Let's Encrypt cert 부재 — smtp_install.sh 단계 3 미완료"
  exit 1
fi
echo "  = postfix 활성 + Let's Encrypt cert 존재 확인"

# ─── 1 패키지 설치 ──────────────────────────────────────────
step "1 dnf install dovecot + dovecot-pigeonhole"
# Pigeonhole = Sieve filter 모듈 (Phase 2 활용 예정, install 만 동시)
dnf install -y dovecot dovecot-pigeonhole 2>&1 | tail -20

# rpm verify
step "1.1 rpm 설치 검증"
rpm -q dovecot dovecot-pigeonhole

# ─── 2 vmail system user ────────────────────────────────────
step "2 vmail system user 생성 (uid=${VMAIL_UID} gid=${VMAIL_GID})"
# group 부재 시 신설, 존재 시 skip
if ! getent group "${VMAIL_USER}" > /dev/null; then
  groupadd -r -g "${VMAIL_GID}" "${VMAIL_USER}"
  echo "  + vmail group 신설"
else
  echo "  = vmail group 기존"
fi
# user 부재 시 신설, 존재 시 skip — -r system user, -d home, -s nologin (로그인 차단)
if ! id -u "${VMAIL_USER}" > /dev/null 2>&1; then
  useradd -r -u "${VMAIL_UID}" -g "${VMAIL_GID}" -d "${VMAIL_HOME}" -s /sbin/nologin "${VMAIL_USER}"
  echo "  + vmail user 신설"
else
  echo "  = vmail user 기존"
fi

# ─── 3 maildir root ─────────────────────────────────────────
step "3 maildir root 생성 (${VMAIL_DOMAIN_DIR})"
# 도메인 디렉토리 신설 + vmail 권한 — 750 (group dovecot 도 읽기 권한 가능)
mkdir -p "${VMAIL_DOMAIN_DIR}"
chown -R "${VMAIL_USER}:${VMAIL_USER}" "${VMAIL_HOME}"
chmod 750 "${VMAIL_HOME}"

# ─── 4 Dovecot conf 6 파일 ──────────────────────────────────
step "4 Dovecot conf 파일 생성 (6 conf — protocols/mail/auth/ssl/master + passwd-file backend)"

# /etc/dovecot/dovecot.conf — 활성 프로토콜 (imap+lmtp+sieve)
cat > /etc/dovecot/dovecot.conf <<EOF
# TooTalk Dovecot 메인 설정 — cycle 169.857 M2
# 한글 주석: imap = 클라이언트 수신 / lmtp = Postfix → Dovecot deliver / sieve = filter (Phase 2)
protocols = imap lmtp sieve

# listen — IPv4 만 (smtp_install.sh inet_protocols=ipv4 정합)
listen = *

# conf.d 분할 include
!include conf.d/*.conf
!include_try local.conf
EOF

# /etc/dovecot/conf.d/10-mail.conf — maildir 위치
cat > /etc/dovecot/conf.d/10-mail.conf <<EOF
# 한글 주석: maildir 위치 = /var/vmail/<domain>/<user>/Maildir (%n = mailbox 이름, @ 앞 부분)
mail_location = maildir:${VMAIL_DOMAIN_DIR}/%n/Maildir

# vmail user 권한으로 mail 디렉토리 접근
mail_uid = ${VMAIL_UID}
mail_gid = ${VMAIL_GID}

# privileged group 부재 (PAM 미사용 정합)
mail_privileged_group = ${VMAIL_USER}

# namespace 기본 (INBOX)
namespace inbox {
  inbox = yes
}
EOF

# /etc/dovecot/conf.d/10-auth.conf — 인증 모듈
cat > /etc/dovecot/conf.d/10-auth.conf <<EOF
# 한글 주석: 평문 인증 차단 (STARTTLS 필수) + plain/login 메커니즘 만 활성
disable_plaintext_auth = yes
auth_mechanisms = plain login

# system 사용자 인증 (PAM) 비활성 — passwd-file 단일 backend
!include auth-passwdfile.conf.ext
EOF

# /etc/dovecot/conf.d/auth-passwdfile.conf.ext — passwd-file backend
cat > /etc/dovecot/conf.d/auth-passwdfile.conf.ext <<EOF
# 한글 주석: passwd-file backend — /etc/dovecot/users 안 SHA512-CRYPT 해시 인증
passdb {
  driver = passwd-file
  args = scheme=SHA512-CRYPT username_format=%u ${DOVECOT_USERS}
}

userdb {
  driver = passwd-file
  args = username_format=%u ${DOVECOT_USERS}
  default_fields = uid=${VMAIL_UID} gid=${VMAIL_GID} home=${VMAIL_DOMAIN_DIR}/%n
}
EOF

# /etc/dovecot/conf.d/10-ssl.conf — Let's Encrypt cert 재사용 (smtp_install.sh §3)
cat > /etc/dovecot/conf.d/10-ssl.conf <<EOF
# 한글 주석: SSL/TLS 강제 + Let's Encrypt cert 재사용 (postfix 와 동일 cert)
ssl = required
ssl_cert = </etc/letsencrypt/live/${HOSTNAME}/fullchain.pem
ssl_key = </etc/letsencrypt/live/${HOSTNAME}/privkey.pem
ssl_min_protocol = TLSv1.2
ssl_cipher_list = ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS
ssl_prefer_server_ciphers = yes
EOF

# /etc/dovecot/conf.d/10-master.conf — LMTP unix socket (Postfix 통합)
cat > /etc/dovecot/conf.d/10-master.conf <<EOF
# 한글 주석: LMTP socket = Postfix virtual_transport 대상 (private/dovecot-lmtp)
service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}

# IMAP 서비스 — 993 IMAPS + 143 IMAP+STARTTLS
service imap-login {
  inet_listener imap {
    port = 143
  }
  inet_listener imaps {
    port = 993
    ssl = yes
  }
}

# auth 서비스 — Dovecot 내부 (Postfix sasl 미사용, smtp_install.sh sasldb2 정합)
service auth {
  unix_listener auth-userdb {
    mode = 0666
    user = ${VMAIL_USER}
    group = ${VMAIL_USER}
  }
}
EOF

# ─── 5 passwd-file 빈 파일 ──────────────────────────────────
step "5 /etc/dovecot/users 빈 파일 생성 (계정 store)"
if [ ! -f "${DOVECOT_USERS}" ]; then
  touch "${DOVECOT_USERS}"
  echo "  + ${DOVECOT_USERS} 신설"
else
  echo "  = ${DOVECOT_USERS} 기존"
fi
chown "${VMAIL_USER}:dovecot" "${DOVECOT_USERS}"
chmod 0640 "${DOVECOT_USERS}"

# ─── 6 Postfix main.cf virtual_* 통합 ──────────────────────
step "6 Postfix main.cf virtual_* 키 추가 (LMTP 통합)"
# virtual_mailbox_domains — dopa.co.kr 가상 도메인 수신 활성
postconf -e "virtual_mailbox_domains=${DOMAIN}"
# virtual_mailbox_base — maildir 최상위 (smtp_install.sh §5 mydestination 정합 유지)
postconf -e "virtual_mailbox_base=${VMAIL_HOME}"
# virtual_transport — Dovecot LMTP socket
postconf -e "virtual_transport=lmtp:unix:private/dovecot-lmtp"
# local_recipient_maps — local 수신 차단 (virtual 만 처리)
postconf -e "local_recipient_maps="

# ─── 7 iptables ACCEPT 143/993/4190 ────────────────────────
step "7 iptables ACCEPT 143/993/4190 + persist"
for port in 143 993 4190; do
  # 중복 rule 회피 — -C 검사 후 부재 시 -I 삽입
  if ! iptables -C INPUT -p tcp --dport "${port}" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT -p tcp --dport "${port}" -j ACCEPT
    echo "  + iptables ACCEPT ${port} 신설"
  else
    echo "  = iptables ACCEPT ${port} 기존"
  fi
done
# Rocky 9 + iptables-services 사용 시 save
iptables-save > /etc/sysconfig/iptables

# ─── 8 systemctl enable + restart ──────────────────────────
step "8 systemctl enable --now dovecot + reload postfix"
systemctl enable --now dovecot 2>&1 | tail -3
# Postfix reload — config 변경 반영, 기존 발신 큐 보존 (restart 회피)
systemctl reload postfix 2>&1 | tail -3 || systemctl restart postfix

# ─── 9 listen 검증 ─────────────────────────────────────────
step "9 listen 검증 (143 / 993 / 4190 + LMTP socket)"
ss -lntp | grep -E ':143|:993|:4190' || echo "  ⚠️ IMAP listen 부재 — 진단 필요"
# LMTP unix socket — Dovecot 가 생성, Postfix 가 통신
if [ -S /var/spool/postfix/private/dovecot-lmtp ]; then
  echo "  = LMTP socket 존재 — /var/spool/postfix/private/dovecot-lmtp"
else
  echo "  ⚠️ LMTP socket 부재 — Dovecot 재기동 필요"
fi

# ─── 10 사용자 안내 ────────────────────────────────────────
step "10 완료 — 계정 추가 명령 안내"
echo
echo "─── 계정 추가 (수신 메일박스 + SMTP 발신 양방향) ─────"
echo "  bash /root/mail_user_add.sh <user>"
echo
echo "  예: bash /root/mail_user_add.sh verify"
echo "      → verify@dopa.co.kr 활성 (IMAP 993 + SMTP 587)"
echo
echo "─── 클라이언트 (Apple Mail / Thunderbird) 설정 ────────"
echo "  IMAP host      : ${HOSTNAME}"
echo "  IMAP port      : 993 (SSL/TLS)"
echo "  SMTP host      : ${HOSTNAME}"
echo "  SMTP port      : 587 (STARTTLS)"
echo "  Username       : <user>@${DOMAIN}"
echo "  Password       : mail_user_add.sh 가 출력하는 자격"
echo
echo "─── 발신 검증 swaks ────────────────────────────────────"
echo "  swaks --to YOUR_TARGET@gmail.com \\"
echo "        --from <user>@${DOMAIN} \\"
echo "        --server ${HOSTNAME}:587 \\"
echo "        --auth LOGIN \\"
echo "        --auth-user <user>@${DOMAIN} \\"
echo "        --auth-password '<pwd>' \\"
echo "        --tls"
echo
echo "─── 수신 검증 Python imaplib ──────────────────────────"
echo "  python3 -c \"import imaplib; m=imaplib.IMAP4_SSL('${HOSTNAME}',993); m.login('<user>@${DOMAIN}','<pwd>'); print(m.list()); m.logout()\""
echo

step "완료 — Dovecot+IMAP 활성 + Postfix LMTP 통합 + 계정 추가 준비"
