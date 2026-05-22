-- 한글 주석: cycle 169.399 — user nickname field 추가 (사용자 directive image #163/164).
-- 사용자명 (username) = 변경 불가 retain. display_name (이름) = readonly (server-side write 차단).
-- nickname = 신규 (avatar text + 친구 list 표시 source). MyAccountDialog 안 "닉네임" row 의 persist column.
-- 0010 user profile fields 정합 — 4 column (display_name + phone + birthdate + bio) retain.
-- 본 cycle 안 nickname column 만 추가 (5th field).

ALTER TABLE users
  ADD COLUMN nickname VARCHAR(64) NOT NULL DEFAULT ''
    COMMENT '사용자 닉네임 — 친구 표시 + avatar text source. MyAccountDialog 안 "닉네임" row 의 persist column. username = 로그인 식별자 (불변) / display_name = 이름 (불변) / nickname = 닉네임 (자유 변경). 0~64자. 빈 문자열 시점 username fallback. 채팅 sender + drawer header + my_profile_dialog avatar 의 display source.';
