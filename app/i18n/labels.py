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
    "메시지를_입력하세요": "메시지를 입력하세요…",  # app/ui/group_chat_view.py:171
    "멤버_보기": "멤버 보기",  # app/ui/group_chat_view.py:133
    "미입력_시_사용자명_사용": "미입력 시 사용자명 사용",  # app/ui/add_friend_dialog.py:150
    "별명_선택": "별명 (선택):",  # app/ui/add_friend_dialog.py:148
    "보내기": "보내기",  # app/ui/group_chat_view.py:174
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
}
LABELS_ZH_TW: dict[str, str] = {
    "친구와_직접_연결_p2p_메신저": "P2P 即時通訊 — 朋友直接連線",
    "원격_데스크탑_도움_gplv3_oss": "遠端桌面協助 + GPLv3 OSS",
    "시작하기": "開始",
    "tootalk_그룹_만들기": "TooTalk · 建立群組",
    "tootalk_채널_만들기": "TooTalk · 建立頻道",
    "투네이션_고객센터": "Toonation 客服",
    "온라인": "線上",
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
    return d.get(key) or LABELS_KO.get(key, key)
