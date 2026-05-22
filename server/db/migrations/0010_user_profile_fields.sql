-- 한글 주석: cycle 169.395 — user profile field 추가 — display_name + phone + birthdate + bio.
-- 사용자 critique image #160/161/162 회수 — MyAccountDialog 수정 後 visual reflect 부재 root cause.
-- 0001_init.sql users table 안 profile field 부재 → MyAccountDialog 4 field 의 persist chain 활성 의무.

ALTER TABLE users
  ADD COLUMN display_name VARCHAR(64) NOT NULL DEFAULT ''
    COMMENT '사용자 표시 이름 (닉네임). MyAccountDialog 안 "이름" row 의 persist column. username = 로그인 식별자 (불변) / display_name = 표시 이름 (가변). 채팅 sender 표기 + drawer header + my_profile_dialog 의 username field 의 source. 0~64자. 빈 문자열 시점 username fallback.',
  ADD COLUMN phone VARCHAR(32) NOT NULL DEFAULT ''
    COMMENT '사용자 전화번호 (국가코드 포함 E.164 권장, hyphen 자유). MyAccountDialog 안 "전화번호" row 의 persist column. 0~32자. 빈 문자열 = 미입력. SMS OTP 연동 시 의 source. PII 의 외부 노출 금지.',
  ADD COLUMN birthdate VARCHAR(10) NOT NULL DEFAULT ''
    COMMENT '사용자 생년월일 (YYYYMMDD 또는 YYYY-MM-DD). MyAccountDialog 안 "생년월일" row 의 persist column. 0~10자. 빈 문자열 = 미입력. PII 의 외부 노출 금지 (그룹/채널 안 표시 부재). 사용자 14세 미만 detect 회피 회수 chain entry.',
  ADD COLUMN bio VARCHAR(255) NOT NULL DEFAULT ''
    COMMENT '사용자 자기소개. MyAccountDialog 안 "자기소개" QTextEdit 의 persist column. 0~255자 (텔레그램 등가). 빈 문자열 = 미입력. MyProfileDialog 안 visible — 친구 + 그룹 멤버 외부 visible.';
