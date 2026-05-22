-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0015 — 사용자 연락처 + 양방향 매칭 (cycle 169.452 신설).
-- 사용자 directive telegram align — phone 기반 contact 등록 + reverse lookup 자동 friend 매칭.

CREATE TABLE IF NOT EXISTS user_contacts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '연락처 PK (AUTO_INCREMENT). 음수 부재',

  owner_user_id BIGINT UNSIGNED NOT NULL
    COMMENT '연락처 소유 사용자 PK (users.id FK). CASCADE DELETE — 사용자 탈퇴 시 contact row 삭제',

  phone VARCHAR(32) NOT NULL
    COMMENT '연락처 전화번호 (E.164 정규화 — 한국 = +82NNNNNNNNNN). UNIQUE(owner+phone) 정합',

  last_name VARCHAR(64) DEFAULT NULL
    COMMENT '성 (last name). 사용자 표기. NULL 허용',

  first_name VARCHAR(64) DEFAULT NULL
    COMMENT '이름 (first name). 사용자 표기. NULL 허용',

  matched_user_id BIGINT UNSIGNED DEFAULT NULL
    COMMENT '연락처 phone 일치 users.id (sign-up 시점 reverse lookup 갱신). NULL = 미가입 사용자. NOT NULL = TooTalk 가입자 + 자동 friend 매칭 trigger base',

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '연락처 등록 시각 (UTC)',

  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    COMMENT '갱신 시각 (UTC). 이름 변경 또는 matched_user_id 갱신 시점',

  PRIMARY KEY (id),
  UNIQUE KEY uq_user_contacts_owner_phone (owner_user_id, phone),
  KEY idx_user_contacts_phone (phone),
  KEY idx_user_contacts_matched_user (matched_user_id),
  CONSTRAINT fk_user_contacts_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='cycle 169.452 — telegram align 연락처 phone 기반 친구 추가 base';
