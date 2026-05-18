#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk postfix entrypoint — Phase 4 환경 변수 치환 + DKIM 키 생성.
# 한글 주석: MAILDOMAIN + DKIM_SELECTOR env 의 postfix/opendkim config 치환.

set -euo pipefail

MAILDOMAIN="${MAILDOMAIN:-tootalk.demo}"
DKIM_SELECTOR="${DKIM_SELECTOR:-tootalk}"
DKIM_KEY_DIR="/etc/opendkim/keys"

echo "[entrypoint] MAILDOMAIN=${MAILDOMAIN} DKIM_SELECTOR=${DKIM_SELECTOR}"

# postfix hostname + origin 치환
postconf -e "myhostname = mail.${MAILDOMAIN}"
postconf -e "mydomain = ${MAILDOMAIN}"
postconf -e "myorigin = ${MAILDOMAIN}"
postconf -e "mydestination = mail.${MAILDOMAIN}, localhost.${MAILDOMAIN}, localhost"

# opendkim KeyTable + SigningTable 의 placeholder 치환
sed -i \
    -e "s/tootalk\.demo/${MAILDOMAIN}/g" \
    -e "s/^tootalk\._domainkey/${DKIM_SELECTOR}._domainkey/g" \
    -e "s|/etc/opendkim/keys/tootalk\.private|${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private|g" \
    /etc/opendkim/KeyTable
sed -i \
    -e "s/tootalk\.demo/${MAILDOMAIN}/g" \
    -e "s/tootalk\._domainkey/${DKIM_SELECTOR}._domainkey/g" \
    /etc/opendkim/SigningTable

# DKIM 키 부재 시 자동 생성 (개발 환경 의무. production 은 host volume mount 의 미리 배포 키)
if [ ! -f "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private" ]; then
    echo "[entrypoint] DKIM 키 부재 — 자동 생성 (개발 환경)"
    mkdir -p "${DKIM_KEY_DIR}"
    opendkim-genkey -b 2048 -d "${MAILDOMAIN}" -s "${DKIM_SELECTOR}" -D "${DKIM_KEY_DIR}"
    mv "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private" "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private"
    chown -R opendkim:opendkim "${DKIM_KEY_DIR}"
    chmod 600 "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private"
    echo "[entrypoint] DKIM TXT record (DNS 등록 의무):"
    cat "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.txt"
fi

# 키 권한 회수 (volume mount 의 chown 문제 회피)
chown -R opendkim:opendkim "${DKIM_KEY_DIR}" || true
chmod 600 "${DKIM_KEY_DIR}/${DKIM_SELECTOR}.private" || true

exec "$@"
