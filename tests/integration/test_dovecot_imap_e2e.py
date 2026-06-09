# SPDX-License-Identifier: GPL-3.0-or-later
"""mail.dopa.co.kr Dovecot+IMAP e2e smoke — cycle 169.857 M4.

본 test 의 커버 영역:

- IMAP CAPABILITY 응답 형식 검증 (실 서버 unreachable 시 graceful skip)
- SMTP submission 587 auth 강제 검증 (RCPT 거부 확인)
- LMTP unix socket 경로 정합 grep (dovecot_install.sh 안 일관성)
- `tools/dovecot_install.sh` syntax check (bash -n, 실 서버 부재 PASS)
- `tools/mail_user_add.sh` syntax check (bash -n)
- `tools/mail_user_add.sh` 인자 부재 호출 → exit 1 + usage stdout 검증
- `tools/mail_user_add.sh` 사용자명 형식 위반 (공백) → exit 1 + ERROR stdout

총 7 test (6 PASS + 1 SKIP — IMAP 993 live unreachable 시 Test 1 skip).
실 서버 검증 = 사용자 SSH 수동 (Exec Plan §6 G-final).
본 test = headless 자동 검증 — protocol smoke + 스크립트 syntax + usage.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

# 한글 주석: 본 저장소 루트 (tests/integration/ → ../..)
REPO_ROOT = Path(__file__).resolve().parents[2]
DOVECOT_INSTALL_SH = REPO_ROOT / "tools" / "dovecot_install.sh"
MAIL_USER_ADD_SH = REPO_ROOT / "tools" / "mail_user_add.sh"
MAIL_SERVER_HOST = os.environ.get("TOOTALK_MAIL_HOST", "mail.dopa.co.kr")
IMAP_PORT = 993
SMTP_PORT = 587


def _server_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """TCP 연결 가능 여부 — 실 서버 부재 시 graceful skip 분기."""

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


# ----------------------------------------------------------------------
# Test 1: IMAP CAPABILITY 응답 형식
# ----------------------------------------------------------------------


def test_imap_capability_greeting() -> None:
    """IMAP4_SSL 연결 + CAPABILITY 응답 형식 검증.

    실 서버 unreachable (Dovecot 미설치 또는 firewall 차단) 시 skip.
    """

    if not _server_reachable(MAIL_SERVER_HOST, IMAP_PORT):
        pytest.skip(
            f"IMAP {MAIL_SERVER_HOST}:{IMAP_PORT} unreachable — "
            "Dovecot 미설치 또는 서버 도달 불가 (Exec Plan §6 G-final 후 활성)"
        )

    # 한글 주석: imaplib.IMAP4_SSL = 993 SSL/TLS wrapper, capability 응답 = SASL-IR/LITERAL+/STARTTLS 등 토큰 다수
    import imaplib

    m = imaplib.IMAP4_SSL(MAIL_SERVER_HOST, IMAP_PORT)
    try:
        typ, data = m.capability()
        assert typ == "OK", f"CAPABILITY 응답 비정상: {typ}"
        cap_str = b" ".join(data).decode("ascii", errors="ignore")
        # 한글 주석: Dovecot 기본 CAPABILITY 안 IMAP4rev1 토큰 반드시 포함
        assert "IMAP4rev1" in cap_str, f"IMAP4rev1 capability 부재: {cap_str}"
    finally:
        m.logout()


# ----------------------------------------------------------------------
# Test 2: SMTP submission auth 강제
# ----------------------------------------------------------------------


def test_smtp_submission_auth_required() -> None:
    """SMTP 587 STARTTLS + auth 부재 시 RCPT TO 거부 검증.

    smtp_install.sh master.cf submission 의 `permit_sasl_authenticated,reject` 정합.
    """

    if not _server_reachable(MAIL_SERVER_HOST, SMTP_PORT):
        pytest.skip(
            f"SMTP {MAIL_SERVER_HOST}:{SMTP_PORT} unreachable — "
            "smtp_install.sh 미실행 또는 서버 도달 불가"
        )

    # 한글 주석: smtplib.SMTP 평문 + STARTTLS 업그레이드 후 auth 없이 MAIL FROM/RCPT TO 시도
    import smtplib

    s = smtplib.SMTP(MAIL_SERVER_HOST, SMTP_PORT, timeout=5)
    try:
        s.ehlo()
        s.starttls()
        s.ehlo()
        # auth 없이 MAIL FROM/RCPT TO — submission restriction `reject` 로 차단되어야 함
        s.mail("test@example.com")
        code, _ = s.rcpt("noreply@dopa.co.kr")
        # 한글 주석: 530 (auth required) 또는 554 (relay denied) 둘 다 차단 의도 정합
        assert code in (530, 554), f"submission auth 강제 부재: rcpt code={code}"
    finally:
        try:
            s.quit()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Test 3: LMTP unix socket 경로 (로직 명시, 실 서버 부재)
# ----------------------------------------------------------------------


def test_lmtp_socket_path_documented() -> None:
    """Dovecot LMTP unix socket 경로 = `/var/spool/postfix/private/dovecot-lmtp` 정합.

    본 머신 부재 — 실 서버 검증은 사용자 SSH 수동 (Exec Plan §6).
    본 test = dovecot_install.sh 안 socket 경로 일관성 grep 검증.
    """

    content = DOVECOT_INSTALL_SH.read_text(encoding="utf-8")
    # 한글 주석: 10-master.conf + main.cf virtual_transport 양쪽 동일 socket 경로 정합
    assert "private/dovecot-lmtp" in content, \
        "LMTP socket 경로 부재 — dovecot_install.sh 10-master.conf 정합 위반"
    assert "virtual_transport=lmtp:unix:private/dovecot-lmtp" in content, \
        "Postfix virtual_transport 정합 부재"


# ----------------------------------------------------------------------
# Test 4: dovecot_install.sh syntax
# ----------------------------------------------------------------------


def test_dovecot_install_script_syntax() -> None:
    """`bash -n tools/dovecot_install.sh` 구문 검증.

    실 서버 부재 시점에도 PASS — script 자체 syntax 정합.
    """

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash 부재 (Windows 환경) — 본 test 비대상")

    result = subprocess.run(
        [bash, "-n", str(DOVECOT_INSTALL_SH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, \
        f"dovecot_install.sh syntax FAIL: {result.stderr}"


# ----------------------------------------------------------------------
# Test 5: mail_user_add.sh syntax
# ----------------------------------------------------------------------


def test_mail_user_add_script_syntax() -> None:
    """`bash -n tools/mail_user_add.sh` 구문 검증."""

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash 부재 (Windows 환경) — 본 test 비대상")

    result = subprocess.run(
        [bash, "-n", str(MAIL_USER_ADD_SH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, \
        f"mail_user_add.sh syntax FAIL: {result.stderr}"


# ----------------------------------------------------------------------
# Test 6: mail_user_add.sh usage (인자 부재)
# ----------------------------------------------------------------------


def test_mail_user_add_usage_no_args() -> None:
    """인자 없이 호출 시 exit 1 + Usage stdout."""

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash 부재 (Windows 환경) — 본 test 비대상")

    result = subprocess.run(
        [bash, str(MAIL_USER_ADD_SH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1, \
        f"인자 부재 exit code != 1: {result.returncode}"
    # 한글 주석: Usage stdout 정합 — "Usage:" prefix + "<user>" placeholder
    assert "Usage:" in result.stdout, \
        f"Usage stdout 부재: {result.stdout!r}"
    assert "<user>" in result.stdout, \
        f"인자 placeholder 부재: {result.stdout!r}"


# ----------------------------------------------------------------------
# Test 7: mail_user_add.sh 사용자명 형식 검증
# ----------------------------------------------------------------------


def test_mail_user_add_invalid_username_rejected() -> None:
    """사용자명 정합 외 문자 (공백/특수문자) → exit 1 + ERROR stdout."""

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash 부재 (Windows 환경) — 본 test 비대상")

    # 한글 주석: 공백 포함 사용자명 = shell 안전성 위반 + RFC 5321 local-part 정합 위반
    result = subprocess.run(
        [bash, str(MAIL_USER_ADD_SH), "bad user"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1, \
        f"형식 위반 exit code != 1: {result.returncode}"
    assert "형식 오류" in result.stdout or "ERROR" in result.stdout, \
        f"ERROR stdout 부재: {result.stdout!r}"
