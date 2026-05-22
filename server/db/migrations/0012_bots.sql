-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0012 — bot framework BotFather 등가 base.
-- 본 파일 = `server/db/migrations/0012_bots.sql`. Phase 3+ 차별화 — 외부 개발자 봇 등록.
-- 정합 memory = [[project_bot_framework]] + [[feedback-db-schema-field-comments]].
-- 모든 컬럼 = 5요소 comment 의무 (용도/제약/값 출처/참조 관계/민감도).

-- =============================================================================
-- 1) bots 신설 — 외부 개발자 봇 등록 메타 + webhook URL + public 디렉토리
-- =============================================================================

CREATE TABLE IF NOT EXISTS bots (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '봇 PK (AUTO_INCREMENT). 외부 노출 가능. 음수 부재 (UNSIGNED)',

  owner_user_id BIGINT UNSIGNED NOT NULL
    COMMENT '봇 소유 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 봇 row 도 삭제. 봇 제어 권한 base',

  name VARCHAR(64) NOT NULL
    COMMENT '봇 표시 이름 (사용자 표기 + UTF-8 한글 가능). 64자 cap. 검색 + 디렉토리 카드 base',

  username VARCHAR(32) NOT NULL
    COMMENT '봇 username (lowercase + _ + 숫자, ASCII). UNIQUE 의무. `@bot_name` mention 식별. BotFather 등가 정합',

  description VARCHAR(255) DEFAULT NULL
    COMMENT '봇 설명 텍스트. 255자 cap. 공개 디렉토리 카드 + /start command 응답 base. NULL = 설명 부재',

  webhook_url VARCHAR(512) DEFAULT NULL
    COMMENT '봇 webhook endpoint URL (HTTPS strict). TooTalk → 봇 message forward POST 대상. NULL = polling 모드',

  inline_enabled TINYINT(1) NOT NULL DEFAULT 0
    COMMENT 'inline mode 활성 (0=비활성, 1=활성). inline query 처리 가능 여부. 텔레그램 inline pattern 정합',

  is_public TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '공개 디렉토리 노출 (0=비공개 owner only, 1=공개). 기본 0 — owner 명시 publish 의무',

  status ENUM('active', 'disabled', 'banned') NOT NULL DEFAULT 'active'
    COMMENT '봇 상태 3 ENUM. active=정상 운영, disabled=owner 임시 비활성, banned=admin 차단 (TOS 위반)',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '봇 등록 시각 (UTC, KST +09:00 변환 = caller). 마케팅 시계열 분석 base',

  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT '봇 갱신 시각 (UTC). webhook_url / description / status 변경 시 자동 갱신',

  PRIMARY KEY (id),
  UNIQUE KEY uq_bots_username (username),
  KEY idx_bots_owner (owner_user_id),
  KEY idx_bots_public_status (is_public, status),
  CONSTRAINT fk_bots_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 3+ bot framework BotFather 등가 — 외부 개발자 봇 등록 디렉토리 (cycle 169.420)';


-- =============================================================================
-- 2) bot_tokens 신설 — 봇 인증 token (HMAC-SHA256 해시 저장)
-- =============================================================================

CREATE TABLE IF NOT EXISTS bot_tokens (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '토큰 PK (AUTO_INCREMENT). 음수 부재',

  bot_id BIGINT UNSIGNED NOT NULL
    COMMENT '소속 봇 PK (bots.id 외래키). CASCADE DELETE — 봇 삭제 시 token row 도 삭제',

  token_hash CHAR(64) NOT NULL
    COMMENT 'token SHA-256 해시 (hex 소문자 64자). plaintext 절대 저장 부재 — 사용자 directive 보안 의무. 봇 인증 = client token plaintext → SHA-256 → table lookup',

  label VARCHAR(64) DEFAULT NULL
    COMMENT 'token 식별 라벨 (예: "production", "dev"). 64자 cap. 사용자 표기 + revoke target 식별 base. NULL = label 부재',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'token 생성 시각 (UTC)',

  last_used_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'token 마지막 사용 시각 (UTC). NULL = 미사용. 활동 추적 + idle revoke base',

  revoked_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '토큰 revoke 시각 (UTC). NULL = 활성, NOT NULL = revoked (인증 차단)',

  PRIMARY KEY (id),
  UNIQUE KEY uq_bot_tokens_hash (token_hash),
  KEY idx_bot_tokens_bot (bot_id),
  CONSTRAINT fk_bot_tokens_bot FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='봇 인증 token — SHA-256 해시 저장. Phase 3+ bot framework token rotation chain';
