#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 데모 서버 (114.207.112.73) 임의 명령 단발 SSH 실행.

.env.ssh credential load + paramiko SSH client + argv[1] 명령 실행 + stdout/stderr 출력.
사용 — `.venv/bin/python3 tools/ssh_exec.py '명령'`
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
    if len(sys.argv) < 2:
        print("사용 — ssh_exec.py '<명령>'", file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    timeout = int(os.environ.get("SSH_EXEC_TIMEOUT", "120"))

    env = load_env(_ROOT / ".env.ssh")
    host = env.get("SSH_HOST", "").strip()
    port = int(env.get("SSH_PORT", "22"))
    user = env.get("SSH_USER", "").strip()
    password = env.get("SSH_PASS", "").strip()
    key_path = env.get("SSH_KEY_PATH", "").strip()

    if not host or not user:
        print("SSH_HOST + SSH_USER 의무", file=sys.stderr)
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
        "timeout": 15,
        "look_for_keys": False,
        "allow_agent": False,
    }
    if key_path:
        connect_kwargs["key_filename"] = str(Path(key_path).expanduser())
    if password:
        connect_kwargs["password"] = password

    print(f"[ssh-exec] connect {user}@{host}:{port}", file=sys.stderr)
    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException as e:
        print(f"[ssh-exec] auth 실패 — {e}", file=sys.stderr)
        return 6
    except paramiko.SSHException as e:
        print(f"[ssh-exec] SSH 오류 — {e}", file=sys.stderr)
        return 7
    except OSError as e:
        print(f"[ssh-exec] network 오류 — {e}", file=sys.stderr)
        return 8

    print(f"[ssh-exec] exec (timeout={timeout}s)", file=sys.stderr)
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    client.close()

    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    print(f"[ssh-exec] exit={exit_code}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
