#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk 테스트 계정 초기화 — porory99@gmail.com 외 사용자 + FK 종속 row 의 전수 삭제.
# 한글 주석 — 사용자 directive cycle 169.473 — 회원가입 재시도 의 의무 cleanup chain.
#
# Usage:
#     bash tools/reset_test_users.sh                # 기본 — porory99 retain
#     KEEP_EMAIL="foo@bar.com" bash tools/reset_test_users.sh  # 다른 email retain
#     KEEP_EMAIL="" bash tools/reset_test_users.sh   # 전수 삭제 (위험)
#
# 환경 변수:
#     SSH_HOST       — demo server (default 114.207.112.73)
#     DB_CONTAINER   — MariaDB container (default tootalk-mariadb)
#     DB_NAME        — DB name (default tootalk)
#     DB_USER        — DB user (default root)
#     DB_PASSWORD    — DB root password (default 데모 server hardcode)
#     KEEP_EMAIL     — retain email (default porory99@gmail.com)

set -euo pipefail

SSH_HOST="${SSH_HOST:-114.207.112.73}"
DB_CONTAINER="${DB_CONTAINER:-tootalk-mariadb}"
DB_NAME="${DB_NAME:-tootalk}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-b5298b6a144d94f79d8a21542fe75a3a}"
KEEP_EMAIL="${KEEP_EMAIL:-porory99@gmail.com}"
DRY_RUN="${DRY_RUN:-1}"   # 한글 주석 — default 1 (preview). DELETE 의 실행 의 의무 DRY_RUN=0 명시

# 한글 주석 — KEEP_EMAIL 인자 안 SQL injection 회피 의무 (영문/숫자/특수문자 의 제한)
if [[ -n "${KEEP_EMAIL}" && ! "${KEEP_EMAIL}" =~ ^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$ ]]; then
    echo "[reset] KEEP_EMAIL 형식 오류 — '${KEEP_EMAIL}'" >&2
    exit 1
fi

mysql() {
    # 한글 주석 — ssh + docker exec + mariadb wrapper. stdin SQL 안 heredoc 의무.
    # -e 인자 사용 시 `-e SQL` 형태 의 ssh 안 quote 손실 회피 — heredoc/<<<만 사용.
    ssh "root@${SSH_HOST}" "docker exec -i ${DB_CONTAINER} mariadb -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME} $*"
}

mysql_query() {
    # 한글 주석 — SQL stdin 의무 wrapper (mysql -e 의 argument quote 손실 회피)
    local opts="${1:-}"
    local sql="${2}"
    ssh "root@${SSH_HOST}" "docker exec -i ${DB_CONTAINER} mariadb -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME} ${opts}" <<< "${sql}"
}

echo "[reset] target = ${SSH_HOST}/${DB_CONTAINER}/${DB_NAME}"
echo "[reset] KEEP_EMAIL = '${KEEP_EMAIL}' (빈 문자열 = 전수 삭제)"
echo "[reset] DRY_RUN = ${DRY_RUN} (1=preview 만, 0=실제 DELETE)"
echo

# 한글 주석 — 직전 사용자 row count snapshot
echo "[reset] 직전 사용자 row count:"
mysql_query "-N" "SELECT COUNT(*) AS users_count FROM users;"

if [[ -z "${KEEP_EMAIL}" ]]; then
    USERS_WHERE="1=1"
    EV_WHERE="1=1"
else
    USERS_WHERE="email != '${KEEP_EMAIL}'"
    EV_WHERE="email != '${KEEP_EMAIL}'"
fi

echo
echo "[reset] 삭제 대상 사용자 preview (WHERE ${USERS_WHERE}):"
mysql_query "" "SELECT id, email, username FROM users WHERE ${USERS_WHERE};"

if [[ "${DRY_RUN}" != "0" ]]; then
    echo
    echo "[reset] DRY_RUN=1 — preview 만 출력. 실제 삭제 의무 시점 'DRY_RUN=0 bash $0' 재실행."
    exit 0
fi

echo
echo "[reset] cleanup 실행 — users WHERE ${USERS_WHERE}"
mysql_query "" "$(cat <<SQL
SET FOREIGN_KEY_CHECKS = 0;
DELETE FROM email_verification WHERE ${EV_WHERE};
DELETE FROM password_reset WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM user_activity_log WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM user_contacts WHERE owner_user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM friends WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE}) OR friend_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM device_tokens WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM devices WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM folders WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM read_states WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM file_meta WHERE owner_user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM peers WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM messages WHERE sender_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM bot_escalations WHERE user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM bots WHERE owner_user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM emoji_packs WHERE owner_user_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM rooms WHERE owner_id IN (SELECT id FROM users WHERE ${USERS_WHERE});
DELETE FROM users WHERE ${USERS_WHERE};
SET FOREIGN_KEY_CHECKS = 1;
SQL
)"

echo
echo "[reset] cleanup 직후 사용자:"
mysql_query "" "SELECT id, email, username, email_verified FROM users;"
echo
echo "[reset] cleanup 직후 email_verification:"
mysql_query "-N" "SELECT COUNT(*) AS ev_count FROM email_verification;"
echo
echo "[reset] 완료 — 신규 회원가입 GO"
