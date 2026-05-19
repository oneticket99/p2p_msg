-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0006 — 자동 업데이트 app_versions 영속화.
-- 본 파일 = `server/db/migrations/0006_app_versions.sql`. Phase 5 cycle 132
-- 의 자동 업데이트 server endpoint prerequisite — 버전 메타 DB 영속화.
-- 정합 memory = [[feedback-db-schema-field-comments]] + [[project_build_policy]].
-- 모든 컬럼 = 5요소 comment 의무 (용도 + 제약 + 값 출처 + 참조 + 민감도).

-- 한글 주석: TooTalk 자동 업데이트 버전 메타 — 플랫폼 별 zip 산출물 + sha256 + release notes
CREATE TABLE IF NOT EXISTS app_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
    COMMENT '버전 PK (AUTO_INCREMENT). 외부 노출 부재 (관리자 console 의 내부 식별자). 음수 부재 (UNSIGNED)',

  version VARCHAR(32) NOT NULL
    COMMENT 'semver 형식 버전 문자열 (예: 0.5.0-phase5). 최대 32자. PEP 440 / semver.org 정합. 비교 = caller 영역 (semver 라이브러리). PII 부재',

  platform ENUM('macos-arm64','macos-x64','windows-x64','linux-x64') NOT NULL
    COMMENT '대상 플랫폼 4 ENUM. macos-arm64=Apple Silicon, macos-x64=Intel Mac, windows-x64=Windows 10/11 64bit, linux-x64=Ubuntu/Debian 64bit. PyInstaller --target-arch 의 정합',

  zip_url VARCHAR(512) NOT NULL
    COMMENT 'GitHub Release zip URL 의 절대 경로 (https://github.com/oneticket99/p2p_msg/releases/download/v...zip). 최대 512자. 외부 노출 의도 (client GET 의 base). HTTPS 의무',

  sha256 CHAR(64) NOT NULL
    COMMENT 'zip 산출물 의 SHA-256 hex 64자 (소문자). client 의 무결성 검증 base. 산출 = CI workflow sha256sum 명령. PII 부재',

  file_size BIGINT UNSIGNED NOT NULL DEFAULT 0
    COMMENT 'zip 산출물 의 바이트 크기. 0 = 미산정 fallback. client progress bar 표시 base. CI workflow stat 명령 의 산출. 음수 부재 (UNSIGNED)',

  min_compatible_version VARCHAR(32) DEFAULT NULL
    COMMENT '하위 호환 minimum 버전 문자열 (예: 0.4.0). NULL = 하위 호환 무제한. NOT NULL = 본 버전 미만 client 의 force upgrade 의무. semver 비교 정합',

  released_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT '출시 일시 (KST 기준 의도, MariaDB 의 server timezone 정합). DEFAULT CURRENT_TIMESTAMP. client 의 release notes 정렬 base',

  release_notes TEXT DEFAULT NULL
    COMMENT '한국어 변경 사항 본문 (markdown 의 허용). NULL = 변경 사항 비공개. UTF-8 한글 보존. PII 부재 (마케팅 본문 만)',

  is_latest TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '플랫폼 별 latest flag (0=아카이브, 1=현 최신). mark_latest 시 동일 platform 의 기존 row 의 0 reset 의무. GET /api/version/latest 의 base',

  PRIMARY KEY (id),
  UNIQUE KEY uq_version_platform (version, platform),
  KEY idx_platform_latest (platform, is_latest),
  KEY idx_released_at (released_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 5 자동 업데이트 버전 메타 — cycle 132 신설 (GitHub Release zip + sha256 + 플랫폼 별 latest)';
