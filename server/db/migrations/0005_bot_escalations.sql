-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0005 — bot 사람 상담 escalation 영속화.
-- 본 파일 = `server/db/migrations/0005_bot_escalations.sql`. Phase 3 cycle 86
-- 의 in-memory EscalationQueue 의 production 진입 prerequisite — DB 영속화.
-- 정합 memory = [[project_bot_framework]] + [[feedback-db-schema-field-comments]].
-- 모든 컬럼 = 5요소 comment 의무.

-- 한글 주석: bot framework 의 사람 상담 ticket — jailbreak / rate limit / 사용자 요청 등 의 escalation
CREATE TABLE IF NOT EXISTS bot_escalations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT 'escalation ticket PK (AUTO_INCREMENT). EscalationQueue next_ticket_id 의 in-memory 등가 대체. 외부 노출 가능 (사용자 의 ticket 번호 표시)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '요청 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 본 row 도 삭제. 음수 부재 (UNSIGNED)',

  reason ENUM(
    'user_request',
    'jailbreak',
    'rate_limit',
    'low_confidence',
    'long_response',
    'explicit'
  ) NOT NULL
    COMMENT 'escalation 사유 6 ENUM. user_request=사용자 명시 요청, jailbreak=BLOCKED detection 의 escalation, rate_limit=분당 cap 초과, low_confidence=LLM 응답 의 confidence 임계 미달, long_response=LLM 응답 의 길이 임계 초과, explicit=명시 escalation. EscalationReason Enum 정합',

  message TEXT NOT NULL
    COMMENT '사용자 의 원본 메시지 본문. UTF-8 한글 보존. 16 KB cap (Phase 3 bot_handlers _MAX_CONTENT_BYTES 정합). PII 제외 의무 (jailbreak detector 통과 본문 만)',

  status ENUM(
    'pending',
    'assigned',
    'resolved',
    'closed'
  ) NOT NULL DEFAULT 'pending'
    COMMENT 'ticket 상태 4 ENUM. pending=대기, assigned=상담원 배정, resolved=해결, closed=종료. TicketStatus Enum 정합. lifecycle: pending → assigned → resolved → closed',

  agent_id BIGINT UNSIGNED NULL DEFAULT NULL
    COMMENT '배정 상담원 PK (users.id 외래키 의 의도, 단 FK 부재 — 일반 사용자 의 자동 배정 부재 의 정합). NULL = 미배정 (pending). 양수 = 배정 완료 (assigned 이후)',

  created_at_ms BIGINT UNSIGNED NOT NULL
    COMMENT 'ticket 생성 시각 (Unix epoch ms). EscalationTicket created_at_ms 의 직접 대응. UTC 기준. KST 변환 = caller 영역',

  resolved_at_ms BIGINT UNSIGNED NULL DEFAULT NULL
    COMMENT 'ticket 해결/종료 시각 (Unix epoch ms). NULL = pending/assigned. NOT NULL = resolved/closed. evict_old retention cutoff 의 base',

  PRIMARY KEY (id),
  KEY idx_bot_escalations_user_status (user_id, status),
  KEY idx_bot_escalations_status_created (status, created_at_ms),
  KEY idx_bot_escalations_agent (agent_id, status),
  KEY idx_bot_escalations_resolved (resolved_at_ms),
  CONSTRAINT fk_bot_escalations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 3 bot framework 사람 상담 escalation ticket — cycle 86 in-memory EscalationQueue 의 DB 영속화 (cycle 125)';
