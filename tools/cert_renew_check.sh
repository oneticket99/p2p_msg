#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ==============================================================================
# cert_renew_check.sh — Let's Encrypt cert 만료 30일 알람 + certbot renew 검증
# ------------------------------------------------------------------------------
# 한글 주석 — TooTalk SMTP infra 의 Let's Encrypt fullchain 만료일 추적 스크립트
# 사용자 manual SSH 의 root crontab 등록 의무: 0 3 * * * /root/cert_renew_check.sh
#
# 사용:
#   bash tools/cert_renew_check.sh                                    # 기본 경로
#   bash tools/cert_renew_check.sh /etc/letsencrypt/live/X/fullchain.pem 30
#
# 인수:
#   $1 = cert 파일 경로 (기본 /etc/letsencrypt/live/mail.dopa.co.kr/fullchain.pem)
#   $2 = 알람 임계일 (기본 30일)
#
# 종료 코드:
#   0 = 정상 (또는 알람 발생 후 certbot dry-run 시도)
#   1 = cert 파일 부재
#
# 호환성: Rocky Linux 9.7 bash + macOS bash 3.2 (date GNU/BSD 양쪽 fallback)
# ==============================================================================

set -uo pipefail

# 한글 주석 — 기본 경로 + 임계일 (외부 인수 우선)
CERT_PATH=${1:-/etc/letsencrypt/live/mail.dopa.co.kr/fullchain.pem}
DAYS_WARN=${2:-30}

# 한글 주석 — cert 파일 존재 검증 (부재 시 즉시 비정상 종료)
if [ ! -f "$CERT_PATH" ] ; then
  echo "[cert-check] 🔴 cert 부재 — $CERT_PATH"
  exit 1
fi

# 한글 주석 — openssl x509 → notAfter 추출 → epoch 변환 (GNU date 우선 + BSD date fallback)
expiry_raw=$(openssl x509 -enddate -noout -in "$CERT_PATH" 2>/dev/null | sed 's/notAfter=//')
if [ -z "$expiry_raw" ] ; then
  echo "[cert-check] 🔴 openssl x509 파싱 실패 — $CERT_PATH"
  exit 1
fi

# 한글 주석 — GNU date 시도 (Rocky Linux 9.7) → 실패 시 BSD date fallback (macOS)
expiry_epoch=$(date -d "$expiry_raw" +%s 2>/dev/null || \
               date -j -f "%b %d %T %Y %Z" "$expiry_raw" +%s 2>/dev/null || \
               echo "0")

if [ "$expiry_epoch" = "0" ] ; then
  echo "[cert-check] 🔴 date 파싱 실패 — $expiry_raw"
  exit 1
fi

# 한글 주석 — 현재 epoch 대비 잔여 일수 계산 (86400초 = 1일)
now_epoch=$(date +%s)
days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

echo "[cert-check] 만료까지 ${days_left}일 — $CERT_PATH"

# 한글 주석 — 임계일 미만 시 알람 + certbot renew dry-run 검증 chain
if [ "$days_left" -lt "$DAYS_WARN" ] ; then
  echo "[cert-check] ⚠️ ${DAYS_WARN}일 미만 — certbot renew 실행 의무"
  if command -v certbot >/dev/null 2>&1 ; then
    certbot renew --dry-run 2>&1 | tail -10
  else
    echo "[cert-check] certbot 미설치 — 사용자 manual 갱신 의무"
  fi
fi

exit 0
