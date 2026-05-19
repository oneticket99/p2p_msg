-- SPDX-License-Identifier: GPL-3.0-or-later
-- cycle 155 — message_reactions table 신설 (emoji + count chain)
-- 정합 = server/api/reactions_handlers.py (cycle 155 신설) + UNIQUE constraint.

CREATE TABLE IF NOT EXISTS message_reactions (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    message_id   BIGINT UNSIGNED NOT NULL COMMENT '대상 메시지 id (messages.id FK)',
    user_id      BIGINT UNSIGNED NOT NULL COMMENT 'reaction 추가 사용자 id (users.id FK)',
    emoji        VARCHAR(32) NOT NULL COMMENT 'Unicode emoji (BMP + supplementary plane, ZWJ sequence 회피)',
    created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'KST 등록 시각',
    PRIMARY KEY (id),
    UNIQUE KEY uniq_message_user_emoji (message_id, user_id, emoji)
        COMMENT '단일 사용자 + 단일 message + 단일 emoji = 1 reaction',
    KEY idx_message_emoji (message_id, emoji) COMMENT 'GROUP BY count query 가속',
    KEY idx_user_created (user_id, created_at) COMMENT '사용자 reaction history'
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='message reaction emoji + count + UNIQUE constraint (cycle 155 신설)';
