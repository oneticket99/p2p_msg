# SPDX-License-Identifier: GPL-3.0-or-later
"""클라이언트 443 nginx 하드코딩 부재 guard 테스트 — cycle 169.823.

데모 서버 nginx 443 reverse-proxy 의 web/ws upstream 컨테이너 다운 시 502.
host-publish 된 8765 직결만 동작하므로, 클라이언트 REST fallback 은 절대
``https://{host}`` (443) 를 가리키면 안 된다 (config.api_base 무력화 시 죽은
443 경로로 빠지는 회귀 차단). 전수 제거(cycle 169.823) 영구 잠금.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# 한글 주석 — 저장소 루트 (본 파일 = tests/app/ 하위)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _REPO_ROOT / "app"

# 한글 주석 — 데모 IP 의 포트 없는 https(=443) literal. 8765/8443 명시 포트는 별도 허용.
_BARE_443 = re.compile(r'https://114\.207\.112\.73"')
# 한글 주석 — 죽은 내부 web 컨테이너 포트 8080 (nginx 443 upstream, host 미공개). 8765 직결로 치환 의무.
_DEAD_8080 = re.compile(r'114\.207\.112\.73:8080')


def _python_sources() -> list[Path]:
    return sorted(_APP_DIR.rglob("*.py"))


class TestNo443Hardcode:
    """app/ 전역 포트 없는 https 443 데모 IP literal 부재."""

    def test_no_bare_443_literal_in_app(self) -> None:
        offenders: list[str] = []
        for src in _python_sources():
            text = src.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if _BARE_443.search(line):
                    offenders.append(f"{src.relative_to(_REPO_ROOT)}:{lineno}")
        assert offenders == [], (
            "포트 없는 https 443 데모 IP 하드코딩 잔존 — 8765 직결로 치환 의무: "
            + ", ".join(offenders)
        )

    def test_no_dead_8080_literal_in_app(self) -> None:
        # 한글 주석 — 죽은 내부 web 컨테이너 포트 8080 하드코딩 부재 (auto-update poller 회귀 차단)
        offenders: list[str] = []
        for src in _python_sources():
            text = src.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if _DEAD_8080.search(line):
                    offenders.append(f"{src.relative_to(_REPO_ROOT)}:{lineno}")
        assert offenders == [], (
            "죽은 web 컨테이너 포트 8080 하드코딩 잔존 — 8765 직결 치환 의무: "
            + ", ".join(offenders)
        )

    @pytest.mark.parametrize(
        "module,attr",
        [
            # 한글 주석 — _DEFAULT_UPDATE_SERVER_URL 3중 정의 전부 8765 잠금 (cycle 169.823 reviewer HIGH)
            ("app.ui._menu_bar_mixin", "_DEFAULT_UPDATE_SERVER_URL"),
            ("app.ui._update_lifecycle_mixin", "_DEFAULT_UPDATE_SERVER_URL"),
            ("app.ui.main_window", "_DEFAULT_UPDATE_SERVER_URL"),
        ],
    )
    def test_update_server_url_is_8765(self, module: str, attr: str) -> None:
        # 한글 주석 — 자동 업데이트 server URL 도 http 8765 직결 (443 nginx + 죽은 8080 우회)
        import importlib

        mod = importlib.import_module(module)
        url = getattr(mod, attr)
        assert url == "http://114.207.112.73:8765", f"{attr}={url!r} — 8765 직결 기대"
        assert ":443" not in url and ":8080" not in url and not url.startswith("https://114")

    def test_no_demo_ip_routing_literal_outside_config(self) -> None:
        # 한글 주석 — cycle 169.852 codex §4.6 수렴 lock: 운영 demo IP api_base routing
        # literal "http://114.207.112.73:8765" 은 app/core/config.py(DEMO_FALLBACK_API_BASE
        # 단일 소스)만 허용. UI mixin/update URL 중복 literal 재발 차단(silent wrong-endpoint).
        # settings_dialog 표시값 + net client docstring 예시(routing 아님)는 제외.
        routing_lit = re.compile(r'"http://114\.207\.112\.73:8765"')
        allow = {"core/config.py"}
        offenders: list[str] = []
        for src in _python_sources():
            rel = str(src.relative_to(_APP_DIR))
            if rel in allow:
                continue
            for lineno, line in enumerate(
                src.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if routing_lit.search(line):
                    offenders.append(f"{src.relative_to(_REPO_ROOT)}:{lineno}")
        assert offenders == [], (
            "demo IP routing literal 잔존 — config.DEMO_FALLBACK_API_BASE 수렴 의무: "
            + ", ".join(offenders)
        )
