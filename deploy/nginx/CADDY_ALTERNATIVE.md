# Caddy 대안 평가 — Phase 4 cycle 112

본 문서 = nginx 1.27-alpine 의 대안 의 `Caddy 2-alpine` 도입 검토. 정합 = [Phase 4 infra setup §4.9](../../docs/exec-plans/active/2026-05-22-phase4-infra-setup.md).

## 1. 비교 표

| 기준 | nginx 1.27-alpine | Caddy 2-alpine |
|---|---|---|
| 이미지 크기 | ~50 MB | ~60 MB |
| TLS 자동화 | 별개 certbot 의무 (本 cycle 112) | 내장 ACME client (Caddyfile auto-HTTPS) |
| config syntax | nginx.conf + conf.d/ (전통적) | Caddyfile (단순 + JSON 변환) |
| WebSocket upgrade | proxy_set_header + Upgrade chain 명시 | `reverse_proxy` directive 의 inline 처리 |
| rate limit | `limit_req_zone` (built-in) | `caddy-ratelimit` 외부 plugin 의무 |
| log format | JSON escape=json | JSON 의무 default (구조화) |
| HTTP/3 | nginx 1.25+ 의 experimental | Caddy 2.6+ 의 stable default |
| memory footprint | 낮음 (~20 MB) | 중간 (~40 MB, Go runtime) |
| 운영 익숙도 | 본 팀 의무 (Toonation 기존 운영 인력) | 학습 비용 (Go config DSL) |
| 인증서 갱신 | certbot cron + nginx -s reload | 자동 갱신 + 무중단 reload |

## 2. 권장 결정

**Phase 4 = nginx 유지**. 이유:

1. Toonation 기존 운영 인력 의 nginx 친화 (학습 비용 0).
2. cycle 112 의 certbot 통합 + cron renew script 완성 — 자동화 의 격차 회수.
3. `limit_req_zone` built-in — Caddy 의 외부 plugin 의존성 부재.
4. SSL/TLS 본 cycle 의 manual control 의 명확성 (cipher + protocols + stapling).
5. nginx 1.27 의 HTTP/3 experimental 의 본 cycle 의 stability 의무 미충족 시 nginx fork (angie / freenginx) 의 대안 의 hot path 가능.

## 3. Caddy 전환 시점 (Phase 5+ 검토)

- 다음 조건 의 1개 이상 충족 시 Caddy 전환 재검토:
  - HTTP/3 의 production 안정성 의무 도달 (사용자 경험 향상 +20% 이상 측정 시).
  - 운영팀 의 Go 친화 + Caddyfile DSL 학습 의무 도달.
  - Let's Encrypt cron 갱신 의 의 fail rate 의 의 1% 이상 도달 (자동화 부재).

## 4. 대안 Caddyfile sample (참고용)

```caddy
{
    email admin@tootalk.demo
    auto_https on
}

tootalk.demo, www.tootalk.demo {
    log {
        output stdout
        format json
    }

    # rate limit (caddy-ratelimit plugin 의무)
    @auth path /api/auth/*
    rate_limit @auth 10r/m

    @bot path /api/bot/*
    rate_limit @bot 20r/m

    # WebSocket upgrade
    handle /ws {
        reverse_proxy ws:8765 {
            header_up Host {host}
            header_up X-Forwarded-For {remote}
        }
    }

    # REST API
    handle /api/* {
        reverse_proxy web:8080 {
            header_up X-Real-IP {remote}
            header_up X-Request-ID {uuid}
        }
    }

    # 정적 fallback
    file_server
}
```

## 5. 참조

- [nginx 1.27 release notes](https://nginx.org/en/CHANGES)
- [Caddy 2 docs](https://caddyserver.com/docs/)
- [caddy-ratelimit plugin](https://github.com/mholt/caddy-ratelimit)
- [Phase 4 infra setup §4.9](../../docs/exec-plans/active/2026-05-22-phase4-infra-setup.md)
