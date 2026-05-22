-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0014 — 읽음 상태 추적 (cycle 169.447 신설).
-- 사용자 directive — 안 읽음 라벨 정식 chain. 읽음 처리 = chat 포커스 시점 last_read 갱신.

CREATE TABLE IF NOT EXISTS read_states (
  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '읽음 주체 사용자 PK (users.id FK). CASCADE DELETE',

  room_id BIGINT UNSIGNED NOT NULL
    COMMENT '룸 PK (rooms.id FK). CASCADE DELETE',

  last_read_msg_id BIGINT UNSIGNED NOT NULL DEFAULT 0
    COMMENT '본 사용자 의 본 룸 안 마지막 읽음 messages.id. chat focus 시점 갱신. msg_id > last_read = 안 읽음 판정 base',

  last_read_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT '마지막 읽음 처리 시각 (UTC). 통계 + read receipt 시계열 base',

  PRIMARY KEY (user_id, room_id),
  KEY idx_read_states_room (room_id),
  CONSTRAINT fk_read_states_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_read_states_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='cycle 169.447 — 읽음 상태 추적. user_id + room_id 복합 PK + last_read_msg_id 갱신 chain';
