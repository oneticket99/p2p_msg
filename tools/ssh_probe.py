#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 데모 서버 (114.207.112.73) SSH 접속 + SMTP 진단 + 설치 chain.

.env.ssh credential load + paramiko SSH client + 명령 chain 실행.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("paramiko 미설치 — `.venv/bin/pip install paramiko`", file=sys.stderr)
    sys.exit(2)


_ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict:
    """KEY=VALUE 파일 load."""

    out: dict = {}
    if not path.is_file():
        print(f"env 파일 부재 — {path}", file=sys.stderr)
        sys.exit(3)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def main() -> int:
    env = load_env(_ROOT / ".env.ssh")
    host = env.get("SSH_HOST", "").strip()
    port = int(env.get("SSH_PORT", "22"))
    user = env.get("SSH_USER", "").strip()
    password = env.get("SSH_PASS", "").strip()
    key_path = env.get("SSH_KEY_PATH", "").strip()

    if not host or not user:
        print("SSH_HOST + SSH_USER 의무 — .env.ssh 작성 검증", file=sys.stderr)
        return 4
    if not password and not key_path:
        print("SSH_PASS 또는 SSH_KEY_PATH 의무", file=sys.stderr)
        return 5

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    connect_kwargs: dict = {
        "hostname": host,
        "port": port,
        "username": user,
        "timeout": 10,
        "look_for_keys": False,
        "allow_agent": False,
    }
    if key_path:
        connect_kwargs["key_filename"] = str(Path(key_path).expanduser())
    if password:
        connect_kwargs["password"] = password

    print(f"[ssh] connect {user}@{host}:{port}")
    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException as e:
        print(f"[ssh] auth 실패 — {e}", file=sys.stderr)
        return 6
    except paramiko.SSHException as e:
        print(f"[ssh] SSH 오류 — {e}", file=sys.stderr)
        return 7
    except OSError as e:
        print(f"[ssh] network 오류 — {e}", file=sys.stderr)
        return 8

    # 진단 명령 chain — SMTP 설치 여부 + listen 포트 + 방화벽
    cmd = " ; ".join([
        "echo '=== uname ===' && uname -a",
        "echo '=== os release ===' && cat /etc/os-release | head -5",
        "echo '=== postfix status ===' && systemctl status postfix 2>&1 | head -10 || echo 'postfix 미설치 또는 systemctl 부재'",
        "echo '=== opendkim status ===' && systemctl status opendkim 2>&1 | head -5 || echo 'opendkim 미설치'",
        "echo '=== listen ports ===' && (sudo ss -lntp 2>/dev/null || ss -lnt) | grep -E ':25|:587|:465|:80|:443|:8765' || echo 'SMTP/HTTP 포트 listen 부재'",
        "echo '=== firewall ===' && (sudo ufw status 2>/dev/null || sudo iptables -L INPUT -n --line-numbers 2>/dev/null | head -15 || echo 'firewall 도구 부재')",
        "echo '=== dpkg postfix ===' && dpkg -l postfix opendkim 2>/dev/null || rpm -qa | grep -E 'postfix|opendkim' || echo '패키지 매니저 부재'",
    ])

    print("[ssh] 진단 명령 실행")
    _, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    client.close()

    print("--- stdout ---")
    print(out)
    if err.strip():
        print("--- stderr ---")
        print(err)
    print(f"--- exit_code = {exit_code} ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
