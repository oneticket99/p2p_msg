#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# 한글 주석 — encrypted backup master key 만료 30일 알람 + rotation 명령 안내
# 사용자 manual SSH cron 등록 의무:
#   0 4 * * 0 /root/backup_rotate_check.sh (일요일 04:00 KST 주간 점검)
set -uo pipefail

KEY_META=${1:-/etc/tootalk/keys/active.json}
WARN_DAYS=${2:-30}
ROTATION_DAYS=${3:-180}

if [ ! -f "$KEY_META" ]; then
  echo "[backup-rotate] 🔴 key meta 부재 — $KEY_META"
  echo "[backup-rotate] → /etc/tootalk/keys/ 초기화 후 재실행 의무"
  exit 1
fi

# 한글 주석 — rotated_at_kst ISO 추출 (python3 의 JSON parse)
last_rotated=$(python3 -c "import json,sys; print(json.load(open('$KEY_META')).get('rotated_at_kst',''))" 2>/dev/null)
if [ -z "$last_rotated" ]; then
  echo "[backup-rotate] ⚠️ rotated_at_kst 부재 — rotation 의무 (즉시 실행 권장)"
  exit 0
fi

echo "[backup-rotate] last rotated = $last_rotated"
echo "[backup-rotate] policy = ${ROTATION_DAYS} day rotation + ${WARN_DAYS} day warn"

# 한글 주석 — 만료일 계산 + 사용자 manual rotation 권장 출력
python3 - "$last_rotated" "$WARN_DAYS" "$ROTATION_DAYS" <<'EOF'
import sys
from datetime import datetime, timezone, timedelta

kst = timezone(timedelta(hours=9))
last_iso, warn_days, rotation_days = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

try:
    last = datetime.fromisoformat(last_iso)
except (ValueError, TypeError):
    print(f"  🔴 invalid timestamp = {last_iso!r} — rotation 의무")
    sys.exit(0)

if last.tzinfo is None:
    last = last.replace(tzinfo=kst)

delta = datetime.now(kst) - last
remain = rotation_days - delta.days

if remain < 0:
    print(f"  🔴 rotation 의무 경과 {-remain}일 — 즉시 rotation 필수")
elif remain < warn_days:
    print(f"  ⚠️ rotation 의무 {remain}일 — 사용자 manual rotation 권장")
else:
    print(f"  ✅ rotation 의무 {remain}일 남음 ({rotation_days} day policy)")
EOF
