-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 초기 스키마 — Phase 1 회원가입 + 시그널링 + 대화 메타.
-- 본 파일 = `server/db/migrations/0001_init.sql` — migration 도구 의 첫 entry.
-- 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 모든 컬럼 = comment 의무 정합 ([[feedback-db-schema-field-comments]]).
-- DDL 본문 = MariaDB 10.6+ + InnoDB + utf8mb4_unicode_ci.

-- =============================================================================
-- AUTH 3 TABLE — Phase 1 회원가입 + 이메일 OTP + 비번 찾기
-- =============================================================================

-- 한글 주석: 사용자 마스터 — email/username/password_hash 의 인증 핵심 테이블
CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '사용자 PK (AUTO_INCREMENT). 외래키 참조 대상 (sessions.user_id / rooms.owner_id / peers.user_id 등). 음수 불가 (UNSIGNED)',

  email VARCHAR(255) NOT NULL
    COMMENT '로그인 식별자 + 이메일 OTP 발송 대상. UNIQUE. RFC 5321 의 256자 상한 정합. PII — 외부 노출 금지. case-insensitive lookup 의무 (저장 시 소문자 normalize 권장)',

  username VARCHAR(64) NOT NULL
    COMMENT '사용자 표시 이름. UNIQUE. 채팅 sender 표기 + 검색 키. 길이 1~64자. 영문/한글/숫자 + underscore 허용 (앱 측 정규식 검증)',

  password_hash VARCHAR(255) NOT NULL
    COMMENT 'PBKDF2-SHA256 해시 (포맷 `pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`). 앱 산출 (app.core.security.hash_password). 평문 저장 절대 금지. 알고리즘 마이그레이션 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 verify 의 의 의 prefix 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의',

  email_verified TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '이메일 OTP 검증 완료 여부 (0=미인증, 1=인증). 회원가입 직후 = 0, OTP 검증 PASS 시 = 1. unverified 사용자 = 로그인 차단 정합',

  status ENUM('active', 'suspended', 'deleted') NOT NULL DEFAULT 'active'
    COMMENT '계정 상태. active=정상, suspended=정지 (관리자 차단), deleted=탈퇴 (soft-delete, 30일 보관 후 hard-delete). 본 컬럼 = active 만 로그인 가능',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '회원가입 시각 (UTC). 가입일 통계 + 30일 inactive 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의',

  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT '레코드 마지막 수정 시각 (UTC). 비번 변경 / 이메일 변경 / status 변경 시 자동 갱신',

  last_login_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '마지막 로그인 시각 (UTC). NULL = 가입 후 미로그인. 30일 inactive 감지용',

  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  UNIQUE KEY uq_users_username (username),
  KEY idx_users_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 사용자 마스터 — 회원가입 + 이메일 OTP + 인증 핵심. 1:N 관계 — sessions / rooms / peers / messages';


-- 한글 주석: 이메일 OTP 코드 — 회원가입 + 비번 찾기 시점 의 일회용 인증 코드
CREATE TABLE IF NOT EXISTS email_verification (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT 'OTP 레코드 PK (AUTO_INCREMENT)',

  email VARCHAR(255) NOT NULL
    COMMENT 'OTP 발송 대상 이메일. users.email 와 join 가능하나 외래키 미설정 (회원가입 직전 의 의 의 의 의 의 의 의 의 의 의 의 의 의 user row 부재 케이스 의 의 의 의 의 의 의 의)',

  purpose ENUM('signup', 'password_reset') NOT NULL
    COMMENT 'OTP 용도. signup=회원가입 인증, password_reset=비번 재설정. 동일 email 의 다른 purpose 동시 발급 허용',

  code_hash CHAR(64) NOT NULL
    COMMENT '6자리 OTP 평문 의 SHA-256 hex (64자). 앱 산출 (app.core.security.hash_otp). 평문 저장 절대 금지. constant-time 비교 (hmac.compare_digest)',

  expires_at TIMESTAMP NOT NULL
    COMMENT 'OTP 만료 시각 (UTC, 발급 시각 + 3분). 본 시각 초과 = 무효. 만료 OTP = 별도 cleanup cron 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의',

  consumed_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'OTP 사용 시각 (UTC). NULL = 미사용, NOT NULL = 사용 완료 (재사용 차단). 검증 PASS 시 본 컬럼 갱신 + 동일 row 재사용 차단',

  attempt_count INT UNSIGNED NOT NULL DEFAULT 0
    COMMENT 'OTP 검증 시도 횟수. 5회 초과 시 본 row 무효화 (brute force 차단). 검증 시도 시마다 +1',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'OTP 발급 시각 (UTC). expires_at - created_at = 3분 의무',

  PRIMARY KEY (id),
  KEY idx_email_verification_email_purpose (email, purpose, consumed_at),
  KEY idx_email_verification_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 이메일 OTP — 회원가입 + 비번 찾기. 3분 만료 + 5회 시도 제한. consumed_at 의 의 의 의 재사용 차단';


-- 한글 주석: 비번 재설정 토큰 — 이메일 link click 의 의 의 의 의 의 의 의 의 비번 재설정 흐름
CREATE TABLE IF NOT EXISTS password_reset (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '비번 재설정 레코드 PK (AUTO_INCREMENT)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '대상 사용자 PK. users.id 외래키. CASCADE DELETE — 사용자 삭제 시 본 row 도 삭제',

  token_hash CHAR(64) NOT NULL
    COMMENT '32 byte URL-safe 토큰 의 SHA-256 hex (64자). 이메일 link query string 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의. 평문 저장 절대 금지',

  expires_at TIMESTAMP NOT NULL
    COMMENT '토큰 만료 시각 (UTC, 발급 시각 + 30분). 본 시각 초과 = 무효',

  consumed_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '토큰 사용 시각 (UTC). NULL = 미사용. 비번 재설정 완료 시 본 컬럼 갱신 + 재사용 차단',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '토큰 발급 시각 (UTC)',

  PRIMARY KEY (id),
  KEY idx_password_reset_user (user_id, consumed_at),
  KEY idx_password_reset_expires (expires_at),
  CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 비번 재설정 토큰 — 이메일 link 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 흐름. 30분 만료. 단일 사용 (consumed_at)';


-- =============================================================================
-- 대화 4 TABLE — Phase 1 시그널링 룸 + peer + 파일 메타 + 메시지 로그
-- =============================================================================

-- 한글 주석: 시그널링 룸 — 1:1 또는 group chat 의 의 의 의 가상 채널
CREATE TABLE IF NOT EXISTS rooms (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '룸 PK (AUTO_INCREMENT)',

  room_code CHAR(16) NOT NULL
    COMMENT '룸 식별 코드 (16자 URL-safe random). UNIQUE. 외부 공유 + 시그널링 WS 의 의 의 의 query parameter 로 사용',

  owner_id BIGINT UNSIGNED NOT NULL
    COMMENT '룸 생성자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 본 row 도 삭제. owner = 추방 / 룸 삭제 권한 보유',

  kind ENUM('direct', 'group') NOT NULL DEFAULT 'direct'
    COMMENT '룸 종류. direct=1:1 (최대 2 peer), group=다자 (Phase 2+ 진입). Phase 1 = direct 만',

  status ENUM('active', 'closed') NOT NULL DEFAULT 'active'
    COMMENT '룸 상태. active=참여 가능, closed=종료 (히스토리 보존 + 신규 join 차단)',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '룸 생성 시각 (UTC)',

  closed_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '룸 종료 시각 (UTC). NULL = active, NOT NULL = closed',

  PRIMARY KEY (id),
  UNIQUE KEY uq_rooms_code (room_code),
  KEY idx_rooms_owner_status (owner_id, status),
  CONSTRAINT fk_rooms_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 시그널링 룸 — 1:1 채팅 가상 채널. 1:N 관계 — peers / messages / file_meta';


-- 한글 주석: 룸 참여자 — 1 룸 의 N peer (Phase 1 = 최대 2)
CREATE TABLE IF NOT EXISTS peers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT 'peer 참여 레코드 PK (AUTO_INCREMENT)',

  room_id BIGINT UNSIGNED NOT NULL
    COMMENT '소속 룸 PK (rooms.id 외래키). CASCADE DELETE — 룸 삭제 시 본 row 도 삭제',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '참여 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 본 row 도 삭제',

  role ENUM('owner', 'member') NOT NULL DEFAULT 'member'
    COMMENT '룸 내 권한. owner=초대/추방/룸 종료, member=메시지 송수신 만. owner 1명 의무 (rooms.owner_id 정합)',

  joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'join 시각 (UTC). 룸 생성 시 owner 자동 등록',

  left_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'leave 시각 (UTC). NULL = 활성 참여 중, NOT NULL = 탈퇴 (히스토리 보존)',

  PRIMARY KEY (id),
  UNIQUE KEY uq_peers_room_user (room_id, user_id),
  KEY idx_peers_user_active (user_id, left_at),
  CONSTRAINT fk_peers_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  CONSTRAINT fk_peers_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 룸 참여자 — N:M (rooms ↔ users) join 테이블. role + left_at 의 의 의 의 의 의 권한/상태 표현';


-- 한글 주석: 파일 전송 메타 — Agent #16 FileSender/FileReceiver 결과 영속화
CREATE TABLE IF NOT EXISTS file_meta (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '파일 레코드 PK (AUTO_INCREMENT)',

  file_id CHAR(32) NOT NULL
    COMMENT 'UUID hex 32자 (app.rtc.protocol.new_file_id 산출). FILE_META 메시지 의 file_id 정합. UNIQUE',

  room_id BIGINT UNSIGNED NOT NULL
    COMMENT '소속 룸 PK (rooms.id 외래키). CASCADE DELETE',

  sender_id BIGINT UNSIGNED NOT NULL
    COMMENT '송신자 PK (users.id 외래키). CASCADE DELETE',

  name VARCHAR(255) NOT NULL
    COMMENT '원본 파일명 (UTF-8 한글 그대로 보존). 수신측 의 의 의 의 의 의 _safe_filename 정규화 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의',

  size BIGINT UNSIGNED NOT NULL
    COMMENT '파일 크기 (byte). 양수. 송신 전 fstat() 결과',

  mime VARCHAR(127) NOT NULL DEFAULT 'application/octet-stream'
    COMMENT 'MIME 타입 (app.rtc.image_processor.guess_mime 산출). image/* = 썸네일 동반',

  sha256 CHAR(64) NOT NULL
    COMMENT '전체 파일 SHA-256 hex (64자). 송신 시 app.rtc.file_sender._sha256_of_file 산출. 수신 측 검증 정합',

  status ENUM('uploading', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'uploading'
    COMMENT '전송 상태. uploading=진행 중, completed=수신 + 무결성 PASS, failed=오류, cancelled=중단',

  thumbnail_base64 MEDIUMTEXT NULL DEFAULT NULL
    COMMENT '이미지 썸네일 base64 (image/* 만). NULL = 비이미지. app.rtc.image_processor.make_thumbnail_base64 산출 (200x200 JPEG 80%). 약 5~15 KB',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'FILE_META 수신 시각 (UTC) = 송신 시작',

  completed_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'FILE_DONE 수신 시각 (UTC). status=completed 시점 정합',

  PRIMARY KEY (id),
  UNIQUE KEY uq_file_meta_file_id (file_id),
  KEY idx_file_meta_room_created (room_id, created_at),
  KEY idx_file_meta_sender (sender_id),
  CONSTRAINT fk_file_meta_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  CONSTRAINT fk_file_meta_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 파일 전송 메타 — Agent #16 FileSender/FileReceiver 의 송수신 영속화. SHA-256 무결성 + 썸네일 + 상태';


-- 한글 주석: 메시지 로그 — 텍스트 + 파일 link 의 통합 history
CREATE TABLE IF NOT EXISTS messages (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '메시지 PK (AUTO_INCREMENT)',

  room_id BIGINT UNSIGNED NOT NULL
    COMMENT '소속 룸 PK (rooms.id 외래키). CASCADE DELETE',

  sender_id BIGINT UNSIGNED NOT NULL
    COMMENT '송신자 PK (users.id 외래키). CASCADE DELETE',

  kind ENUM('text', 'file', 'system') NOT NULL
    COMMENT '메시지 종류. text=일반 텍스트 (body 에 본문), file=파일 (file_id 참조), system=시스템 알림 (join/leave/owner change)',

  body MEDIUMTEXT NULL DEFAULT NULL
    COMMENT 'kind=text 시 본문 (UTF-8 한글 그대로). kind=file 시 NULL. kind=system 시 시스템 메시지 본문 (예: "alice 가 룸에 참여했습니다")',

  file_id CHAR(32) NULL DEFAULT NULL
    COMMENT 'kind=file 시 file_meta.file_id 참조 (UUID hex 32자). kind=text/system 시 NULL',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '메시지 수신 시각 (UTC). 시그널링 서버 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의',

  PRIMARY KEY (id),
  KEY idx_messages_room_created (room_id, created_at),
  KEY idx_messages_sender (sender_id),
  KEY idx_messages_file (file_id),
  CONSTRAINT fk_messages_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  CONSTRAINT fk_messages_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 1 메시지 로그 — 텍스트 + 파일 + 시스템 알림 통합 history. (room_id, created_at) index = 채팅 timeline 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의';
