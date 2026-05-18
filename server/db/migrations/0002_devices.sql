-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB devices table — Phase 2 사이클 43 multi-device sync.
-- 본 파일 = `server/db/migrations/0002_devices.sql` — 사이클 42 의 device_registry skeleton 의 server-side counterpart.
-- 사용자 directive [[feedback-db-schema-field-comments]] 정합 — 매 필드 5요소 comment 의무 (용도/제약/출처/참조/민감도).
-- DDL = MariaDB 10.6+ + InnoDB + utf8mb4_unicode_ci.

-- =============================================================================
-- devices — 1 user N device (Signal Protocol multi-device 모델)
-- =============================================================================

-- 한글 주석: 사용자 1명 의 N대 device — desktop / mobile / tablet 별 X3DH bundle 보유
CREATE TABLE IF NOT EXISTS devices (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '내부 PK (AUTO_INCREMENT). 외부 노출 금지 — 외부 식별자는 device_id (UUID) 사용. 음수 불가 (UNSIGNED)',

  device_id VARCHAR(64) NOT NULL
    COMMENT 'client-generated UUID4 device 식별자. UNIQUE. 외부 노출 + API 경로 식별자. 재설치 시 새 UUID 발급 (이전 device row = soft-delete 의무). 비밀 정보 아님 (서버 fingerprint 검증 후 등록)',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '소유자 user_id (users.id FK). 본 사용자 의 모든 device fetch 시 인덱스 키. ON DELETE CASCADE = 사용자 삭제 시 모든 device 자동 정리',

  label VARCHAR(128) NOT NULL DEFAULT ''
    COMMENT '사용자 친화 표시명 (예: "홍원표 의 MacBook"). 빈 문자열 허용. UI 의 device list 표기 + 사용자 직접 입력. PII 일부 (개인 식별 가능) — 외부 공개 시 마스킹 의무',

  identity_public BLOB NOT NULL
    COMMENT 'X25519 장기 identity 공개 키 (32 byte raw bytes). PreKeyBundle.identity_public 정합. 변경 = trust violation alert + re-verify 의무. 공개 키 (민감도 낮음) 단 무결성 의무',

  signed_prekey_public BLOB NOT NULL
    COMMENT 'X25519 중기 signed prekey 공개 키 (32 byte). 주기 rotation 의무 (권장 7일~30일). XEd25519 signature 별도 컬럼 = 추후 cycle. 공개 키 (민감도 낮음)',

  one_time_prekey_public BLOB NULL DEFAULT NULL
    COMMENT 'X25519 일회용 prekey 공개 키 (32 byte). NULL = OPK fallback (security 약화). 사용 후 폐기 의무 (forward secrecy 강화). 공개 키 (민감도 낮음) 단 단일 사용 정합',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'device 등록 시각 (UTC, application 의 KST 변환 의무 [[feedback-timezone-kst]]). 가입일 통계 + 30일 inactive 감지',

  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT 'prekey rotation / label 변경 시 자동 갱신. signed_prekey rotation 추적 의무',

  last_seen_at TIMESTAMP NULL DEFAULT NULL
    COMMENT '마지막 활동 시각 (메시지 송신 또는 연결 갱신). NULL = 등록 후 미사용. 30일 inactive device = 자동 soft-delete 후보',

  status ENUM('active', 'revoked') NOT NULL DEFAULT 'active'
    COMMENT 'device 상태. active = 정상 사용 가능, revoked = 사용자 직접 제거 또는 도난 신고 (key rotation trigger). revoked device 의 fan-out 송신 차단 의무',

  PRIMARY KEY (id),
  UNIQUE KEY uk_device_id (device_id),
  KEY idx_user_id (user_id),
  KEY idx_user_status (user_id, status),
  CONSTRAINT fk_devices_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 2 사이클 43 multi-device sync — 1 user N device X3DH bundle 영속화';
