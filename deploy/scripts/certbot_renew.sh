#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk Let's Encrypt 인증서 갱신 — Phase 4 cycle 112.
# 한글 주석: cron 등록 의무 (매일 03:00 KST). 60일 cutoff 도달 시 자동 갱신.
# usage: 0 3 * * * /opt/tootalk/deploy/scripts/certbot_renew.sh

set -euo pipefail

CERTBOT_IMAGE="${CERTBOT_IMAGE:-certbot/certbot:latest}"
WEBROOT_PATH="${WEBROOT_PATH:-/var/www/certbot}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/tootalk/deploy/docker-compose.yml}"

echo "[certbot_renew] $(date '+%Y-%m-%d %H:%M:%S KST') 갱신 시도"

docker run --rm \
    -v letsencrypt:/etc/letsencrypt \
    -v "${WEBROOT_PATH}:${WEBROOT_PATH}" \
    "$CERTBOT_IMAGE" renew \
    --webroot --webroot-path="$WEBROOT_PATH" \
    --quiet --no-random-sleep-on-renew

# 갱신 발생 시점 nginx reload (live config swap 의무)
if docker compose -f "$COMPOSE_FILE" ps nginx --status running >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t \
        && docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload
    echo "[certbot_renew] nginx reload 완료"
else
    echo "[certbot_renew] nginx 미가동 — reload skip"
fi
