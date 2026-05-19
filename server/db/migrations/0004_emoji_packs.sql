-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0004 — emoji pack share 공개 디렉토리.
-- 본 파일 = `server/db/migrations/0004_emoji_packs.sql`. Phase 5 Item 3 cycle 132 skeleton.
-- 정합 memory = [[project_emoji_pack_share]] + [[feedback-db-schema-field-comments]].
-- 모든 컬럼 = 5요소 comment 의무 (용도/제약/값 출처/참조 관계/민감도).
-- Phase 5 Item 3 emoji pack share — sticker + custom emoji pack 공개 디렉토리 base.

-- =============================================================================
-- 1) emoji_packs 신설 — 팩 메타 + 공개 여부 + moderation 상태
-- =============================================================================

-- 한글 주석: emoji 팩 메타 — owner + name + slug + 공개 여부 + moderation chain 상태
CREATE TABLE IF NOT EXISTS emoji_packs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
        COMMENT '팩 PK (AUTO_INCREMENT). 외부 노출 가능. 음수 부재 (UNSIGNED)',

    owner_user_id BIGINT UNSIGNED NOT NULL
        COMMENT '팩 소유 사용자 PK (users.id 외래키). CASCADE DELETE — 사용자 탈퇴 시 본 row 도 삭제. 비공개 팩 의 접근 권한 base',

    name VARCHAR(64) NOT NULL
        COMMENT '팩 이름 (사용자 표기, UTF-8 한글 포함 가능). 64자 cap. 검색 + 표시 base',

    slug VARCHAR(64) NOT NULL
        COMMENT 'URL slug (lowercase + hyphen, ASCII 만). UNIQUE 의무 — /api/emoji/packs/{slug} 의 라우팅 key. 사용자 영역 의 생성 + admin 영역 의 변경 가능',

    description VARCHAR(255) DEFAULT NULL
        COMMENT '팩 설명 텍스트. 255자 cap. 공개 디렉토리 의 카드 표시 base. NULL = 설명 부재',

    is_public TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '공개 여부 (0=비공개 owner only, 1=공개 디렉토리 노출). 기본 0 — owner 의 명시 publish 의무. moderation_status=approved 만 의 실 노출',

    moderation_status ENUM('pending', 'approved', 'rejected', 'dmca_takedown') NOT NULL DEFAULT 'pending'
        COMMENT 'moderation 상태 4 ENUM. pending=대기 (신규 default), approved=공개 가능, rejected=거부 (jailbreak OCR 또는 admin), dmca_takedown=DMCA 신고 의 takedown. Phase 5 Item 3 본격 cycle 의 OCR + DMCA chain 의 연결',

    download_count BIGINT UNSIGNED NOT NULL DEFAULT 0
        COMMENT '다운로드 누계 (마케팅 통계 + 인기 팩 sort base). atomic INCREMENT 의무 (race 차단). 음수 부재',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT '팩 생성 시각 (UTC, KST +09:00 변환 = caller 영역). 마케팅 시계열 분석 base',

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        COMMENT '팩 갱신 시각 (UTC). moderation_status 변경 또는 description 갱신 시 자동 갱신. 최근 갱신 sort base',

    PRIMARY KEY (id),
    UNIQUE KEY uq_emoji_packs_slug (slug),
    KEY idx_emoji_packs_owner (owner_user_id),
    KEY idx_emoji_packs_public_moderation (is_public, moderation_status),
    CONSTRAINT fk_emoji_packs_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Phase 5 Item 3 emoji 팩 메타 — 공개 디렉토리 base (cycle 132 skeleton)';


-- =============================================================================
-- 2) emoji_pack_items 신설 — 팩 안 의 개별 emoji 아이템
-- =============================================================================

-- 한글 주석: emoji 팩 의 개별 아이템 — shortcode + 파일 + moderation
CREATE TABLE IF NOT EXISTS emoji_pack_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
        COMMENT '아이템 PK (AUTO_INCREMENT). 음수 부재 (UNSIGNED)',

    pack_id BIGINT UNSIGNED NOT NULL
        COMMENT '소속 팩 PK (emoji_packs.id 외래키). CASCADE DELETE — 팩 삭제 시 본 row 도 삭제',

    shortcode VARCHAR(32) NOT NULL
        COMMENT 'emoji shortcode (예: tootalk_wow). 32자 cap. ASCII + underscore + digit 만 의무. (pack_id, shortcode) UNIQUE — 팩 안 중복 차단',

    file_path VARCHAR(255) NOT NULL
        COMMENT '저장 경로 (S3 key 또는 server volume relative path). 255자 cap. Phase 5 본격 cycle 진입 시 S3 binding production 활성',

    mime_type VARCHAR(64) NOT NULL DEFAULT 'image/png'
        COMMENT 'MIME 타입. image/png 또는 image/webp 또는 image/gif 만 허용 (server-side validation). 그 외 거부',

    file_size BIGINT UNSIGNED NOT NULL DEFAULT 0
        COMMENT '파일 크기 byte. 업로드 cap = 1 MB (Phase 5 본격 cycle 의 server-side validation). 음수 부재',

    width INT UNSIGNED NOT NULL DEFAULT 0
        COMMENT '가로 픽셀. 권장 128~512 px (sticker) 또는 100 px (custom emoji). 업로드 시 server-side detect',

    height INT UNSIGNED NOT NULL DEFAULT 0
        COMMENT '세로 픽셀. 권장 128~512 px (sticker) 또는 100 px (custom emoji). 업로드 시 server-side detect',

    moderation_status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending'
        COMMENT '개별 아이템 moderation 3 ENUM. pending=대기 (신규 default), approved=공개 가능, rejected=거부 (OCR 또는 admin). 팩 단위 moderation 의 더 세밀한 layer',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT '아이템 생성 시각 (UTC, KST +09:00 변환 = caller 영역). 업로드 시계열 분석 base',

    PRIMARY KEY (id),
    UNIQUE KEY uq_emoji_pack_items_pack_shortcode (pack_id, shortcode),
    KEY idx_emoji_pack_items_pack (pack_id),
    CONSTRAINT fk_emoji_pack_items_pack FOREIGN KEY (pack_id) REFERENCES emoji_packs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Phase 5 Item 3 emoji 팩 아이템 — shortcode + 파일 + moderation (cycle 132 skeleton)';
