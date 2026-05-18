-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0003 — 사용자 활동 추적 + IP 기록.
-- 본 파일 = `server/db/migrations/0003_user_activity.sql`. 사용자 directive 2026-05-22
-- "회원 가입 시 db 업데이트 인서트 할때에 datetime 반드시 남기도록해. 마케팅 통계 자료 활용 + 접속자 IP + 접속 시간 + 활동 시간 추적".
-- 정합 memory = [[feedback-db-audit-timestamp-ip-activity]].
-- 모든 컬럼 = comment 의무 정합 ([[feedback-db-schema-field-comments]]).

-- =============================================================================
-- 1) users 테이블 확장 — 가입 IP + 마지막 로그인 IP + 활동 시각 + User-Agent
-- =============================================================================

-- 한글 주석: users 의 가입 IP + User-Agent 추가 — 마케팅 funnel 분석 + 부정 가입 IP 차단
ALTER TABLE users
  ADD COLUMN signup_ip VARCHAR(45) NULL DEFAULT NULL
    COMMENT '회원가입 시 클라이언트 IP. IPv4 (최대 15자) 또는 IPv6 (최대 45자, RFC 4291). nginx X-Forwarded-For header 의 parse 결과 (Phase 4 cycle 109). PII — 90일 후 hash/truncate 의무 ([[feedback-db-audit-timestamp-ip-activity]] §8). NULL = 마이그레이션 이전 가입 사용자 (회수 무, 그대로 보존)'
    AFTER status,
  ADD COLUMN signup_user_agent VARCHAR(255) NULL DEFAULT NULL
    COMMENT '회원가입 시 User-Agent header. 클라이언트 분포 통계 (TooTalk-Desktop/macOS, TooTalk-Desktop/Windows, brand 별 점유율). 255자 cap (오버플로우 시 truncate)'
    AFTER signup_ip,
  ADD COLUMN last_login_ip VARCHAR(45) NULL DEFAULT NULL
    COMMENT '마지막 로그인 시 클라이언트 IP. 의심 활동 감지 (지역 이상 + 짧은 시간 내 다른 IP 다중 로그인 등). 매 로그인 시 갱신. PII = 90일 hash/truncate'
    AFTER last_login_at,
  ADD COLUMN last_activity_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '마지막 활동 시각 (UTC, 모든 API 호출 + 메시지 송수신 + 시그널링 ping 의 trigger). DAU/MAU 정의 base. aiohttp middleware 가 1분 throttle 로 갱신 (write storm 회피). NULL = 가입 후 미활동'
    AFTER last_login_ip,
  ADD KEY idx_users_last_activity (last_activity_at),
  ADD KEY idx_users_signup_ip (signup_ip);


-- =============================================================================
-- 2) user_sessions 테이블 신설 — 접속 세션 추적 (IP + 접속 시간 + 활동 시간)
-- =============================================================================

-- 한글 주석: 사용자 접속 세션 — 1 로그인 의 1 row. 세션 시작/종료/지속시간 추적
CREATE TABLE IF NOT EXISTS user_sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '세션 레코드 PK (AUTO_INCREMENT)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '소속 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 본 row 도 삭제',

  session_token_hash CHAR(64) NOT NULL
    COMMENT '세션 토큰 (JWT 또는 Bearer) 의 SHA-256 hex (64자). 평문 저장 절대 금지. revoke 시 본 row delete 또는 disconnected_at 갱신',

  ip_address VARCHAR(45) NOT NULL
    COMMENT '세션 접속 IP. IPv4 (15자) 또는 IPv6 (45자). nginx X-Forwarded-For header parse 결과. PII = 90일 hash/truncate 의무',

  user_agent VARCHAR(255) NULL DEFAULT NULL
    COMMENT '세션 User-Agent header. 클라이언트 OS / 버전 통계. 255자 cap',

  connected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '세션 시작 시각 (UTC, 로그인 직후). 마케팅 일/시간대 별 활성 사용자 분포 분석 base',

  last_active_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '본 세션 의 마지막 활동 시각 (UTC). API 호출 + WS message + 시그널링 ping 시마다 갱신 (1분 throttle). 세션 idle timeout 판정 base',

  disconnected_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '세션 종료 시각 (UTC). NULL = 활성 세션, NOT NULL = 종료 (명시적 logout 또는 idle timeout). 활성 세션 조회 = WHERE disconnected_at IS NULL',

  duration_seconds INT UNSIGNED NULL DEFAULT NULL
    COMMENT '세션 지속 시간 (초). disconnected_at - connected_at 의 계산값 (disconnect 시점 의). 평균 세션 시간 + 사용자 engagement 통계',

  end_reason ENUM('logout', 'idle_timeout', 'token_revoke', 'force_disconnect', 'server_restart') NULL DEFAULT NULL
    COMMENT '세션 종료 사유. logout=명시적 로그아웃, idle_timeout=비활성 timeout, token_revoke=관리자 강제 revoke, force_disconnect=다른 기기 로그인 등, server_restart=서버 재시작 시 일괄 종료',

  PRIMARY KEY (id),
  UNIQUE KEY uq_user_sessions_token (session_token_hash),
  KEY idx_user_sessions_user_connected (user_id, connected_at),
  KEY idx_user_sessions_active (user_id, disconnected_at),
  KEY idx_user_sessions_ip (ip_address),
  KEY idx_user_sessions_last_active (last_active_at),
  CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 + 마케팅 통계용 사용자 접속 세션 추적. IP + 접속 시간 + 활동 시간 + 종료 사유 (사용자 directive 2026-05-22)';


-- =============================================================================
-- 3) user_activity_log 테이블 신설 — 주요 action audit log (마케팅 funnel)
-- =============================================================================

-- 한글 주석: 사용자 활동 로그 — 주요 action 의 audit + 마케팅 funnel 분석 base
CREATE TABLE IF NOT EXISTS user_activity_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '활동 로그 PK (AUTO_INCREMENT)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '활동 사용자 PK (users.id 외래키). CASCADE DELETE',

  action ENUM(
    'signup', 'signup_otp_verify',
    'login', 'logout', 'password_reset_request', 'password_reset_complete',
    'room_create', 'room_join', 'room_leave', 'room_close',
    'message_send', 'file_send', 'file_receive',
    'device_register', 'device_revoke',
    'bot_chat', 'bot_escalate',
    'remote_request', 'remote_grant', 'remote_revoke',
    'profile_update', 'email_change', 'account_delete'
  ) NOT NULL
    COMMENT '활동 종류. 주요 action 22종 + 별개 cycle 의 확장 가능. 마케팅 funnel 분석 (가입 → 첫 메시지 → DAU/MAU) base',

  target_id BIGINT UNSIGNED NULL DEFAULT NULL
    COMMENT '활동 대상 ID (room_id / target_user_id / device_id 등). action 별 의미 상이 (예: message_send 시 room_id, device_register 시 device_id). NULL = 대상 없는 action (login 등)',

  ip_address VARCHAR(45) NULL DEFAULT NULL
    COMMENT '활동 발생 IP. nginx X-Forwarded-For 의 parse. PII = 90일 hash/truncate. NULL = 서버 내부 trigger (cron 등)',

  user_agent VARCHAR(255) NULL DEFAULT NULL
    COMMENT '활동 발생 User-Agent. 클라이언트 분포 통계',

  metadata JSON NULL DEFAULT NULL
    COMMENT '활동 부가 정보 JSON. action 별 schema 상이 (예: bot_chat 시 {"provider": "anthropic", "tokens": 128}). PII (이메일 / 비번 / 토큰 평문) 절대 금지 — sensitive_redact 의 server-side 정합',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '활동 시각 (UTC). 마케팅 funnel 시계열 분석 base',

  PRIMARY KEY (id),
  KEY idx_user_activity_user_created (user_id, created_at),
  KEY idx_user_activity_action_created (action, created_at),
  KEY idx_user_activity_ip (ip_address),
  KEY idx_user_activity_target (target_id),
  CONSTRAINT fk_user_activity_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='마케팅 통계 + audit 용 사용자 활동 로그. 주요 action 22종 + 시계열 funnel 분석 base (사용자 directive 2026-05-22)';


-- =============================================================================
-- 4) email_verification + password_reset 확장 — 발급 IP 추가
-- =============================================================================

-- 한글 주석: OTP 발급 IP 추적 — 부정 가입 / brute force 차단
ALTER TABLE email_verification
  ADD COLUMN requester_ip VARCHAR(45) NULL DEFAULT NULL
    COMMENT 'OTP 발급 요청 IP. 동일 IP 의 단시간 다중 발급 차단 base. PII = 90일 hash/truncate'
    AFTER attempt_count,
  ADD KEY idx_email_verification_ip (requester_ip);

-- 한글 주석: 비번 재설정 token 발급 IP 추적
ALTER TABLE password_reset
  ADD COLUMN requester_ip VARCHAR(45) NULL DEFAULT NULL
    COMMENT '비번 재설정 token 발급 요청 IP. 의심 활동 감지 base. PII = 90일 hash/truncate'
    AFTER consumed_at,
  ADD KEY idx_password_reset_ip (requester_ip);
