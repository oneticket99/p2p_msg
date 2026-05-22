-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0016 — 4 platform streaming OAuth token persistence.
-- 본 파일 = `server/db/migrations/0016_streaming_oauth_tokens.sql`. Phase 5 cycle 169.486.
-- 정합 = [[project_bot_framework]] §방송_도우미_봇 + [[feedback-db-schema-field-comments]].
-- 4 platform = Twitch + YouTube + CHZZK + Kick. 모든 컬럼 = 5요소 comment 의무.

-- =============================================================================
-- streaming_oauth_tokens 신설 — 사용자 platform 의 OAuth2 token persistence
-- =============================================================================

CREATE TABLE IF NOT EXISTS streaming_oauth_tokens (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT 'token row PK (AUTO_INCREMENT). 외부 노출 부재. 음수 부재 (UNSIGNED)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '소유 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 token row 삭제. 사용자 OAuth 권한 base',

  platform ENUM('twitch','youtube','chzzk','kick') NOT NULL
    COMMENT 'streaming platform 식별. twitch=Twitch IRC + Helix API / youtube=YouTube LiveChat API / chzzk=네이버 CHZZK / kick=Kick.com',

  access_token VARCHAR(512) NOT NULL
    COMMENT 'platform OAuth2 access_token (Bearer). PII + 보안 — 외부 노출 절대 금지. TLS 의무. 만료 시 refresh chain trigger',

  refresh_token VARCHAR(512) DEFAULT NULL
    COMMENT 'platform OAuth2 refresh_token. access_token 만료 시 재 발급 base. NULL = refresh 부재 (device code flow + 단기 token). PII + 보안',

  expires_at TIMESTAMP NOT NULL
    COMMENT 'access_token 만료 시각 (UTC). NOW() 비교 시 만료 detect → refresh trigger. platform 응답 expires_in 적용',

  scopes VARCHAR(255) DEFAULT NULL
    COMMENT 'OAuth2 scope list (공백 또는 콤마 구분). twitch=chat:read+chat:edit / youtube=youtube.readonly / 등. 검증 base',

  token_type VARCHAR(16) NOT NULL DEFAULT 'Bearer'
    COMMENT 'token type — 대부분 Bearer. RFC 6750 정합. NULL 부재 — default Bearer',

  channel_id VARCHAR(64) DEFAULT NULL
    COMMENT '연결 channel 식별자 (platform-specific). twitch=login / youtube=channel_id / chzzk=channel_id / kick=username. NULL = 부재',

  channel_login VARCHAR(64) DEFAULT NULL
    COMMENT 'channel 표시 이름 / login. twitch=login (소문자) / youtube=display_name / chzzk=channel_name. 검색 + UI 표기 base',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'token 발급 시각 (UTC). 통계 + 만료 시각 검증 base',

  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT 'token 마지막 갱신 시각 (UTC). refresh chain trigger 시점 자동 갱신',

  PRIMARY KEY (id),
  UNIQUE KEY uq_user_platform (user_id, platform)
    COMMENT '사용자 1명 안 platform 별 1 token 의무 (재 OAuth 시 UPSERT)',
  KEY idx_expires_at (expires_at)
    COMMENT '만료 임박 token 일괄 refresh chain — cron base',
  CONSTRAINT fk_streaming_oauth_user FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 5 cycle 169.486 — 4 platform streaming OAuth token persistence (Twitch + YouTube + CHZZK + Kick). 사용자 별 platform UNIQUE chain';
