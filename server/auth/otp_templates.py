# SPDX-License-Identifier: GPL-3.0-or-later
"""OTP 이메일 본문 i18n template — Phase 5 Item 1 (cycle 131~140) skeleton."""
from __future__ import annotations
from app.i18n import SUPPORTED_LOCALES, DEFAULT_LOCALE

# 한글 주석 — locale × purpose 의 본문 mapping (Phase 5 i18n 진입 시 .ts 파일로 이전)
_TEMPLATES = {
    ("ko", "signup"): ("[TooTalk] 회원가입 인증코드", "TooTalk 회원가입 인증코드: {code}\n본 코드는 3분 후 만료됩니다."),
    ("en", "signup"): ("[TooTalk] Sign-up verification", "Your TooTalk sign-up code: {code}\nExpires in 3 minutes."),
    ("zh-CN", "signup"): ("[TooTalk] 注册验证码", "TooTalk 注册验证码: {code}\n3 分钟后过期。"),
    ("zh-TW", "signup"): ("[TooTalk] 註冊驗證碼", "TooTalk 註冊驗證碼: {code}\n3 分鐘後過期。"),
    ("ja", "signup"): ("[TooTalk] サインアップ認証コード", "TooTalk サインアップ認証コード: {code}\n3 分後に期限切れ。"),
    ("ko", "password_reset"): ("[TooTalk] 비밀번호 재설정 인증코드", "TooTalk 비밀번호 재설정 인증코드: {code}\n본 코드는 3분 후 만료됩니다."),
    ("en", "password_reset"): ("[TooTalk] Password reset code", "Your TooTalk password reset code: {code}\nExpires in 3 minutes."),
    ("zh-CN", "password_reset"): ("[TooTalk] 密码重置验证码", "TooTalk 密码重置验证码: {code}\n3 分钟后过期。"),
    ("zh-TW", "password_reset"): ("[TooTalk] 密碼重設驗證碼", "TooTalk 密碼重設驗證碼: {code}\n3 分鐘後過期。"),
    ("ja", "password_reset"): ("[TooTalk] パスワードリセットコード", "TooTalk パスワードリセットコード: {code}\n3 分後に期限切れ。"),
}


def render_otp(locale: str, purpose: str, code: str) -> tuple[str, str]:
    """한글 주석 — locale unsupported 시 default ko fallback."""
    loc = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    key = (loc, purpose)
    if key not in _TEMPLATES:
        key = (DEFAULT_LOCALE, purpose)
    subject, body_tpl = _TEMPLATES[key]
    return subject, body_tpl.format(code=code)
