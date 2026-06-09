#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# TooTalk mail 계정 1건 추가 명령 — mail.dopa.co.kr 수신/발신 양방향 자격
# Exec Plan: docs/exec-plans/active/2026-06-09-dovecot-imap-install.md (cycle 169.857 M3)
#
# 사용자 manual 실행 (사전 조건: dovecot_install.sh 실행 완료):
#   bash /root/mail_user_add.sh <user>
#
# 결과:
#   - Dovecot passwd-file (/etc/dovecot/users) 안 user 신설 + SHA512-CRYPT 해시
#   - maildir (/var/vmail/dopa.co.kr/<user>/Maildir/{cur,new,tmp}) 생성
#   - cyrus-sasl sasldb2 안 user@dopa.co.kr SMTP 발신 자격 동시 등록
#   - Dovecot + Postfix reload (config 변경 즉시 반영)
#   - stdout 안내 — USER + PASS + IMAP/SMTP 설정

set -euo pipefail

# ─── 변수 정의 ───────────────────────────────────────────────
DOMAIN=dopa.co.kr                              # 도메인 (dovecot_install.sh 정합)
HOSTNAME=mail.dopa.co.kr                       # 메일 서버 hostname
VMAIL_USER=vmail                               # virtual mailbox system user
VMAIL_UID=5000                                 # vmail uid
VMAIL_GID=5000                                 # vmail gid
VMAIL_HOME=/var/vmail                          # maildir root parent
VMAIL_DOMAIN_DIR="${VMAIL_HOME}/${DOMAIN}"     # 도메인 maildir root
DOVECOT_USERS=/etc/dovecot/users               # passwd-file 계정 store

# ─── 1 인자 검증 ───────────────────────────────────────────
if [ $# -ne 1 ]; then
  echo "Usage: $0 <user>"
  echo "  예: $0 verify   → verify@${DOMAIN} 활성 (IMAP 993 + SMTP 587)"
  exit 1
fi
USER_NAME=$1
USER_EMAIL="${USER_NAME}@${DOMAIN}"

# 사용자명 형식 검증 — 영숫자 + ._- 만 허용 (메일 RFC 정합 + shell 안전)
if ! [[ "${USER_NAME}" =~ ^[a-zA-Z0-9._-]+$ ]]; then
  echo "ERROR: 사용자명 형식 오류 — 영숫자 + . _ - 만 허용"
  exit 1
fi

# ─── 2 중복 검사 ───────────────────────────────────────────
# 한글 주석: passwd-file 중복 등록 차단 — 패스워드 의도치 않은 덮어쓰기 방지
if grep -q "^${USER_NAME}:" "${DOVECOT_USERS}" 2>/dev/null; then
  echo "ERROR: ${USER_EMAIL} 이미 등록됨 (${DOVECOT_USERS})"
  echo "       패스워드 변경은 별도 명령 (mail_user_passwd.sh, Phase 2 예정)"
  exit 2
fi

# ─── 3 패스워드 생성 ───────────────────────────────────────
# 한글 주석: openssl rand 24 byte → base64 32 char → URL-safe 변환 (/+ 제거)
PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)

# ─── 4 SHA512-CRYPT 해시 ───────────────────────────────────
# 한글 주석: doveadm pw = Dovecot 표준 해시 도구, SHA512-CRYPT = passwd-file 권장 scheme
PWHASH=$(doveadm pw -s SHA512-CRYPT -p "${PASSWORD}")

# ─── 5 passwd-file 추가 ────────────────────────────────────
# 한글 주석: 형식 = user@domain:hash:uid:gid:gecos:home:shell:extra (Dovecot passwd-file 표준)
# cycle 169.860 회수 — username_format=%u (full email) 정합. bare name 사용 시 userdb lookup FAIL
echo "${USER_EMAIL}:${PWHASH}:${VMAIL_UID}:${VMAIL_GID}::${VMAIL_DOMAIN_DIR}/${USER_NAME}::" \
  >> "${DOVECOT_USERS}"

# ─── 6 maildir 생성 ────────────────────────────────────────
# 한글 주석: maildir 표준 3 디렉토리 (cur=확정 / new=신착 / tmp=처리중)
USER_MAILDIR="${VMAIL_DOMAIN_DIR}/${USER_NAME}/Maildir"
mkdir -p "${USER_MAILDIR}"/{cur,new,tmp}
chown -R "${VMAIL_USER}:${VMAIL_USER}" "${VMAIL_DOMAIN_DIR}/${USER_NAME}"
chmod -R 700 "${VMAIL_DOMAIN_DIR}/${USER_NAME}"

# ─── 6.1 SELinux fcontext (Rocky 9 enforcing 정합) ────────
# 한글 주석: cycle 169.860 회수 — 신규 maildir 디렉토리 fcontext mail_spool_t 적용 의무
# dovecot_install.sh 가 /var/vmail 전체 fcontext 등록 후 신규 디렉토리도 restorecon 필요
if command -v restorecon &>/dev/null; then
  restorecon -R "${VMAIL_DOMAIN_DIR}/${USER_NAME}" 2>/dev/null || true
fi

# ─── 7 sasldb2 SMTP 자격 ───────────────────────────────────
# 한글 주석: 발신 (Postfix submission 587) 자격 동시 등록 — IMAP/SMTP 동일 자격 정합
# printf builtin = bash 내장 명령, process listing 노출 차단 (echo 도 builtin 이나 명시적 printf '%s' 패턴 권장)
printf '%s' "${PASSWORD}" | saslpasswd2 -c -u "${DOMAIN}" -p "${USER_NAME}"
chown postfix /etc/sasldb2 || true
chmod 640 /etc/sasldb2 || true

# ─── 8 서비스 reload ───────────────────────────────────────
# 한글 주석: config 변경 즉시 반영 — restart 회피 (기존 발신 큐 보존)
systemctl reload dovecot postfix 2>&1 | tail -3 || \
  systemctl restart dovecot postfix

# ─── 9 사용자 안내 stdout ──────────────────────────────────
echo
echo "════════════════════════════════════════════════════════════"
echo "  ${USER_EMAIL} 계정 생성 완료"
echo "════════════════════════════════════════════════════════════"
echo
echo "  USER     : ${USER_EMAIL}"
echo "  PASSWORD : ${PASSWORD}"
echo
echo "  IMAP host: ${HOSTNAME}"
echo "  IMAP port: 993 (SSL/TLS)"
echo
echo "  SMTP host: ${HOSTNAME}"
echo "  SMTP port: 587 (STARTTLS)"
echo
echo "════════════════════════════════════════════════════════════"
echo "  ⚠️ 본 패스워드 표시는 1회 — 안전한 곳에 즉시 보관"
echo "════════════════════════════════════════════════════════════"
