-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0018 — 사용자 프로필 avatar 이미지 영속 (cycle 169.852 신설).
-- 사용자 directive 텔레그램 정합 아바타 이미지 picker — 그룹/채널 만들기 + 개인 프로필 3곳.
--   그룹/채널 avatar = rooms.avatar_ref(0017) 재사용. 개인 프로필 avatar = users 에 컬럼 부재 → 본 마이그레이션 신설.
-- 실 이미지 업로드 파이프라인(POST /api/avatars multipart → 디스크 저장 → avatar_ref 회신)은 본 directive 가 0017 주석의 "별도 directive" 를 채운다.

-- 한글 주석: users 에 avatar_ref 컬럼 추가 — 프로필 avatar 이미지 서버 영속.
--   기존 row = DEFAULT '' 채움 (NOT NULL 안전). 빈값 = 이니셜 fallback (회귀 0).
ALTER TABLE users
  ADD COLUMN avatar_ref VARCHAR(255) NOT NULL DEFAULT ''
    COMMENT '사용자 프로필 avatar 참조 키 (server volume relative path "avatars/<sha256>.<ext>"). 용도=프로필/친구/채팅 sender/drawer avatar 이미지 표시. 제약=0~255자, 빈값=이니셜 fallback(nickname/display_name/username 앞 2글자, _avatar_helper.make_avatar_pixmap), 실 byte 는 AVATAR_STORAGE_DIR 디스크 영속(DB 미보관). 출처=PATCH /api/me/avatar REST(POST /api/avatars 업로드 후 회신된 avatar_ref 로 갱신, 빈 문자열=avatar 제거). 참조=_avatar_helper.make_avatar_pixmap + my_profile_dialog avatar picker. 민감도=일반(프로필 공개 이미지)';
