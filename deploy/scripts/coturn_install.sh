#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk coturn install + config + iptables — Rocky 9 idempotent (cycle 169.81 신설).
#
# 데모 서버 (114.207.112.73) — TURN realm = tootalk.demo, port 3478 UDP/TCP + 5349 TLS.
# 사용자 directive 2026-05-20 — "사용자 테스트 외의 모든 작업 다 진행해" ack 정합.
# CLAUDE.md §10-6 + project_smtp_demo_server pattern 정합.
#
# env 의무:
#   TURN_REALM       — TURN realm (default "tootalk.demo")
#   TURN_USER        — TURN static auth user (default "tootalk")
#   TURN_PASSWORD    — TURN static auth password (필수)
#   EXTERNAL_IP      — server public IP (default 114.207.112.73)
#   MIN_PORT         — relay port range start (default 49152)
#   MAX_PORT         — relay port range end (default 65535)
#
# 사용 path:
#   sudo TURN_PASSWORD='xxx' bash coturn_install.sh
#
# idempotent — 재 run 시 dnf install 무 op + config 갱신 + service restart 만.

set -euo pipefail

# 한글 주석 — 환경변수 default + 필수 변수 검증
TURN_REALM="${TURN_REALM:-tootalk.demo}"
TURN_USER="${TURN_USER:-tootalk}"
TURN_PASSWORD="${TURN_PASSWORD:-}"
EXTERNAL_IP="${EXTERNAL_IP:-114.207.112.73}"
MIN_PORT="${MIN_PORT:-49152}"
MAX_PORT="${MAX_PORT:-65535}"

if [[ -z "$TURN_PASSWORD" ]]; then
    echo "ERROR: TURN_PASSWORD env 필수 — TURN static auth credential" >&2
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: root 권한 필수 — sudo 의 의 run" >&2
    exit 1
fi

# 한글 주석 — Rocky 9 EPEL 활성 + coturn package install
echo "[coturn_install] EPEL 활성 + coturn install"
dnf install -y epel-release || true
dnf install -y coturn

# 한글 주석 — /etc/turnserver.conf 작성 (idempotent overwrite)
echo "[coturn_install] /etc/turnserver.conf 작성"
cat > /etc/turnserver.conf <<EOF
# TooTalk TURN server — cycle 169.81 신설
listening-port=3478
tls-listening-port=5349
listening-ip=0.0.0.0
external-ip=${EXTERNAL_IP}
relay-ip=${EXTERNAL_IP}
min-port=${MIN_PORT}
max-port=${MAX_PORT}

fingerprint
lt-cred-mech
realm=${TURN_REALM}

user=${TURN_USER}:${TURN_PASSWORD}

# TLS — Let's Encrypt cert (postfix 의 의 cert 재 사용)
cert=/etc/letsencrypt/live/${TURN_REALM}/fullchain.pem
pkey=/etc/letsencrypt/live/${TURN_REALM}/privkey.pem

# logging
log-file=/var/log/turnserver/turnserver.log
simple-log
verbose

# security — disable loopback peer + 사설 IP 차단
no-loopback-peers
no-multicast-peers
denied-peer-ip=0.0.0.0-0.255.255.255
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=127.0.0.0-127.255.255.255
denied-peer-ip=169.254.0.0-169.254.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.0.0.0-192.0.0.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=198.18.0.0-198.19.255.255
EOF

chmod 640 /etc/turnserver.conf

# 한글 주석 — /etc/sysconfig/coturn TURNSERVER_ENABLED=1
echo "[coturn_install] /etc/sysconfig/coturn 활성"
if [[ -f /etc/sysconfig/coturn ]]; then
    sed -i 's/^#*TURNSERVER_ENABLED=.*/TURNSERVER_ENABLED=1/' /etc/sysconfig/coturn
else
    echo "TURNSERVER_ENABLED=1" > /etc/sysconfig/coturn
fi

# 한글 주석 — log directory + permission
mkdir -p /var/log/turnserver
chown turnserver:turnserver /var/log/turnserver 2>/dev/null || true

# 한글 주석 — iptables ACCEPT — 3478 UDP/TCP + 5349 TCP + 49152~65535 UDP
echo "[coturn_install] iptables ACCEPT"
iptables -I INPUT -p udp --dport 3478 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p tcp --dport 3478 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p tcp --dport 5349 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p udp --dport "${MIN_PORT}:${MAX_PORT}" -j ACCEPT 2>/dev/null || true

# 한글 주석 — service enable + restart
echo "[coturn_install] coturn service enable + restart"
systemctl enable coturn
systemctl restart coturn

# 한글 주석 — status check
sleep 2
if systemctl is-active --quiet coturn; then
    echo "[coturn_install] SUCCESS — coturn active"
    echo "[coturn_install] TURN url = turn:${EXTERNAL_IP}:3478?transport=udp"
    echo "[coturn_install] TURNS url = turns:${TURN_REALM}:5349?transport=tcp"
    echo "[coturn_install] user = ${TURN_USER}"
    exit 0
else
    echo "[coturn_install] FAIL — coturn inactive" >&2
    journalctl -u coturn -n 30 --no-pager >&2 || true
    exit 1
fi
