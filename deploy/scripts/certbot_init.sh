#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk Let's Encrypt 초기 인증서 발급 — Phase 4 cycle 112.
# 한글 주석: 본 script = 데모 서버 (114.207.112.73) 의 production 진입 시 1회 실행.
# webroot challenge + nginx 가동 상태 의무 (HTTP /well-known/acme-challenge/ proxy 활성).

set -euo pipefail

DOMAIN="${TLS_PRIMARY_DOMAIN:-tootalk.demo}"
ACME_EMAIL="${ACME_EMAIL:-admin@${DOMAIN}}"
WEBROOT_PATH="${WEBROOT_PATH:-/var/www/certbot}"
STAGING="${CERTBOT_STAGING:-0}"
CERTBOT_IMAGE="${CERTBOT_IMAGE:-certbot/certbot:latest}"

if [ -z "$ACME_EMAIL" ]; then
    echo "[certbot_init] ACME_EMAIL env 의무" >&2
    exit 1
fi

# staging flag — Let's Encrypt 의 production rate limit 회피 (test 단계)
EXTRA_ARGS=""
if [ "$STAGING" = "1" ]; then
    EXTRA_ARGS="--staging"
    echo "[certbot_init] STAGING mode active (실 인증서 부재)"
fi

echo "[certbot_init] domain=${DOMAIN} email=${ACME_EMAIL} webroot=${WEBROOT_PATH}"

docker run --rm \
    -v letsencrypt:/etc/letsencrypt \
    -v "${WEBROOT_PATH}:${WEBROOT_PATH}" \
    "$CERTBOT_IMAGE" certonly \
    --webroot --webroot-path="$WEBROOT_PATH" \
    --email "$ACME_EMAIL" \
    --agree-tos --no-eff-email \
    --rsa-key-size 2048 \
    -d "$DOMAIN" \
    -d "mail.${DOMAIN}" \
    $EXTRA_ARGS

echo "[certbot_init] 발급 완료. nginx reload 의무:"
echo "  docker compose -f deploy/docker-compose.yml exec nginx nginx -s reload"
