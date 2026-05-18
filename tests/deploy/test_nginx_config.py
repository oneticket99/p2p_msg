# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 112 — nginx config 구조 검증.

`deploy/nginx/nginx.conf` + `conf.d/tootalk.conf` 의 의무 directive 의
정합 + 5 rate limit zone + 8 location + 5 보안 header + TLS 1.2/1.3 +
Let's Encrypt path + WebSocket upgrade chain 의 grep-style 검증.

본 module 범위 외
----------------
- `nginx -t` 실 실행 — 별개 manual test 의무 (의존성 docker + nginx
  image 의 host install 부재).
- HTTPS handshake smoke — 실 인증서 발급 후 의 manual test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_DEPLOY_DIR = Path(__file__).resolve().parents[2] / "deploy" / "nginx"
_NGINX_CONF = _DEPLOY_DIR / "nginx.conf"
_TOOTALK_CONF = _DEPLOY_DIR / "conf.d" / "tootalk.conf"


@pytest.fixture(scope="module")
def nginx_conf_text() -> str:
    assert _NGINX_CONF.is_file(), f"{_NGINX_CONF} 부재"
    return _NGINX_CONF.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tootalk_conf_text() -> str:
    assert _TOOTALK_CONF.is_file(), f"{_TOOTALK_CONF} 부재"
    return _TOOTALK_CONF.read_text(encoding="utf-8")


class TestNginxBaseConfig:
    """`deploy/nginx/nginx.conf` 의 base 의무 directive."""

    def test_file_exists(self, nginx_conf_text: str) -> None:
        assert nginx_conf_text

    def test_worker_processes_auto(self, nginx_conf_text: str) -> None:
        assert "worker_processes auto" in nginx_conf_text

    def test_includes_conf_d(self, nginx_conf_text: str) -> None:
        assert "/etc/nginx/conf.d/*.conf" in nginx_conf_text

    def test_server_tokens_off(self, nginx_conf_text: str) -> None:
        assert "server_tokens off" in nginx_conf_text

    def test_gzip_enabled(self, nginx_conf_text: str) -> None:
        assert "gzip on" in nginx_conf_text


class TestNginxRateLimitZones:
    """5 rate limit zone 의 정의 검증 (Item 3 §4.4 정합)."""

    def test_auth_zone_present(self, nginx_conf_text: str) -> None:
        assert "zone=auth_zone" in nginx_conf_text

    def test_api_zone_present(self, nginx_conf_text: str) -> None:
        assert "zone=api_zone" in nginx_conf_text

    def test_bot_zone_present(self, nginx_conf_text: str) -> None:
        assert "zone=bot_zone" in nginx_conf_text

    def test_upload_zone_present(self, nginx_conf_text: str) -> None:
        assert "zone=upload_zone" in nginx_conf_text

    def test_ws_conn_zone_present(self, nginx_conf_text: str) -> None:
        assert "zone=ws_conn" in nginx_conf_text


class TestNginxRealIP:
    """Docker bridge X-Forwarded-For 신뢰 chain."""

    def test_set_real_ip_from_docker_bridge(self, nginx_conf_text: str) -> None:
        assert "set_real_ip_from 172.16.0.0/12" in nginx_conf_text

    def test_real_ip_header_xff(self, nginx_conf_text: str) -> None:
        assert "real_ip_header X-Forwarded-For" in nginx_conf_text

    def test_real_ip_recursive_on(self, nginx_conf_text: str) -> None:
        assert "real_ip_recursive on" in nginx_conf_text


class TestNginxVirtualHostHTTPS:
    """`tootalk.conf` 의 HTTPS server block 정합."""

    def test_listen_443_ssl_http2(self, tootalk_conf_text: str) -> None:
        assert "listen 443 ssl http2" in tootalk_conf_text

    def test_http_80_redirect(self, tootalk_conf_text: str) -> None:
        assert "listen 80 default_server" in tootalk_conf_text
        assert "return 301 https://" in tootalk_conf_text

    def test_acme_challenge_location(self, tootalk_conf_text: str) -> None:
        assert "/.well-known/acme-challenge/" in tootalk_conf_text
        assert "/var/www/certbot" in tootalk_conf_text

    def test_tls_protocols_modern_only(self, tootalk_conf_text: str) -> None:
        # 한글 주석: TLSv1.2 + TLSv1.3 만 허용 (1.0/1.1 reject)
        assert "ssl_protocols TLSv1.2 TLSv1.3" in tootalk_conf_text

    def test_letsencrypt_cert_path(self, tootalk_conf_text: str) -> None:
        assert "/etc/letsencrypt/live/" in tootalk_conf_text
        assert "fullchain.pem" in tootalk_conf_text
        assert "privkey.pem" in tootalk_conf_text

    def test_ocsp_stapling(self, tootalk_conf_text: str) -> None:
        assert "ssl_stapling on" in tootalk_conf_text
        assert "ssl_stapling_verify on" in tootalk_conf_text


class TestNginxSecurityHeaders:
    """5 보안 header 정합."""

    def test_hsts_header(self, tootalk_conf_text: str) -> None:
        assert "Strict-Transport-Security" in tootalk_conf_text

    def test_x_frame_options(self, tootalk_conf_text: str) -> None:
        assert 'X-Frame-Options "SAMEORIGIN"' in tootalk_conf_text

    def test_x_content_type_nosniff(self, tootalk_conf_text: str) -> None:
        assert 'X-Content-Type-Options "nosniff"' in tootalk_conf_text

    def test_referrer_policy(self, tootalk_conf_text: str) -> None:
        assert "Referrer-Policy" in tootalk_conf_text

    def test_csp_default_self(self, tootalk_conf_text: str) -> None:
        assert "Content-Security-Policy" in tootalk_conf_text
        assert "default-src 'self'" in tootalk_conf_text


class TestNginxProxyHeaders:
    """request_id + IP forwarding 의 upstream 전파."""

    def test_x_request_id_propagation(self, tootalk_conf_text: str) -> None:
        assert "X-Request-ID" in tootalk_conf_text

    def test_x_real_ip_propagation(self, tootalk_conf_text: str) -> None:
        assert "X-Real-IP $remote_addr" in tootalk_conf_text

    def test_x_forwarded_for_propagation(self, tootalk_conf_text: str) -> None:
        assert "X-Forwarded-For $proxy_add_x_forwarded_for" in tootalk_conf_text

    def test_x_forwarded_proto(self, tootalk_conf_text: str) -> None:
        assert "X-Forwarded-Proto $scheme" in tootalk_conf_text


class TestNginxLocations:
    """8 location 의 정합 검증."""

    def test_auth_location_present(self, tootalk_conf_text: str) -> None:
        # auth/signup/login/otp/password_reset 분리
        assert "/api/auth/" in tootalk_conf_text or "signup|login" in tootalk_conf_text

    def test_bot_location_streaming_buffering_off(
        self, tootalk_conf_text: str
    ) -> None:
        assert "/api/bot/" in tootalk_conf_text
        assert "proxy_buffering off" in tootalk_conf_text

    def test_file_upload_location(self, tootalk_conf_text: str) -> None:
        assert "/api/files/" in tootalk_conf_text or "upload|chunk" in tootalk_conf_text
        assert "client_max_body_size 100M" in tootalk_conf_text

    def test_websocket_upgrade_chain(self, tootalk_conf_text: str) -> None:
        # WebSocket upgrade chain — Upgrade + Connection upgrade
        assert "/ws" in tootalk_conf_text
        assert "Upgrade $http_upgrade" in tootalk_conf_text
        assert 'Connection "upgrade"' in tootalk_conf_text
        # 3600s read/send timeout (long-lived WS)
        assert "proxy_read_timeout 3600s" in tootalk_conf_text

    def test_healthz_no_log(self, tootalk_conf_text: str) -> None:
        assert "/healthz" in tootalk_conf_text
        assert "access_log off" in tootalk_conf_text


class TestNginxUpstreamHosts:
    """upstream host 의 docker-compose service name 정합."""

    def test_upstream_web(self, tootalk_conf_text: str) -> None:
        assert "http://web:8080" in tootalk_conf_text

    def test_upstream_ws(self, tootalk_conf_text: str) -> None:
        assert "http://ws:8765" in tootalk_conf_text
