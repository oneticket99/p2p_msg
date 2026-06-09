# SPDX-License-Identifier: GPL-3.0-or-later
"""webmail.dopa.co.kr nginx vhost 정합 검증 — cycle 169.858 M2.

본 test 의 커버 영역:

- `deploy/nginx/conf.d/webmail.conf` 파일 존재 + 구조 정합
- server_name webmail.dopa.co.kr 명시 (catch-all `_` 회피)
- TLS cert path = `/etc/letsencrypt/live/webmail.dopa.co.kr/`
- upstream = webmail:8090 (M3 후속 cycle docker-compose 정합)
- location 4종 (`/static/` / `/healthz` / `/api/` / `/`)
- 보안 header 5종 + CSP 메일 본문 정합 (img-src https: + script unsafe-inline)
- brace balance + listen 443 ssl http2

실 nginx -t 검증 = G-final 사용자 SSH 수동 (Exec Plan §7).
본 test = headless 자동 검증 — structural smoke 만.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# 한글 주석: 본 저장소 루트 (tests/integration/ → ../..)
REPO_ROOT = Path(__file__).resolve().parents[2]
WEBMAIL_CONF = REPO_ROOT / "deploy" / "nginx" / "conf.d" / "webmail.conf"


@pytest.fixture(scope="module")
def conf_text() -> str:
    """webmail.conf 본문 read — module scope cache."""

    assert WEBMAIL_CONF.exists(), f"vhost 파일 부재: {WEBMAIL_CONF}"
    return WEBMAIL_CONF.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# Test 1: SPDX header + 기본 메타
# ----------------------------------------------------------------------


def test_spdx_header_present(conf_text: str) -> None:
    """SPDX header GPL-3.0-or-later 존재."""

    assert "SPDX-License-Identifier: GPL-3.0-or-later" in conf_text


def test_cycle_marker_present(conf_text: str) -> None:
    """cycle 169.858 marker + Exec Plan 참조."""

    assert "cycle 169.858" in conf_text
    assert "2026-06-09-webmail-python-backend.md" in conf_text


# ----------------------------------------------------------------------
# Test 2: server_name + listen
# ----------------------------------------------------------------------


def test_server_name_explicit(conf_text: str) -> None:
    """server_name webmail.dopa.co.kr 명시 (catch-all `_` 회피)."""

    assert "server_name webmail.dopa.co.kr;" in conf_text
    # 한글 주석: 명시 server_name 만 — `_` catch-all 부재 (tootalk.conf 와 분리)
    assert "server_name _;" not in conf_text


def test_listen_443_ssl_http2(conf_text: str) -> None:
    """443 SSL HTTP/2 + IPv6 양쪽 listen."""

    assert "listen 443 ssl http2;" in conf_text
    assert "listen [::]:443 ssl http2;" in conf_text


# ----------------------------------------------------------------------
# Test 3: TLS cert path
# ----------------------------------------------------------------------


def test_tls_cert_path_webmail(conf_text: str) -> None:
    """TLS cert path = Let's Encrypt webmail.dopa.co.kr 별도 cert."""

    assert "/etc/letsencrypt/live/webmail.dopa.co.kr/fullchain.pem" in conf_text
    assert "/etc/letsencrypt/live/webmail.dopa.co.kr/privkey.pem" in conf_text


def test_tls_protocols_modern(conf_text: str) -> None:
    """TLS protocols = TLSv1.2 + TLSv1.3 만 (구버전 차단)."""

    assert "ssl_protocols TLSv1.2 TLSv1.3;" in conf_text


# ----------------------------------------------------------------------
# Test 4: upstream + reverse proxy
# ----------------------------------------------------------------------


def test_upstream_webmail_8090(conf_text: str) -> None:
    """upstream = webmail:8090 (M3 docker-compose 서비스 정합)."""

    # 한글 주석: proxy_pass 3 location 전수 webmail:8090 target 정합
    assert conf_text.count("http://webmail:8090") >= 3


def test_proxy_headers_complete(conf_text: str) -> None:
    """proxy header 6종 — X-Request-ID/X-Real-IP/X-Forwarded-*/Host."""

    expected = [
        "proxy_set_header X-Request-ID $request_id;",
        "proxy_set_header X-Real-IP $remote_addr;",
        "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "proxy_set_header X-Forwarded-Proto $scheme;",
        "proxy_set_header X-Forwarded-Host $host;",
        "proxy_set_header Host $host;",
    ]
    for header in expected:
        assert header in conf_text, f"proxy header 부재: {header}"


# ----------------------------------------------------------------------
# Test 5: 보안 header 5종
# ----------------------------------------------------------------------


def test_security_headers_five(conf_text: str) -> None:
    """보안 header 5종 (tootalk.conf 정합)."""

    expected = [
        "Strict-Transport-Security",
        'X-Frame-Options "SAMEORIGIN"',
        'X-Content-Type-Options "nosniff"',
        'Referrer-Policy "strict-origin-when-cross-origin"',
        "Content-Security-Policy",
    ]
    for header in expected:
        assert header in conf_text, f"보안 header 부재: {header}"


def test_csp_mail_body_compatible(conf_text: str) -> None:
    """CSP 메일 본문 정합 — img-src https: + script unsafe-inline (HTMX)."""

    # 한글 주석: img-src https: = 외부 이미지 표시 (메일 본문 안 원격 이미지)
    assert "img-src 'self' data: https:" in conf_text
    # 한글 주석: script-src unsafe-inline = HTMX 인라인 스크립트 정합
    assert "script-src 'self' 'unsafe-inline'" in conf_text


# ----------------------------------------------------------------------
# Test 6: location 4종
# ----------------------------------------------------------------------


def test_location_blocks_four(conf_text: str) -> None:
    """location 4종 — /static/ / /healthz / /api/ / /."""

    expected_patterns = [
        "location /static/ {",
        "location /healthz {",
        "location /api/ {",
        "location / {",
    ]
    for pattern in expected_patterns:
        assert pattern in conf_text, f"location 부재: {pattern}"


def test_static_alias_path(conf_text: str) -> None:
    """static alias = nginx html 디렉토리 안 webmail-static/."""

    assert "alias /usr/share/nginx/html/webmail-static/;" in conf_text


def test_healthz_access_log_off(conf_text: str) -> None:
    """healthz endpoint 의 access_log off — 모니터링 noise 회피."""

    assert "access_log off;" in conf_text


# ----------------------------------------------------------------------
# Test 7: 첨부 upload 한도 + timeout
# ----------------------------------------------------------------------


def test_client_max_body_size_25m(conf_text: str) -> None:
    """첨부 upload 한도 = 25M (메일 표준)."""

    assert "client_max_body_size 25M;" in conf_text


def test_proxy_timeout_60s(conf_text: str) -> None:
    """proxy timeout = 60s (IMAP 검색 / 대용량 본문 정합)."""

    assert "proxy_send_timeout 60s;" in conf_text
    assert "proxy_read_timeout 60s;" in conf_text


# ----------------------------------------------------------------------
# Test 8: brace balance + 구조 정합
# ----------------------------------------------------------------------


def test_brace_balance(conf_text: str) -> None:
    """`{` 와 `}` 수 일치 — nginx config 구조 정합."""

    # 한글 주석: 주석 처리 후 brace count — `#` 시작 line 제거하여 정확성 향상
    body_lines = [
        line for line in conf_text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    body = "\n".join(body_lines)
    open_count = body.count("{")
    close_count = body.count("}")
    assert open_count == close_count, \
        f"brace 불균형: open={open_count} close={close_count}"


def test_single_server_block(conf_text: str) -> None:
    """server block 1개 만 — HTTPS 443 단독 (HTTP 80 부재, tootalk.conf 가 처리)."""

    # 한글 주석: `server {` 패턴 count — 정확히 1
    server_blocks = [
        line for line in conf_text.splitlines()
        if line.strip().startswith("server {")
    ]
    assert len(server_blocks) == 1, \
        f"server block 수 != 1: {len(server_blocks)}"


# ----------------------------------------------------------------------
# Test 9: 한글 주석 의무 M4
# ----------------------------------------------------------------------


def test_korean_comment_present(conf_text: str) -> None:
    """한글 주석 의무 M4 — `# 한글 주석:` prefix 다수."""

    korean_comment_count = conf_text.count("# 한글 주석:")
    # 한글 주석: 최소 5건 — 의도/배경/설계 분기 명시 정합
    assert korean_comment_count >= 5, \
        f"한글 주석 부족: {korean_comment_count} < 5"
