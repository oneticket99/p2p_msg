# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk i18n label catalog — cycle 169.354 sweep.

127 unique UI literal extract from app/ 안 setText/setPlaceholderText/QLabel/
QPushButton/QMessageBox/addAction call site. 추후 cycle 안 binding chain:
- 각 hardcoded literal → labels.LABEL_KEY reference 교체
- ko/en/zh-CN/zh-TW/ja 4 locale ts file entry 추가
- PyQt6 QTranslator + tr() chain 강화
"""

from __future__ import annotations


# 한글 주석 — 기본 ko 라벨 dict — key → ko text
LABELS_KO: dict[str, str] = {
    "새_폴더_만들기": "  + 새 폴더 만들기",  # app/ui/folder_manage_dialog.py:109
    "thumbnail_부재": "(thumbnail 부재)",  # app/ui/admin/emoji_moderation_dialog.py:415
    "미선택": "(미선택)",  # app/ui/admin/emoji_moderation_dialog.py:367, app/ui/admin/emoji_moderation_dialog.py:404, app/ui/admin/emoji_moderation_dialog.py:468
    "pack_등록": "+ pack 등록",  # app/ui/emoji_picker.py:162
    "6자리_otp_3분_유효": "6자리 OTP (3분 유효)",  # app/ui/password_reset_dialog.py:65
    "8_128자": "8~128자",  # app/ui/password_reset_dialog.py:70
    "dmca_신고_takedown": "DMCA 신고 (takedown)",  # app/ui/admin/emoji_moderation_dialog.py:381
    "otp_발송": "OTP 발송",  # app/ui/password_reset_dialog.py:54
    "tootalk_그룹_만들기": "TooTalk · 그룹 만들기",  # app/ui/new_group_dialog.py:41
    "tootalk_그룹_정보": "TooTalk · 그룹 정보",  # app/ui/group_info_dialog.py:51
    "tootalk_내_계정": "TooTalk · 내 계정",  # app/ui/my_account_dialog.py:39
    "tootalk_내_프로필": "TooTalk · 내 프로필",  # app/ui/my_profile_dialog.py:46
    "tootalk_새_폴더": "TooTalk · 새 폴더",  # app/ui/folder_edit_dialog.py:57
    "tootalk_연락처": "TooTalk · 연락처",  # app/ui/contacts_dialog.py:36
    "tootalk_원격_연결": "TooTalk · 원격 연결",  # app/ui/remote_control_dialog.py:186
    "tootalk_원격_요청": "TooTalk · 원격 요청",  # app/ui/remote_control_dialog.py:53
    "tootalk_전화": "TooTalk · 전화",  # app/ui/calls_dialog.py:35
    "tootalk_채널_만들기": "TooTalk · 채널 만들기",  # app/ui/new_channel_dialog.py:41
    "tootalk_친구_추가": "TooTalk · 친구 추가",  # app/ui/add_friend_dialog.py:112
    "tootalk_폴더": "TooTalk · 폴더",  # app/ui/folder_manage_dialog.py:43
    "tootalk_비밀번호_재설정": "TooTalk 비밀번호 재설정",  # app/ui/password_reset_dialog.py:36
    "tootalk_업데이트": "TooTalk 업데이트",  # app/ui/update_dialog.py:108
    "emoji_팩_moderation_관리자_cycle_144": "emoji 팩 moderation 관리자 (cycle 144)",  # app/ui/admin/emoji_moderation_dialog.py:348
    "pending_팩_queue": "pending 팩 queue",  # app/ui/admin/emoji_moderation_dialog.py:363
    "답장": "↳ 답장",  # app/ui/message_bubble.py:350
    "signal_protocol_활성": "✅ Signal Protocol 활성",  # app/ui/settings_dialog.py:539
    "전달_cycle_155": "➡ 전달 (cycle 155+)",  # app/ui/message_bubble.py:353
    "거부_reject": "거부 (reject)",  # app/ui/admin/emoji_moderation_dialog.py:380
    "거절": "거절",  # app/ui/friend_list.py:151, app/ui/remote_call_dialog.py:119, app/ui/remote_control_dialog.py:240
    "검색": "검색",  # app/ui/new_channel_dialog.py:167, app/ui/add_friend_dialog.py:133, app/ui/chat_list_panel.py:229
    "결정_사유_dmca_notice": "결정 사유 + DMCA notice",  # app/ui/admin/emoji_moderation_dialog.py:374
    "고정된_메시지": "고정된 메시지",  # app/ui/chat_header.py:139
    "구독자_추가": "구독자 추가",  # app/ui/new_channel_dialog.py:156, app/ui/new_channel_dialog.py:280
    "권한_mode": "권한 mode",  # app/ui/remote_control_dialog.py:101
    "그룹_관리": "그룹 관리",  # app/ui/main_window.py:2210
    "그룹_만들기": "그룹 만들기",  # app/ui/new_group_dialog.py:67
    "그룹_정보_보기": "그룹 정보 보기",  # app/ui/main_window.py:2209
    "그룹명": "그룹명",  # app/ui/new_group_dialog.py:103
    "나이와_직업_도시_따위를_자유롭게_소개하세요": "나이와 직업, 도시 따위를 자유롭게 소개하세요.",  # app/ui/my_account_dialog.py:108
    "나중에": "나중에",  # app/ui/update_dialog.py:123
    "내_폴더": "내 폴더",  # app/ui/folder_manage_dialog.py:100
    "다음": "다음",  # app/ui/new_channel_dialog.py:136, app/ui/new_group_dialog.py:125
    "닫기": "닫기",  # app/ui/add_friend_dialog.py:157
    "대기_중_원격_요청": "대기 중 원격 요청",  # app/ui/remote_control_dialog.py:217
    "대상_사용자": "대상 사용자",  # app/ui/remote_control_dialog.py:84
    "대화_내용_비우기": "대화 내용 비우기",  # app/ui/main_window.py:2212
    "대화_목록의_폴더_색상": "대화 목록의 폴더 색상",  # app/ui/folder_edit_dialog.py:126
    "대화방을_모은_폴더를_여럿_만들고_신속하게_대화를_전환하세요": "대화방을 모은 폴더를 여럿 만들고 신속하게 대화를 전환하세요.",  # app/ui/folder_manage_dialog.py:91
    "만들기": "만들기",  # app/ui/new_channel_dialog.py:212, app/ui/folder_edit_dialog.py:188, app/ui/new_group_dialog.py:204
    "메뉴": "메뉴",  # app/ui/sidebar_rail.py:61
    "메시지_작성_중": "메시지 작성 중",  # app/ui/typing_indicator.py:46
    "메시지_작성_중_2": "메시지 작성 중.",  # app/ui/typing_indicator.py:33
    "멤버_보기": "멤버 보기",  # app/ui/_chat_header_mixin.py:240
    "미입력_시_사용자명_사용": "미입력 시 사용자명 사용",  # app/ui/add_friend_dialog.py:150
    "별명_선택": "별명 (선택):",  # app/ui/add_friend_dialog.py:148
    "보내기": "보내기",  # app/ui/main_window.py:367
    "비밀번호_갱신": "비밀번호 갱신",  # app/ui/password_reset_dialog.py:76
    "사용자명_2자_이상": "사용자명 (2자 이상)",  # app/ui/add_friend_dialog.py:131
    "삭제": "삭제",  # app/ui/friend_list.py:165
    "삭제하고_나가기": "삭제하고 나가기",  # app/ui/main_window.py:2214
    "새_폴더": "새 폴더",  # app/ui/folder_edit_dialog.py:83
    "설문_만들기": "설문 만들기",  # app/ui/main_window.py:2211
    "수락": "수락",  # app/ui/call_dialog.py:139, app/ui/friend_list.py:146
    "수신_통화": "수신 통화…",  # app/ui/call_dialog.py:108
    "승인": "승인",  # app/ui/remote_call_dialog.py:109, app/ui/remote_control_dialog.py:231
    "승인_approve": "승인 (approve)",  # app/ui/admin/emoji_moderation_dialog.py:379
    "실패": "실패",  # app/ui/file_progress_widget.py:188
    "알림_끄기": "알림 끄기",  # app/ui/main_window.py:2207, app/ui/main_window.py:2222
    "야간_모드": "야간 모드",  # app/ui/hamburger_drawer.py:111
    "언어_선택_language": "언어 선택 / Language / 语言 / 言語",  # app/ui/settings_locale.py:96
    "언어_설정_language": "언어 설정 / Language / 语言 / 言語",  # app/ui/settings_locale.py:93
    "업데이트": "업데이트",  # app/ui/update_dialog.py:122
    "연결됨": "연결됨",  # app/ui/call_dialog.py:266
    "연락처": "연락처",  # app/ui/contacts_dialog.py:58
    "영상_부재": "영상 부재",  # app/ui/call_dialog.py:70
    "영상_수신_대기": "영상 수신 대기…",  # app/ui/call_dialog.py:295
    "예_obs_설정_도움_요청": "예: OBS 설정 도움 요청",  # app/ui/remote_control_dialog.py:131
    "온라인": "온라인",  # app/ui/my_account_dialog.py:95, app/ui/my_profile_dialog.py:116
    "완료": "완료",  # app/ui/file_progress_widget.py:181
    "요청_보내기": "요청 보내기",  # app/ui/remote_control_dialog.py:139
    "요청_사유": "요청 사유",  # app/ui/remote_control_dialog.py:127
    "원격_연결": "원격 연결",  # app/ui/main_window.py:2148, app/ui/remote_control_dialog.py:208
    "원격_요청": "원격 요청",  # app/ui/main_window.py:2147, app/ui/remote_control_dialog.py:75
    "유효_시간_초": "유효 시간 (초)",  # app/ui/remote_control_dialog.py:114
    "이_폴더의_일부_그룹_및_채널_접근을_다른_사용자와_공유합니다": "이 폴더의 일부 그룹 및 채널 접근을 다른 사용자와 공유합니다.",  # app/ui/folder_edit_dialog.py:171
    "이메일_또는_유저_id": "이메일 또는 유저 ID",  # app/ui/contacts_dialog.py:70
    "이전": "이전",  # app/ui/password_reset_dialog.py:74
    "자기소개": "자기소개",  # app/ui/my_account_dialog.py:104
    "저장": "저장",  # app/ui/my_account_dialog.py:129
    "전화": "전화",  # app/ui/calls_dialog.py:57
    "정보": "정보",  # app/ui/my_account_dialog.py:65
    "제외할_대화방": "제외할 대화방",  # app/ui/folder_edit_dialog.py:113
    "종료": "종료",  # app/ui/call_dialog.py:155
    "차단_해제": "차단 해제",  # app/ui/friend_list.py:174
    "참가자_추가": "참가자 추가",  # app/ui/new_group_dialog.py:146, app/ui/new_group_dialog.py:277
    "채널_만들기": "채널 만들기",  # app/ui/new_channel_dialog.py:67
    "채널_설명_선택": "채널 설명 (선택)",  # app/ui/new_channel_dialog.py:111
    "채널_소개": "채널 소개",  # app/ui/new_channel_dialog.py:115
    "채널명": "채널명",  # app/ui/new_channel_dialog.py:100
    "채팅": "채팅",  # app/ui/friend_list.py:160
    "채팅_나가기": "채팅 나가기",  # app/ui/main_window.py:2224
    "채팅_정보": "채팅 정보",  # app/ui/main_window.py:2221
    "초대": "초대",  # app/ui/invite_dialog.py:180
    "최근_통화": "최근 통화",  # app/ui/calls_dialog.py:67
    "추가": "추가",  # app/ui/contacts_dialog.py:76
    "추방": "추방",  # app/ui/member_list.py:120
    "취소": "취소",  # app/ui/new_channel_dialog.py:128, app/ui/new_channel_dialog.py:204, app/ui/chat_picker_dialog.py:72
    "친구_목록_client_미초기화_사전_주입_의무": "친구 목록 client 미초기화 — 사전 주입 의무",  # app/ui/invite_dialog.py:235
    "친구_추가": "친구 추가",  # app/ui/add_friend_dialog.py:160
    "탭_뷰": "탭 뷰",  # app/ui/folder_manage_dialog.py:125
    "투턱": "투턱",  # app/ui/welcome_dialog.py:114
    "포함할_대화방": "포함할 대화방",  # app/ui/folder_edit_dialog.py:100
    "폴더": "폴더",  # app/ui/folder_manage_dialog.py:66
    "폴더_공유": "폴더 공유",  # app/ui/folder_edit_dialog.py:157
    "폴더명": "폴더명",  # app/ui/folder_edit_dialog.py:88
    "폴더명_입력": "폴더명 입력…",  # app/ui/folder_edit_dialog.py:92
    "폴더에_표시하지_않을_대화방_혹은_유형을_정하세요": "폴더에 표시하지 않을 대화방 혹은 유형을 정하세요.",  # app/ui/folder_edit_dialog.py:118
    "폴더에_표시할_대화방_혹은_대화방_유형을_정하세요": "폴더에 표시할 대화방 혹은 대화방 유형을 정하세요.",  # app/ui/folder_edit_dialog.py:105
    "확인": "확인",  # app/ui/chat_picker_dialog.py:76, app/ui/settings_locale.py:108
    "회원님의_스토리가_여기에_표시됩니다": "회원님의 스토리가 여기에 표시됩니다.",  # app/ui/my_profile_dialog.py:147
    "복사": "📋 복사",  # app/ui/message_bubble.py:352
    "emoji_검색": "🔍 emoji 검색",  # app/ui/emoji_picker.py:134
    "검색_2": "🔍 검색",  # app/ui/chat_picker_dialog.py:54
    "초대_링크_생성": "🔗  초대 링크 생성",  # app/ui/folder_edit_dialog.py:160
    "삭제_2": "🗑 삭제",  # app/ui/message_bubble.py:355
    "반응_추가": "😀 반응 추가",  # app/ui/message_bubble.py:351
    # cycle 169.410 — 아이디 찾기 / 비밀번호 찾기 dialog 신규 entry
    "아이디_찾기": "아이디 찾기",
    "비밀번호_찾기": "비밀번호 찾기",
    "사용자명": "사용자명",
    "전화번호": "전화번호",
    "찾기": "찾기",
    "찾은_이메일": "찾은 이메일",
    "사용자명_전화번호_입력_안내": "회원가입 시점 등록한 사용자명 + 전화번호 입력 의무. 일치 시점 가입 이메일 일부 표시.",
    "사용자명_전화번호_입력_의무": "사용자명 + 전화번호 입력 의무",
    # cycle 169.411 — 야간 모드 state badge
    "켜짐": "켜짐",
    "꺼짐": "꺼짐",
    # cycle 169.454 — 신규 연락처 dialog (telegram align)
    "새로운_연락처": "새로운 연락처",
    "성": "성",
    "이름": "이름",
    "등록": "등록",
    # cycle 169.834 — user-facing 문구 친절화 binding (dev jargon 제거 + 정중체)
    # 한글 주석 — tray / auth / friend / invite / 폴더 / 로그인 / 비번재설정 / 연락처 / 검수 안내 문구
    "tray_minimized_hint": (
        "창을 닫아도 TooTalk는 트레이에서 계속 실행돼요. "
        "트레이 아이콘을 마우스 오른쪽 버튼으로 누르면 로그아웃하거나 종료할 수 있어요."
    ),
    "msg_auth_client_unavailable": "로그인 기능을 준비하지 못했어요. 앱을 다시 시작해 주세요.",
    "msg_not_logged_in": "현재 로그인되어 있지 않아요.",
    "msg_login_done": "로그인했어요. 환영해요!",
    "msg_login_required_add_friend": "친구를 추가하려면 먼저 로그인해 주세요.",
    "msg_login_required_pending": "받은 친구 요청을 보려면 먼저 로그인해 주세요.",
    "msg_friend_request_sent": "친구 요청을 보냈어요.",
    "msg_friend_request_sent_status": "친구 요청을 보냈어요. (대상 번호 {user_id})",
    "msg_friend_request_no_auth": "친구 요청을 보내지 못했어요. 다시 로그인해 주세요.",
    "msg_invite_client_unavailable": "친구 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
    "msg_invite_select_friend": "초대할 친구를 먼저 선택해 주세요.",
    "msg_invite_need_group_room": "그룹 채팅방에 들어간 뒤에 친구를 초대할 수 있어요.",
    "msg_folder_name_required": "폴더 이름을 입력해 주세요.",
    "msg_login_input_required": "이메일과 비밀번호를 입력해 주세요.",
    "msg_password_reset_otp_required": "6자리 숫자 인증코드를 입력해 주세요.",
    "msg_new_password_required": "새 비밀번호를 입력해 주세요.",
    "msg_username_min_3": "사용자명을 3자 이상 입력해 주세요.",
    "msg_contact_name_required": "이름이나 성 중 하나는 입력해 주세요.",
    "msg_contact_phone_required": "전화번호를 입력해 주세요. (+82 뒤 10자리)",
    "msg_moderation_queue_failed": "검수 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
    "ph_reset_email": "이메일을 입력해 주세요.",
    "btn_otp_send": "인증코드 받기",
    "ph_reset_otp": "6자리 인증코드 (3분 동안 유효)",
    "ph_new_password_len": "8~128자",
    "label_email": "이메일",
    "label_otp_code": "인증코드",
    "label_new_password": "새 비밀번호",
    "btn_prev": "이전",
    "btn_password_update": "비밀번호 바꾸기",
    "msg_reset_email_sent": "가입된 이메일이라면 인증코드를 보내 드렸어요. 메일함을 확인해 주세요.",
    "msg_password_update_done": "비밀번호를 바꿨어요. 새 비밀번호로 로그인해 주세요.",
    "title_password_reset_failed": "비밀번호 재설정 실패",
    # 한글 주석 — slug-key 기반 (signup/login/otp dialog 의 _tr() wrap entry) 친절화
    "비밀번호_8_32자_의무": "비밀번호는 8자에서 32자 사이로 입력해 주세요.",
    "사용자명_3_16자_의무": "사용자명은 3자에서 16자 사이로 입력해 주세요.",
    "만료_재_송신_의무": "인증 시간이 지났어요. 인증코드를 다시 받아 주세요.",
}


# 한글 주석 — cycle 169.355 — 4 locale lookup dict (placeholder — 추후 자동 번역 chain 의무)
LABELS_EN: dict[str, str] = {
    "친구와_직접_연결_p2p_메신저": "P2P Messenger — Direct Friend Connection",
    "원격_데스크탑_도움_gplv3_oss": "Remote Desktop Help + GPLv3 OSS",
    "시작하기": "Get Started",
    "투턱_로그인": "TooTalk Login",
    "email_password_입력": "Email + Password",
    "비밀번호": "Password",
    "로그인": "Login",
    "취소": "Cancel",
    "회원가입": "Sign Up",
    # cycle 169.410 — find id entry
    "아이디_찾기": "Find ID",
    "비밀번호_찾기": "Find Password",
    "사용자명": "Username",
    "전화번호": "Phone Number",
    "찾기": "Find",
    "찾은_이메일": "Email Found",
    "사용자명_전화번호_입력_안내": "Enter the username and phone number used at signup. Matching account email will be partially shown.",
    "사용자명_전화번호_입력_의무": "Username + phone number required",
    "켜짐": "ON",
    "꺼짐": "OFF",
    "새로운_연락처": "New Contact",
    "성": "Last Name",
    "이름": "First Name",
    "등록": "Add",
    "확인": "OK",
    "저장": "Save",
    "검색": "Search",
    "다음": "Next",
    "만들기": "Create",
    "그룹명": "Group Name",
    "채널명": "Channel Name",
    "참가자_추가": "Add Participants",
    "구독자_추가": "Add Subscribers",
    "메시지_작성": "Message...",
    "발신_통화": "Outgoing Call…",
    "수신_통화": "Incoming Call…",
    "종료": "End",
    "승인": "Accept",
    "거절": "Reject",
    "원격_요청_발신_중": "Sending Remote Request…",
    "원격_요청_수신": "Remote Request Incoming…",
    "최근에_접속함": "Last seen recently",
    "tootalk_그룹_만들기": "TooTalk · Create Group",
    "tootalk_채널_만들기": "TooTalk · Create Channel",
    "tootalk_연락처": "TooTalk · Contacts",
    "tootalk_전화": "TooTalk · Calls",
    "tootalk_원격_요청": "TooTalk · Remote Request",
    "tootalk_원격_수신": "TooTalk · Remote Incoming",
    "tootalk_내_프로필": "TooTalk · My Profile",
    "tootalk_그룹_정보": "TooTalk · Group Info",
    "tootalk_음성_통화": "TooTalk · Voice Call",
    "tootalk_영상_통화": "TooTalk · Video Call",
    "투네이션_고객센터": "Toonation Customer Service",
    "온라인": "Online",
    "투턱_회원가입": "TooTalk Sign Up",
    "email_username_password_의무": "Email + Username + Password required",
    "가입_otp_송신": "Sign Up + Send OTP",
    "otp_인증": "OTP Verification",
    "메일함_안_6_digit_otp_확인": "Check 6-digit OTP in inbox",
    "재_송신": "Resend",
    "검증": "Verify",
    "tootalk_비밀번호_재설정": "TooTalk Password Reset",
    "otp_발송": "Send OTP",
    "6자리_otp_3분_유효": "6-digit OTP (3 min valid)",
    "8_128자": "8~128 chars",
    "이전": "Back",
    "비밀번호_갱신": "Update Password",
    "내_프로필": "My Profile",
    "그룹_만들기": "Create Group",
    "채널_만들기": "Create Channel",
    "연락처": "Contacts",
    "전화": "Calls",
    "저장한_메시지": "Saved Messages",
    "설정": "Settings",
    "야간_모드": "Night Mode",
    "로그아웃": "Logout",
    "메시지_작성": "Type a message…",
    "고정된_메시지": "Pinned Message",
    "답장_중": "Replying…",
    "예": "Yes",
    "아니오": "No",
    "확인": "OK",
    "포함할_대화방": "Include Chats",
    "제외할_대화방": "Exclude Chats",
    "로그아웃_의무_어플_종료_다음_진입_시_재_로그인": "Logout will close the app. You must log in again on next launch.",
    "최근에_접속함": "Last seen recently",
    "나에게_메모_파일_보관": "Notes + files to self",
    "안녕하세요_무엇을_도와드릴까요_24시간_llm_상담_c": "Hello! How may I help? 24/7 LLM support.",
    # cycle 169.413 — Phase 1 잔존 i18n EN sweep (91 missing entry append)
    "dmca_신고_takedown": "DMCA Notice (takedown)",
    "emoji_검색": "Search Emoji",
    "emoji_팩_moderation_관리자_cycle_144": "Emoji Pack Moderation (Admin)",
    "pack_등록": "+ Register Pack",
    "pending_팩_queue": "Pending Pack Queue",
    "signal_protocol_활성": "Signal Protocol Active",
    "thumbnail_부재": "(no thumbnail)",
    "tootalk_내_계정": "TooTalk · My Account",
    "tootalk_새_폴더": "TooTalk · New Folder",
    "tootalk_업데이트": "TooTalk Update",
    "tootalk_원격_연결": "TooTalk · Remote Connect",
    "tootalk_친구_추가": "TooTalk · Add Friend",
    "tootalk_폴더": "TooTalk · Folders",
    "거부_reject": "Reject",
    "검색_2": "Search",
    "결정_사유_dmca_notice": "Reason + DMCA Notice",
    "권한_mode": "Permission Mode",
    "그룹_관리": "Manage Group",
    "그룹_정보_보기": "Group Info",
    "나이와_직업_도시_따위를_자유롭게_소개하세요": "Introduce yourself — age, job, city, etc.",
    "나중에": "Later",
    "내_폴더": "My Folders",
    "닫기": "Close",
    "답장": "Reply",
    "대기_중_원격_요청": "Pending Remote Requests",
    "대상_사용자": "Target User",
    "대화_내용_비우기": "Clear Chat",
    "대화_목록의_폴더_색상": "Folder Color in Chat List",
    "대화방을_모은_폴더를_여럿_만들고_신속하게_대화를_전환하세요": "Create folders to group chats and switch between them quickly.",
    "메뉴": "Menu",
    "메시지_작성_중": "Typing",
    "메시지_작성_중_2": "Typing.",
    "멤버_보기": "View Members",
    "미선택": "(none)",
    "미입력_시_사용자명_사용": "Falls back to username if empty",
    "반응_추가": "Add Reaction",
    "별명_선택": "Nickname (optional):",
    "보내기": "Send",
    "복사": "Copy",
    "사용자명_2자_이상": "Username (2+ chars)",
    "삭제": "Delete",
    "삭제_2": "Delete",
    "삭제하고_나가기": "Delete and Leave",
    "새_폴더": "New Folder",
    "새_폴더_만들기": "  + Create New Folder",
    "설문_만들기": "Create Poll",
    "수락": "Accept",
    "승인_approve": "Approve",
    "실패": "Failed",
    "알림_끄기": "Mute Notifications",
    "언어_선택_language": "Language / 언어 / 语言 / 言語",
    "언어_설정_language": "Language Settings",
    "업데이트": "Update",
    "연결됨": "Connected",
    "영상_부재": "No Video",
    "영상_수신_대기": "Waiting for Video…",
    "예_obs_설정_도움_요청": "e.g. OBS setup help request",
    "완료": "Done",
    "요청_보내기": "Send Request",
    "요청_사유": "Request Reason",
    "원격_연결": "Remote Connect",
    "원격_요청": "Remote Request",
    "유효_시간_초": "Valid Duration (sec)",
    "이_폴더의_일부_그룹_및_채널_접근을_다른_사용자와_공유합니다": "Share access to selected groups and channels in this folder.",
    "이메일_또는_유저_id": "Email or User ID",
    "자기소개": "Bio",
    "전달_cycle_155": "Forward",
    "정보": "Info",
    "차단_해제": "Unblock",
    "채널_설명_선택": "Channel Description (optional)",
    "채널_소개": "Channel Description",
    "채팅": "Chat",
    "채팅_나가기": "Leave Chat",
    "채팅_정보": "Chat Info",
    "초대": "Invite",
    "초대_링크_생성": "Create Invite Link",
    "최근_통화": "Recent Calls",
    "추가": "Add",
    "추방": "Kick",
    "친구_목록_client_미초기화_사전_주입_의무": "Friends list client not initialized — injection required",
    "친구_추가": "Add Friend",
    "탭_뷰": "Tab View",
    "투턱": "TooTalk",
    "폴더": "Folders",
    "폴더_공유": "Share Folder",
    "폴더명": "Folder Name",
    "폴더명_입력": "Enter folder name…",
    "폴더에_표시하지_않을_대화방_혹은_유형을_정하세요": "Choose chats or types to exclude from this folder.",
    "폴더에_표시할_대화방_혹은_대화방_유형을_정하세요": "Choose chats or types to include in this folder.",
    "회원님의_스토리가_여기에_표시됩니다": "Your story will appear here.",
    # cycle 169.834 — user-facing 문구 친절화 binding (EN)
    "tray_minimized_hint": (
        "TooTalk keeps running in the tray after you close the window. "
        "Right-click the tray icon to log out or quit."
    ),
    "msg_auth_client_unavailable": "We couldn't get login ready. Please restart the app.",
    "msg_not_logged_in": "You're not logged in yet.",
    "msg_login_done": "You're logged in. Welcome!",
    "msg_login_required_add_friend": "Please log in first to add friends.",
    "msg_login_required_pending": "Please log in first to see your friend requests.",
    "msg_friend_request_sent": "Friend request sent.",
    "msg_friend_request_sent_status": "Friend request sent. (to user {user_id})",
    "msg_friend_request_no_auth": "We couldn't send the friend request. Please log in again.",
    "msg_invite_client_unavailable": "We couldn't load your friend list. Please try again in a moment.",
    "msg_invite_select_friend": "Please pick a friend to invite first.",
    "msg_invite_need_group_room": "Open a group chat first to invite friends.",
    "msg_folder_name_required": "Please enter a folder name.",
    "msg_login_input_required": "Please enter your email and password.",
    "msg_password_reset_otp_required": "Please enter the 6-digit verification code.",
    "msg_new_password_required": "Please enter a new password.",
    "msg_username_min_3": "Please enter a username with at least 3 characters.",
    "msg_contact_name_required": "Please enter at least a first or last name.",
    "msg_contact_phone_required": "Please enter a phone number. (10 digits after +82)",
    "msg_moderation_queue_failed": "We couldn't load the review queue. Please try again in a moment.",
    "ph_reset_email": "Please enter your email.",
    "btn_otp_send": "Send code",
    "ph_reset_otp": "6-digit code (valid for 3 minutes)",
    "ph_new_password_len": "8–128 characters",
    "label_email": "Email",
    "label_otp_code": "Verification code",
    "label_new_password": "New password",
    "btn_prev": "Back",
    "btn_password_update": "Change password",
    "msg_reset_email_sent": "If this email is registered, we've sent a code. Please check your inbox.",
    "msg_password_update_done": "Your password has been changed. Please log in with the new one.",
    "title_password_reset_failed": "Password reset failed",
    "비밀번호_8_32자_의무": "Please enter a password between 8 and 32 characters.",
    "사용자명_3_16자_의무": "Please enter a username between 3 and 16 characters.",
    "만료_재_송신_의무": "The code has expired. Please request a new one.",
}
LABELS_ZH_CN: dict[str, str] = {
    "친구와_직접_연결_p2p_메신저": "P2P 即时通讯 — 朋友直接连接",
    "원격_데스크탑_도움_gplv3_oss": "远程桌面帮助 + GPLv3 OSS",
    "시작하기": "开始",
    "투턱_로그인": "TooTalk 登录",
    "email_password_입력": "邮箱 + 密码",
    "비밀번호": "密码",
    "로그인": "登录",
    "취소": "取消",
    "회원가입": "注册",
    "확인": "确定",
    "저장": "保存",
    "검색": "搜索",
    "다음": "下一步",
    "만들기": "创建",
    "그룹명": "群组名",
    "채널명": "频道名",
    "메시지_작성": "输入消息…",
    "종료": "结束",
    "승인": "接受",
    "거절": "拒绝",
    "tootalk_그룹_만들기": "TooTalk · 创建群组",
    "tootalk_채널_만들기": "TooTalk · 创建频道",
    "tootalk_연락처": "TooTalk · 联系人",
    "tootalk_전화": "TooTalk · 通话",
    "투네이션_고객센터": "Toonation 客服",
    "온라인": "在线",
    "투턱_회원가입": "TooTalk 注册",
    "email_username_password_의무": "邮箱 + 用户名 + 密码",
    "가입_otp_송신": "注册 + 发送验证码",
    "otp_인증": "验证码确认",
    "검증": "验证",
    "재_송신": "重新发送",
    "tootalk_비밀번호_재설정": "TooTalk 密码重置",
    "otp_발송": "发送验证码",
    "이전": "上一步",
    "비밀번호_갱신": "更新密码",
    "내_프로필": "我的资料",
    "그룹_만들기": "创建群组",
    "채널_만들기": "创建频道",
    "연락처": "联系人",
    "전화": "通话",
    "저장한_메시지": "已保存消息",
    "설정": "设置",
    "야간_모드": "夜间模式",
    "로그아웃": "退出登录",
    "메시지_작성": "输入消息…",
    "고정된_메시지": "置顶消息",
    "예": "是",
    "아니오": "否",
    "확인": "确认",
    "포함할_대화방": "包含的对话",
    "제외할_대화방": "排除的对话",
    "로그아웃_의무_어플_종료_다음_진입_시_재_로그인": "退出将关闭应用，下次启动需重新登录。",
    "최근에_접속함": "最近上线",
    "나에게_메모_파일_보관": "我的备忘 + 文件存储",
    # cycle 169.414 — Phase 5 Item 1 i18n ZH-CN sweep (KO 137 entry full coverage)
    "6자리_otp_3분_유효": "6 位验证码 (3 分钟有效)",
    "8_128자": "8~128 字符",
    "dmca_신고_takedown": "DMCA 投诉 (takedown)",
    "emoji_검색": "搜索表情",
    "emoji_팩_moderation_관리자_cycle_144": "表情包审核 (管理员)",
    "pack_등록": "+ 注册表情包",
    "pending_팩_queue": "待审核表情包队列",
    "signal_protocol_활성": "Signal Protocol 已启用",
    "thumbnail_부재": "(无缩略图)",
    "tootalk_그룹_정보": "TooTalk · 群组信息",
    "tootalk_내_계정": "TooTalk · 我的账号",
    "tootalk_내_프로필": "TooTalk · 我的资料",
    "tootalk_새_폴더": "TooTalk · 新文件夹",
    "tootalk_업데이트": "TooTalk 更新",
    "tootalk_원격_연결": "TooTalk · 远程连接",
    "tootalk_원격_요청": "TooTalk · 远程请求",
    "tootalk_친구_추가": "TooTalk · 添加好友",
    "tootalk_폴더": "TooTalk · 文件夹",
    "거부_reject": "拒绝",
    "검색_2": "搜索",
    "결정_사유_dmca_notice": "理由 + DMCA 通知",
    "구독자_추가": "添加订阅者",
    "권한_mode": "权限模式",
    "그룹_관리": "管理群组",
    "그룹_정보_보기": "查看群组信息",
    "꺼짐": "关闭",
    "나이와_직업_도시_따위를_자유롭게_소개하세요": "自由介绍 — 年龄、职业、城市等。",
    "나중에": "稍后",
    "내_폴더": "我的文件夹",
    "닫기": "关闭",
    "답장": "回复",
    "대기_중_원격_요청": "待处理远程请求",
    "대상_사용자": "目标用户",
    "대화_내용_비우기": "清空聊天",
    "대화_목록의_폴더_색상": "聊天列表文件夹颜色",
    "대화방을_모은_폴더를_여럿_만들고_신속하게_대화를_전환하세요": "创建多个文件夹分组聊天，快速切换会话。",
    "메뉴": "菜单",
    "메시지_작성_중": "正在输入",
    "메시지_작성_중_2": "正在输入。",
    "멤버_보기": "查看成员",
    "미선택": "(未选择)",
    "미입력_시_사용자명_사용": "留空时使用用户名",
    "반응_추가": "添加反应",
    "별명_선택": "昵称 (可选):",
    "보내기": "发送",
    "복사": "复制",
    "비밀번호_찾기": "找回密码",
    "사용자명": "用户名",
    "사용자명_2자_이상": "用户名 (2 字符以上)",
    "사용자명_전화번호_입력_안내": "请输入注册时的用户名 + 电话号码。匹配时显示账号邮箱的部分内容。",
    "사용자명_전화번호_입력_의무": "需输入用户名 + 电话号码",
    "새로운_연락처": "新建联系人",
    "성": "姓",
    "이름": "名",
    "등록": "添加",
    "삭제": "删除",
    "삭제_2": "删除",
    "삭제하고_나가기": "删除并退出",
    "새_폴더": "新文件夹",
    "새_폴더_만들기": "  + 创建新文件夹",
    "설문_만들기": "创建投票",
    "수락": "接受",
    "수신_통화": "来电…",
    "승인_approve": "批准",
    "실패": "失败",
    "아이디_찾기": "找回账号",
    "알림_끄기": "关闭通知",
    "언어_선택_language": "语言 / Language / 언어 / 言語",
    "언어_설정_language": "语言设置",
    "업데이트": "更新",
    "연결됨": "已连接",
    "영상_부재": "无视频",
    "영상_수신_대기": "等待接收视频…",
    "예_obs_설정_도움_요청": "例: OBS 设置协助请求",
    "완료": "完成",
    "요청_보내기": "发送请求",
    "요청_사유": "请求理由",
    "원격_연결": "远程连接",
    "원격_요청": "远程请求",
    "유효_시간_초": "有效时长 (秒)",
    "이_폴더의_일부_그룹_및_채널_접근을_다른_사용자와_공유합니다": "与其他用户共享此文件夹中部分群组与频道的访问权限。",
    "이메일_또는_유저_id": "邮箱或用户 ID",
    "자기소개": "个人简介",
    "전달_cycle_155": "转发",
    "전화번호": "电话号码",
    "정보": "信息",
    "차단_해제": "解除屏蔽",
    "참가자_추가": "添加参与者",
    "찾기": "查找",
    "찾은_이메일": "找到的邮箱",
    "채널_설명_선택": "频道描述 (可选)",
    "채널_소개": "频道介绍",
    "채팅": "聊天",
    "채팅_나가기": "退出聊天",
    "채팅_정보": "聊天信息",
    "초대": "邀请",
    "초대_링크_생성": "创建邀请链接",
    "최근_통화": "最近通话",
    "추가": "添加",
    "추방": "踢出",
    "친구_목록_client_미초기화_사전_주입_의무": "好友列表 client 未初始化 — 需要预先注入",
    "친구_추가": "添加好友",
    "켜짐": "开启",
    "탭_뷰": "选项卡视图",
    "투턱": "TooTalk",
    "폴더": "文件夹",
    "폴더_공유": "共享文件夹",
    "폴더명": "文件夹名",
    "폴더명_입력": "输入文件夹名…",
    "폴더에_표시하지_않을_대화방_혹은_유형을_정하세요": "选择不在此文件夹中显示的聊天或类型。",
    "폴더에_표시할_대화방_혹은_대화방_유형을_정하세요": "选择要在此文件夹中显示的聊天或类型。",
    "회원님의_스토리가_여기에_표시됩니다": "您的故事将显示在此处。",
    # cycle 169.834 — user-facing 문구 친절화 binding (ZH-CN)
    "tray_minimized_hint": "关闭窗口后 TooTalk 仍会在托盘中运行。右键点击托盘图标即可登出或退出。",
    "msg_auth_client_unavailable": "登录功能尚未就绪，请重新启动应用。",
    "msg_not_logged_in": "您还没有登录。",
    "msg_login_done": "登录成功，欢迎回来！",
    "msg_login_required_add_friend": "请先登录后再添加好友。",
    "msg_login_required_pending": "请先登录后再查看好友请求。",
    "msg_friend_request_sent": "已发送好友请求。",
    "msg_friend_request_sent_status": "已发送好友请求。（对方 ID {user_id}）",
    "msg_friend_request_no_auth": "无法发送好友请求，请重新登录。",
    "msg_invite_client_unavailable": "无法加载好友列表，请稍后再试。",
    "msg_invite_select_friend": "请先选择要邀请的好友。",
    "msg_invite_need_group_room": "请先进入群聊后再邀请好友。",
    "msg_folder_name_required": "请输入文件夹名称。",
    "msg_login_input_required": "请输入邮箱和密码。",
    "msg_password_reset_otp_required": "请输入 6 位验证码。",
    "msg_new_password_required": "请输入新密码。",
    "msg_username_min_3": "请输入至少 3 个字符的用户名。",
    "msg_contact_name_required": "请至少填写名字或姓氏。",
    "msg_contact_phone_required": "请输入电话号码。（+82 后 10 位）",
    "msg_moderation_queue_failed": "无法加载审核列表，请稍后再试。",
    "ph_reset_email": "请输入邮箱。",
    "btn_otp_send": "获取验证码",
    "ph_reset_otp": "6 位验证码（3 分钟内有效）",
    "ph_new_password_len": "8～128 个字符",
    "label_email": "邮箱",
    "label_otp_code": "验证码",
    "label_new_password": "新密码",
    "btn_prev": "上一步",
    "btn_password_update": "修改密码",
    "msg_reset_email_sent": "若该邮箱已注册，我们已发送验证码，请查收邮件。",
    "msg_password_update_done": "密码已修改，请使用新密码登录。",
    "title_password_reset_failed": "密码重置失败",
    "비밀번호_8_32자_의무": "请输入 8 到 32 个字符的密码。",
    "사용자명_3_16자_의무": "请输入 3 到 16 个字符的用户名。",
    "만료_재_송신_의무": "验证已过期，请重新获取验证码。",
}
LABELS_ZH_TW: dict[str, str] = {
    "친구와_직접_연결_p2p_메신저": "P2P 即時通訊 — 朋友直接連線",
    "원격_데스크탑_도움_gplv3_oss": "遠端桌面協助 + GPLv3 OSS",
    "시작하기": "開始",
    "tootalk_그룹_만들기": "TooTalk · 建立群組",
    "tootalk_채널_만들기": "TooTalk · 建立頻道",
    "투네이션_고객센터": "Toonation 客服",
    "온라인": "線上",
    # cycle 169.834 — user-facing 문구 친절화 binding (ZH-TW)
    "tray_minimized_hint": "關閉視窗後 TooTalk 仍會在系統匣中執行。在系統匣圖示按右鍵即可登出或結束。",
    "msg_auth_client_unavailable": "登入功能尚未就緒，請重新啟動應用程式。",
    "msg_not_logged_in": "您還沒有登入。",
    "msg_login_done": "登入成功，歡迎回來！",
    "msg_login_required_add_friend": "請先登入後再新增好友。",
    "msg_login_required_pending": "請先登入後再查看好友邀請。",
    "msg_friend_request_sent": "已送出好友邀請。",
    "msg_friend_request_sent_status": "已送出好友邀請。（對方 ID {user_id}）",
    "msg_friend_request_no_auth": "無法送出好友邀請，請重新登入。",
    "msg_invite_client_unavailable": "無法載入好友清單，請稍後再試。",
    "msg_invite_select_friend": "請先選擇要邀請的好友。",
    "msg_invite_need_group_room": "請先進入群組聊天後再邀請好友。",
    "msg_folder_name_required": "請輸入資料夾名稱。",
    "msg_login_input_required": "請輸入電子郵件和密碼。",
    "msg_password_reset_otp_required": "請輸入 6 位數驗證碼。",
    "msg_new_password_required": "請輸入新密碼。",
    "msg_username_min_3": "請輸入至少 3 個字元的使用者名稱。",
    "msg_contact_name_required": "請至少填寫名字或姓氏。",
    "msg_contact_phone_required": "請輸入電話號碼。（+82 後 10 碼）",
    "msg_moderation_queue_failed": "無法載入審核清單，請稍後再試。",
    "ph_reset_email": "請輸入電子郵件。",
    "btn_otp_send": "取得驗證碼",
    "ph_reset_otp": "6 位數驗證碼（3 分鐘內有效）",
    "ph_new_password_len": "8～128 個字元",
    "label_email": "電子郵件",
    "label_otp_code": "驗證碼",
    "label_new_password": "新密碼",
    "btn_prev": "上一步",
    "btn_password_update": "變更密碼",
    "msg_reset_email_sent": "若此電子郵件已註冊，我們已寄出驗證碼，請查收郵件。",
    "msg_password_update_done": "密碼已變更，請使用新密碼登入。",
    "title_password_reset_failed": "密碼重設失敗",
    "비밀번호_8_32자_의무": "請輸入 8 到 32 個字元的密碼。",
    "사용자명_3_16자_의무": "請輸入 3 到 16 個字元的使用者名稱。",
    "만료_재_송신_의무": "驗證已逾時，請重新取得驗證碼。",
}
LABELS_JA: dict[str, str] = {
    "친구와_직접_연결_p2p_메신저": "P2P メッセンジャー — 友達と直接接続",
    "원격_데스크탑_도움_gplv3_oss": "リモートデスクトップ支援 + GPLv3 OSS",
    "시작하기": "始める",
    "투턱_로그인": "TooTalk ログイン",
    "email_password_입력": "メール + パスワード",
    "비밀번호": "パスワード",
    "로그인": "ログイン",
    "취소": "キャンセル",
    "회원가입": "新規登録",
    "확인": "OK",
    "저장": "保存",
    "검색": "検索",
    "다음": "次へ",
    "만들기": "作成",
    "그룹명": "グループ名",
    "채널명": "チャンネル名",
    "메시지_작성": "メッセージを入力…",
    "종료": "終了",
    "승인": "承認",
    "거절": "拒否",
    "tootalk_그룹_만들기": "TooTalk · グループ作成",
    "tootalk_채널_만들기": "TooTalk · チャンネル作成",
    "tootalk_연락처": "TooTalk · 連絡先",
    "tootalk_전화": "TooTalk · 通話",
    "투네이션_고객센터": "Toonation カスタマーサポート",
    "온라인": "オンライン",
    "투턱_회원가입": "TooTalk 新規登録",
    "email_username_password_의무": "メール + ユーザー名 + パスワード",
    "가입_otp_송신": "登録 + OTP 送信",
    "otp_인증": "OTP 認証",
    "검증": "認証",
    "재_송신": "再送信",
    "tootalk_비밀번호_재설정": "TooTalk パスワード再設定",
    "otp_발송": "OTP 送信",
    "이전": "戻る",
    "비밀번호_갱신": "パスワード更新",
    "내_프로필": "マイプロフィール",
    "그룹_만들기": "グループ作成",
    "채널_만들기": "チャンネル作成",
    "연락처": "連絡先",
    "전화": "通話",
    "저장한_메시지": "保存済みメッセージ",
    "설정": "設定",
    "야간_모드": "ナイトモード",
    "로그아웃": "ログアウト",
    "메시지_작성": "メッセージを入力…",
    "고정된_메시지": "固定メッセージ",
    "예": "はい",
    "아니오": "いいえ",
    "확인": "確認",
    "포함할_대화방": "含めるチャット",
    "제외할_대화방": "除外するチャット",
    "로그아웃_의무_어플_종료_다음_진입_시_재_로그인": "ログアウトするとアプリが終了し、次回起動時に再ログインが必要です。",
    "최근에_접속함": "最近オンライン",
    "나에게_메모_파일_보관": "自分用メモ + ファイル保存",
    # cycle 169.414 — Phase 5 Item 1 i18n JA sweep (KO 137 entry full coverage)
    "6자리_otp_3분_유효": "6 桁 OTP (3 分間有効)",
    "8_128자": "8〜128 文字",
    "dmca_신고_takedown": "DMCA 申告 (takedown)",
    "emoji_검색": "絵文字検索",
    "emoji_팩_moderation_관리자_cycle_144": "絵文字パック審査 (管理者)",
    "pack_등록": "+ パック登録",
    "pending_팩_queue": "保留中パックキュー",
    "signal_protocol_활성": "Signal Protocol 有効",
    "thumbnail_부재": "(サムネイルなし)",
    "tootalk_그룹_정보": "TooTalk · グループ情報",
    "tootalk_내_계정": "TooTalk · マイアカウント",
    "tootalk_내_프로필": "TooTalk · マイプロフィール",
    "tootalk_새_폴더": "TooTalk · 新しいフォルダ",
    "tootalk_업데이트": "TooTalk アップデート",
    "tootalk_원격_연결": "TooTalk · リモート接続",
    "tootalk_원격_요청": "TooTalk · リモート要請",
    "tootalk_친구_추가": "TooTalk · 友達追加",
    "tootalk_폴더": "TooTalk · フォルダ",
    "거부_reject": "拒否",
    "검색_2": "検索",
    "결정_사유_dmca_notice": "理由 + DMCA 通知",
    "구독자_추가": "購読者を追加",
    "권한_mode": "権限モード",
    "그룹_관리": "グループ管理",
    "그룹_정보_보기": "グループ情報を見る",
    "꺼짐": "オフ",
    "나이와_직업_도시_따위를_자유롭게_소개하세요": "年齢、職業、都市など自由に紹介してください。",
    "나중에": "後で",
    "내_폴더": "マイフォルダ",
    "닫기": "閉じる",
    "답장": "返信",
    "대기_중_원격_요청": "保留中リモート要請",
    "대상_사용자": "対象ユーザー",
    "대화_내용_비우기": "チャット履歴を消去",
    "대화_목록의_폴더_색상": "チャットリスト内フォルダの色",
    "대화방을_모은_폴더를_여럿_만들고_신속하게_대화를_전환하세요": "フォルダを複数作成してチャットをグループ化し、素早く切り替えられます。",
    "메뉴": "メニュー",
    "메시지_작성_중": "入力中",
    "메시지_작성_중_2": "入力中。",
    "멤버_보기": "メンバー表示",
    "미선택": "(未選択)",
    "미입력_시_사용자명_사용": "空欄時はユーザー名を使用",
    "반응_추가": "リアクション追加",
    "별명_선택": "ニックネーム (任意):",
    "보내기": "送信",
    "복사": "コピー",
    "비밀번호_찾기": "パスワード再発行",
    "사용자명": "ユーザー名",
    "사용자명_2자_이상": "ユーザー名 (2 文字以上)",
    "사용자명_전화번호_입력_안내": "登録時のユーザー名 + 電話番号を入力してください。一致時はアカウントメールの一部が表示されます。",
    "사용자명_전화번호_입력_의무": "ユーザー名 + 電話番号が必要",
    "새로운_연락처": "新規連絡先",
    "성": "姓",
    "이름": "名",
    "등록": "追加",
    "삭제": "削除",
    "삭제_2": "削除",
    "삭제하고_나가기": "削除して退出",
    "새_폴더": "新しいフォルダ",
    "새_폴더_만들기": "  + 新しいフォルダ作成",
    "설문_만들기": "投票作成",
    "수락": "承認",
    "수신_통화": "着信…",
    "승인_approve": "承認",
    "실패": "失敗",
    "아이디_찾기": "ID 検索",
    "알림_끄기": "通知オフ",
    "언어_선택_language": "言語 / Language / 언어 / 语言",
    "언어_설정_language": "言語設定",
    "업데이트": "アップデート",
    "연결됨": "接続済み",
    "영상_부재": "映像なし",
    "영상_수신_대기": "映像受信待機…",
    "예_obs_설정_도움_요청": "例: OBS 設定支援要請",
    "완료": "完了",
    "요청_보내기": "要請送信",
    "요청_사유": "要請理由",
    "원격_연결": "リモート接続",
    "원격_요청": "リモート要請",
    "유효_시간_초": "有効時間 (秒)",
    "이_폴더의_일부_그룹_및_채널_접근을_다른_사용자와_공유합니다": "このフォルダ内の一部グループとチャンネルへのアクセスを他ユーザーと共有します。",
    "이메일_또는_유저_id": "メールまたはユーザー ID",
    "자기소개": "自己紹介",
    "전달_cycle_155": "転送",
    "전화번호": "電話番号",
    "정보": "情報",
    "차단_해제": "ブロック解除",
    "참가자_추가": "参加者を追加",
    "찾기": "検索",
    "찾은_이메일": "見つかったメール",
    "채널_설명_선택": "チャンネル説明 (任意)",
    "채널_소개": "チャンネル紹介",
    "채팅": "チャット",
    "채팅_나가기": "チャットを退出",
    "채팅_정보": "チャット情報",
    "초대": "招待",
    "초대_링크_생성": "招待リンク生成",
    "최근_통화": "最近の通話",
    "추가": "追加",
    "추방": "強制退出",
    "친구_목록_client_미초기화_사전_주입_의무": "友達リスト client 未初期化 — 事前注入が必要",
    "친구_추가": "友達追加",
    "켜짐": "オン",
    "탭_뷰": "タブビュー",
    "투턱": "TooTalk",
    "폴더": "フォルダ",
    "폴더_공유": "フォルダ共有",
    "폴더명": "フォルダ名",
    "폴더명_입력": "フォルダ名を入力…",
    "폴더에_표시하지_않을_대화방_혹은_유형을_정하세요": "このフォルダで表示しないチャットや種類を選択してください。",
    "폴더에_표시할_대화방_혹은_대화방_유형을_정하세요": "このフォルダに表示するチャットや種類を選択してください。",
    "회원님의_스토리가_여기에_표시됩니다": "あなたのストーリーがここに表示されます。",
    # cycle 169.834 — user-facing 문구 친절화 binding (JA)
    "tray_minimized_hint": "ウィンドウを閉じても TooTalk はトレイで動き続けます。トレイアイコンを右クリックするとログアウトや終了ができます。",
    "msg_auth_client_unavailable": "ログイン機能を準備できませんでした。アプリを再起動してください。",
    "msg_not_logged_in": "まだログインしていません。",
    "msg_login_done": "ログインしました。ようこそ！",
    "msg_login_required_add_friend": "友達を追加するには、先にログインしてください。",
    "msg_login_required_pending": "友達リクエストを見るには、先にログインしてください。",
    "msg_friend_request_sent": "友達リクエストを送りました。",
    "msg_friend_request_sent_status": "友達リクエストを送りました。（相手 ID {user_id}）",
    "msg_friend_request_no_auth": "友達リクエストを送れませんでした。もう一度ログインしてください。",
    "msg_invite_client_unavailable": "友達リストを読み込めませんでした。しばらくしてからもう一度お試しください。",
    "msg_invite_select_friend": "招待する友達を先に選んでください。",
    "msg_invite_need_group_room": "グループチャットに入ってから友達を招待できます。",
    "msg_folder_name_required": "フォルダ名を入力してください。",
    "msg_login_input_required": "メールアドレスとパスワードを入力してください。",
    "msg_password_reset_otp_required": "6 桁の認証コードを入力してください。",
    "msg_new_password_required": "新しいパスワードを入力してください。",
    "msg_username_min_3": "ユーザー名は 3 文字以上で入力してください。",
    "msg_contact_name_required": "名前または姓のどちらかを入力してください。",
    "msg_contact_phone_required": "電話番号を入力してください。（+82 のあと 10 桁）",
    "msg_moderation_queue_failed": "審査リストを読み込めませんでした。しばらくしてからもう一度お試しください。",
    "ph_reset_email": "メールアドレスを入力してください。",
    "btn_otp_send": "コードを受け取る",
    "ph_reset_otp": "6 桁の認証コード（3 分間有効）",
    "ph_new_password_len": "8〜128 文字",
    "label_email": "メールアドレス",
    "label_otp_code": "認証コード",
    "label_new_password": "新しいパスワード",
    "btn_prev": "戻る",
    "btn_password_update": "パスワードを変更",
    "msg_reset_email_sent": "登録済みのメールアドレスであれば、認証コードを送りました。メールをご確認ください。",
    "msg_password_update_done": "パスワードを変更しました。新しいパスワードでログインしてください。",
    "title_password_reset_failed": "パスワード再設定に失敗しました",
    "비밀번호_8_32자_의무": "パスワードは 8〜32 文字で入力してください。",
    "사용자명_3_16자_의무": "ユーザー名は 3〜16 文字で入力してください。",
    "만료_재_송신_의무": "認証の有効期限が切れました。認証コードを再送してください。",
}


_LOCALE_DICT = {
    "ko": LABELS_KO,
    "en": LABELS_EN,
    "zh-CN": LABELS_ZH_CN,
    "zh-TW": LABELS_ZH_TW,
    "ja": LABELS_JA,
}

# 한글 주석 — global current locale state (WelcomeDialog 4 toggle 시점 동적 갱신 entry)
_CURRENT_LOCALE: str = "ko"


def set_locale(locale: str) -> None:
    """current locale 갱신 — WelcomeDialog 4 lang toggle chain 의 의 entry."""
    global _CURRENT_LOCALE
    if locale in _LOCALE_DICT:
        _CURRENT_LOCALE = locale


def get_locale() -> str:
    """current locale 반환."""
    return _CURRENT_LOCALE


def tr(key: str, locale: str | None = None) -> str:
    """label key → locale 별 text — fallback chain: locale dict → ko dict → key.

    Parameters
    ----------
    key : str
        labels key (예: "tootalk_그룹_만들기").
    locale : str | None
        명시 locale (None 시점 global _CURRENT_LOCALE 활용).
    """
    loc = locale or _CURRENT_LOCALE
    d = _LOCALE_DICT.get(loc, LABELS_KO)
    val = d.get(key)
    if val:
        return val
    # cycle 169.414 — ZH-TW miss → ZH-CN fallback chain (Traditional → Simplified intermediate)
    if loc == "zh-TW":
        cn_val = LABELS_ZH_CN.get(key)
        if cn_val:
            return cn_val
    return LABELS_KO.get(key, key)
