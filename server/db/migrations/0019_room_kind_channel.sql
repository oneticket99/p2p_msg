-- SPDX-License-Identifier: GPL-3.0-or-later
-- TooTalk(p2p_msg) MariaDB 마이그레이션 0019 — rooms.kind 에 channel type 추가 (cycle 169.852 신설).
-- 사용자 directive 도메인 모델 — folder(최상위) ⊃ room(group/channel) ⊃ participants(users, peers n:n).
--   기존 rooms.kind = direct(1:1)/group(다자) → channel 추가로 채널(방송형 room) 을 독립 type 으로 승격.
--   channel = owner(채널주) + member(구독자) peers 구조 재사용. name/description/avatar_ref(0017)는 group 과 동일 활용.

-- 한글 주석: rooms.kind ENUM 에 'channel' 추가 — group/channel 서버 영속 type 분리.
--   기존 row 무손상 — channel 은 신규 허용값 추가 만(기존 direct/group 값 유지). DEFAULT 'direct' 불변.
ALTER TABLE rooms
  MODIFY COLUMN kind ENUM('direct', 'group', 'channel') NOT NULL DEFAULT 'direct'
    COMMENT 'room 종류 3-tier (cycle 169.852 channel 추가). 용도=room 유형 분기 + chat 표시/송신 경로. 값=direct(1:1 친구 대화, name/avatar 빈값) / group(다자 그룹 채팅, owner+member 양방 송신) / channel(방송형, owner=채널주 게시 + member=구독자). 제약=DEFAULT direct, group/channel 만 name/description/avatar_ref(0017) 활용. 출처=POST /api/rooms kind(그룹/채널 생성 dialog). 참조=rooms_handlers.handle_create_room kind 검증 + ChatListEntry(kind=room 통합 진입). 민감도=일반';
