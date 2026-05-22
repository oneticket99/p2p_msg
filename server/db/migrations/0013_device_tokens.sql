-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0013 — FCM device tokens (cycle 169.446 신설).
-- 정합 사용자 directive — 메신저 기본 FCM 실시간 push notification chain base.
-- 모든 컬럼 = 5요소 comment 의무 (용도/제약/값 출처/참조 관계/민감도).

CREATE TABLE IF NOT EXISTS device_tokens (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '디바이스 토큰 PK (AUTO_INCREMENT). 음수 부재',

  user_id BIGINT UNSIGNED NOT NULL
    COMMENT '소유 사용자 PK (users.id FK). CASCADE DELETE — 사용자 탈퇴 시 token row 삭제. push notification 의 대상 식별 base',

  fcm_token VARCHAR(512) NOT NULL
    COMMENT 'Firebase Cloud Messaging registration token. 클라이언트 firebase-messaging SDK 의 의 발급값. plaintext 저장 (FCM API 직접 사용 의무 — 해시 부재). 사용자 별 다중 디바이스 retain (UNIQUE 부재)',

  platform ENUM('macos', 'windows', 'linux', 'ios', 'android', 'web') NOT NULL
    COMMENT '디바이스 platform. push payload 별 분기 base (APNs vs FCM Android vs Web Push)',

  device_label VARCHAR(64) DEFAULT NULL
    COMMENT '디바이스 식별 라벨 (사용자 표기 — "MacBook Pro 2024" 등). 64자 cap. NULL = 라벨 부재. 사용자 설정 panel 안 다중 device 식별 base',

  is_active TINYINT(1) NOT NULL DEFAULT 1
    COMMENT 'token 활성 여부 (0=비활성, 1=활성). FCM unregister 응답 시점 0 갱신. push send 시점 active 만 대상',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'token 등록 시각 (UTC). retention + token rotation 시계열 분석 base',

  last_used_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'token 마지막 push send 시각 (UTC). NULL = 미사용. idle revoke chain base (예: 90일 미사용 시 revoke)',

  PRIMARY KEY (id),
  UNIQUE KEY uq_device_tokens_user_token (user_id, fcm_token),
  KEY idx_device_tokens_user_active (user_id, is_active),
  CONSTRAINT fk_device_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='FCM push notification device tokens — cycle 169.446 base';
