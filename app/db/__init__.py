# SPDX-License-Identifier: GPL-3.0-or-later
"""local SQLite cache — 클라이언트 PC 안 대화 내용 영속 (cycle 169.440 신설).

memory `feedback_local_sqlite_cache` (cycle 169.440 사용자 directive) 정합:
- MariaDB + local SQLite 동시 저장 (write-through)
- 어플 설치 PC 안 대화 영속 → MariaDB 서버 부하 분담
- scroll lazy-load = SQLite 안 부재 msg 시점 MariaDB fetch → SQLite sync
- 자동 업데이트 cycle 시점 schema migration chain 의무

본 module:
- `local_db.get_connection()` — SQLite singleton + schema bootstrap
- `messages_cache.insert_message()` — single msg INSERT (write-through path)
- `messages_cache.list_messages_by_room()` — local cache 안 paginated SELECT
- `messages_cache.get_min_msg_id()` — lazy-load 진입 cursor

본 cycle 의 범위 외 (별 cycle):
- 실 scroll-up lazy-load UI 호출 chain
- MariaDB sync conflict resolution (서버 truth + local follow)
- 자동 업데이트 시점 schema migration 의무 (별 cycle)
"""
