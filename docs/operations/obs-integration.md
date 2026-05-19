---
title: "OBS Integration — optional binding (cycle 151 사용자 directive 회수)"
owner: oneticket99
last_verified: 2026-05-19T22:00:00+09:00
status: active
cycle: 151
---


> TooTalk client/server 의 OBS Studio install 의무 부재 ([[feedback-obs-install-not-required]] 정합).
> 본 문서 = OBS Studio active 사용자 환경 의 optional binding chain. 친구 A (OBS 사용자) ↔ 친구 B (도움 제공자) 원격 제어 chain prerequisite.
> 정합: `app/bot/obs_websocket_client.py` · `app/bot/streaming_helper.py` · memory `project_bot_framework.md` · `project_phase2_remote_control_differentiator.md`.

본 문서 = OBS Studio v28+ 의 obs-websocket v5 protocol optional binding. TooTalk 자체 install 강제 부재 — 사용자 OBS 환경 active 시 chat overlay alert + scene 제어 통합 가능. 부재 시 graceful skip (chat 메신저 + 친구 + 그룹 + emoji + 자동 업데이트 chain 정상 활용).

---

## 1. OBS Studio v28+ obs-websocket v5 설치

OBS Studio v28 부터 obs-websocket v5 가 내장되어 별도 plugin 설치 부재.

- `Tools → WebSocket Server Settings` 메뉴 진입
- `Enable WebSocket server` 체크
- `Server Port` = 4455 (default)
- `Enable Authentication` 체크 + `Server Password` 설정
- `Show Connect Info` 버튼 → password + 연결 정보 확인

OBS v27 이하 = obs-websocket plugin v4 별도 설치 필요. **본 cycle skeleton 은 v5 protocol 전용** — v4 호환 부재.

## 2. Port 4455 방화벽 + 네트워크 설정

기본 설정 = `localhost:4455` (동일 PC 안 TooTalk + OBS 가정).

- 동일 PC = 방화벽 추가 설정 부재
- 별도 PC = TooTalk PC 에서 OBS PC 의 4455 port TCP 허용 + OBS PC 의 inbound 4455 방화벽 허용 (Windows Defender Firewall / iptables 등)
- 인터넷 노출 절대 금지 — VPN / Tailscale 등 private network 만 허용

## 3. Password 설정 + env 주입

TooTalk 가 OBS WebSocket 연결 시 사용할 password 는 환경변수로 주입한다.

- `OBS_HOST` — OBS Studio host (default `localhost`)
- `OBS_PORT` — WebSocket Server port (default `4455`)
- `OBS_PASSWORD` — Server Password (default 빈 문자열 = 무인증)

`app.bot.obs_websocket_client.build_default_client()` 가 위 3 env 를 읽어 default client 생성. 정합 — `dotenv` / shell rc / systemd unit `Environment=` directive 어디서나 주입 가능.

## 4. 4 streaming platform chat overlay alert 흐름

`StreamingHelperDispatcher` 가 platform 별 chat handler 등록 + OBS browser source `trigger_alert` dispatch chain 을 제공.

| Platform | callback method | OBS alert_id |
| --- | --- | --- |
| YouTube | `youtube_chat_handler(payload)` | `youtube_chat` |
| Twitch | `twitch_chat_handler(payload)` | `twitch_chat` |
| CHZZK (네이버) | `chzzk_chat_handler(payload)` | `chzzk_chat` |
| Kick | `kick_chat_handler(payload)` | `kick_chat` |

payload 예시:

```python
payload = {
    "viewer": "username",
    "message": "안녕하세요",
    "amount": 5000,        # 후원 / 구독 금액 (옵션)
    "tier": "tier1",       # 구독 등급 (옵션)
    "platform": "twitch",
}
```

각 platform 의 실 chat stream binding (YouTube Data API / Twitch IRC / CHZZK polling / Kick WebSocket) 은 **별개 cycle** 진행.

## 5. Nightbot 등가 기능 매핑

| Nightbot | TooTalk 방송 도우미 |
| --- | --- |
| `!command` list | `StreamingHelperBot.commands` |
| custom command add/remove | `add_command` / `remove_command` |
| cooldown per command | `StreamingCommand.cooldown_seconds` |
| chat alert overlay | `ObsWebSocketClient.trigger_alert` |
| scene switch on event | `ObsWebSocketClient.set_current_scene` |
| !uptime 자동 산출 | 별개 cycle — streaming session 통합 |
| 단어 필터 / moderation | `customer_service_bot` + `emoji_dmca_check` 연동 |

## 6. customer_service_bot 연동

`app.bot.customer_service_bot` (LLM 기반 Q&A) + `streaming_helper` 의 통합 경로.

1. viewer chat → `StreamingHelperBot.apply_command()` — `!command` 의 즉답 응답
2. command 미매치 시 → `customer_service_bot` 의 LLM dispatch (옵션)
3. LLM 응답 → `StreamingHelperDispatcher.dispatch()` — OBS browser source overlay alert
4. donation / sub event → `trigger_alert("donation", payload)` — 후원 알림 매크로

각 단계 cooldown + spam 차단 + DMCA emoji 체크는 기존 module (`escalation_queue` / `emoji_dmca_check` / `usage_tracker`) 의 재활용 패턴.

---

마지막 갱신: 2026-05-19 (cycle 141 — OBS WebSocket actual binding skeleton 신설)
