-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0007 — 친구 관계 영속화 (cycle 144).
-- 본 파일 = `server/db/migrations/0007_friends.sql`. Phase 1 친구 관리 chain —
-- 검색 + 추가 + 수락 + 차단 + 삭제 의 5 endpoint prerequisite. 그룹 채팅
-- invite_dialog (cycle 136) 의 friends dropdown 의 actual data 소스.
-- 정합 memory = [[feedback-db-schema-field-comments]] + [[feedback-db-audit-timestamp-ip-activity]].
-- 모든 컬럼 = 5요소 comment 의무 (용도 + 제약 + 값 출처 + 참조 + 민감도).

-- 한글 주석: TooTalk 친구 관계 — 단방향 row (user_id → friend_user_id) + status 흐름.
CREATE TABLE IF NOT EXISTS friends (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '친구 관계 PK (AUTO_INCREMENT). 외부 노출 부재 (내부 식별자). 음수 부재 (UNSIGNED)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '관계 owner 사용자 PK. users.id 외래키 (CASCADE DELETE). 양방향 관계 의 한쪽 row (반대 방향 = 별개 row). PII 부재 (FK 만)',

  friend_user_id BIGINT UNSIGNED NOT NULL
    COMMENT '관계 peer 사용자 PK. users.id 외래키 (CASCADE DELETE). user_id != friend_user_id 의 caller 검증 (자기 자신 친구 차단). PII 부재 (FK 만)',

  status ENUM('pending', 'accepted', 'blocked', 'removed') NOT NULL DEFAULT 'pending'
    COMMENT '관계 상태 — pending=요청 발신 후 수락 대기, accepted=수락 완료 (양방향 채팅 허용), blocked=차단 (메시지 차단), removed=관계 해제 (history 보존). 흐름 = pending → accepted → blocked/removed',

  nickname VARCHAR(64) DEFAULT NULL
    COMMENT 'owner 의 friend 표시 명 (별명). 최대 64자. NULL = 표시 = friend.username 폴백. UTF-8 한글 보존. PII 가능 (사용자 개인 별칭)',

  requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '친구 요청 발신 일시 (KST 기준 의도). DEFAULT CURRENT_TIMESTAMP. pending → accepted 전환 시점 = accepted_at 별개',

  accepted_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '수락 완료 일시 (KST 기준 의도). NULL = pending/blocked/removed 상태. status = accepted 전환 시 caller 의 UPDATE 의무',

  PRIMARY KEY (id),
  UNIQUE KEY uq_user_friend (user_id, friend_user_id),
  KEY idx_user_status (user_id, status),
  KEY idx_friend_status (friend_user_id, status),
  CONSTRAINT fk_friends_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_friends_friend
    FOREIGN KEY (friend_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 친구 관계 — cycle 144 신설 (검색 + 추가 + 수락 + 차단 + 삭제 의 5 endpoint prerequisite)';

-- 한글 주석: user_activity_log.action ENUM 확장 — friend_* 5 audit action 추가.
-- DDL 정합 = server/db/migrations/0003_user_activity.sql + ActivityAction 의 enum.
ALTER TABLE user_activity_log MODIFY action ENUM(
  'signup', 'signup_otp_verify',
  'login', 'logout', 'password_reset_request', 'password_reset_complete',
  'room_create', 'room_join', 'room_leave', 'room_close',
  'message_send', 'file_send', 'file_receive',
  'device_register', 'device_revoke',
  'bot_chat', 'bot_escalate',
  'remote_request', 'remote_grant', 'remote_revoke',
  'profile_update', 'email_change', 'account_delete',
  'friend_request', 'friend_accept', 'friend_reject',
  'friend_block', 'friend_remove'
) NOT NULL
  COMMENT '활동 종류. cycle 144 확장 — 22 + 5 친구 audit = 28 ENUM. 마케팅 funnel 분석 base';
