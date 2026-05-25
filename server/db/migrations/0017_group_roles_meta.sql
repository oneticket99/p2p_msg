-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0017 — 그룹 권한 admin role + 그룹 메타 영속 (cycle 169.820 신설).
-- 사용자 directive 텔레그램 그룹 멤버 관리 정합 — owner/member 2-tier → owner/admin/member 3-tier 확장.
-- 모델 단계 (model→REST→UI 순): write 경로(승격/강등 + 그룹 수정) foundation.
--   1) peers.role ENUM 에 admin 추가 — 텔레그램 "관리자" 권한. owner 가 승격/강등 (PATCH members REST, 후속 단계).
--   2) rooms 에 name/description/avatar_ref 컬럼 추가 — 그룹명/설명/avatar 서버 영속 (그룹 수정 dialog 저장, 후속 단계).
-- 표시(read) 경로는 본 마이그레이션 불요 (online/last-seen 은 users.last_activity_at[0003] 재사용).

-- 한글 주석: peers.role ENUM owner/member → owner/admin/member 3-tier 확장.
--   기존 row 무손상 — admin 은 신규 허용값 추가 만 (기존 owner/member 값 유지). DEFAULT 'member' 불변.
ALTER TABLE peers
  MODIFY COLUMN role ENUM('owner', 'admin', 'member') NOT NULL DEFAULT 'member'
    COMMENT '룸 내 권한 3-tier (cycle 169.820 admin 추가). 용도=초대/추방/관리 권한 gate. 값=owner(룸 소유자 1명, 생성자, 삭제/전권/양도) / admin(관리자, owner 가 승격, 초대·추방·멤버 관리, 다수 허용) / member(일반, 메시지 송수신). 제약=owner 1명 의무(rooms.owner_id 정합), DEFAULT member. 출처=owner 의 승격/강등 REST(PATCH /api/rooms/{id}/members/{uid}, 후속 단계). 참조=member_list _MemberRow badge 분기 + 관리자 목록 dialog. 민감도=중요(권한 = 추방/관리 gate)';

-- 한글 주석: rooms 에 그룹 메타 3 컬럼 추가 — 그룹명/설명/avatar 서버 영속.
--   기존 row = DEFAULT '' 채움 (NOT NULL 안전). direct(1:1) kind = 빈값 의미, group kind 만 활용.
ALTER TABLE rooms
  ADD COLUMN name VARCHAR(128) NOT NULL DEFAULT ''
    COMMENT '그룹명 (group chat 표시 이름). 용도=그룹 정보/수정 dialog title + chat_list entry source. 제약=0~128자, group kind 만 의미(direct=빈값). 출처=그룹 생성/수정 REST(PATCH /api/rooms/{id}, 후속 단계). 참조=group_info_dialog name_label. 민감도=일반(공개 표시명)',
  ADD COLUMN description VARCHAR(255) NOT NULL DEFAULT ''
    COMMENT '그룹 설명 (소개 문구). 용도=그룹 수정 dialog 설명 row. 제약=0~255자, group kind 만 의미. 출처=그룹 수정 REST(PATCH /api/rooms/{id}). 참조=group_edit_dialog 설명 입력. 민감도=일반',
  ADD COLUMN avatar_ref VARCHAR(255) NOT NULL DEFAULT ''
    COMMENT '그룹 avatar 참조 키 (object storage object key 또는 URL). 용도=그룹 avatar 표시. 제약=참조 키 만 보관(실 이미지 업로드 파이프라인 = 별도 directive), 빈값=기본 avatar(그룹명 이니셜). 출처=그룹 수정 REST. 참조=group_info_dialog _make_avatar. 민감도=일반';
