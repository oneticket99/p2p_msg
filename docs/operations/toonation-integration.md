# Toonation REST API 통합 운영서 — cycle 140

> Phase 5 Item 4 bot framework 마무리 chain 의 prerequisite skeleton.
> 본 문서 = Toonation REST API client + customer_service_bot dispatch chain
> 정합 + 사용자 manual 확정 의무 5건.

---

## 1. 개요

cycle 140 = TooTalk 의 bot framework Phase 5 Item 4 의 prerequisite —
Toonation REST API client (`app/bot/toonation_client.py`) skeleton 신설 +
`customer_service_bot.py` 의 dispatch chain 의 RAG source 추가.

본 cycle 의 범위:

- `ToonationClient` 6 method skeleton (graceful — actual REST binding 부재)
- `ToonationDonationRecord` + `ToonationStreamerProfile` 의 frozen dataclass
- `customer_service_bot` 의 dispatch keyword match → ToonationClient 호출 chain
- pytest 27건 신규 + 1 신규 module + 1 module 갱신

본 cycle 의 범위 외 (Phase 5 본격 cycle 의무):

- 실 Toonation REST endpoint binding (사용자 확정 의무)
- OAuth2 + refresh token 의 인증 flow
- webhook + SSE 의 real-time donation push
- rate limit + retry + circuit breaker
- 캐시 (Redis 등 의 statistics cache)

---

## 2. Toonation REST API 5 endpoint (placeholder)

| HTTP method | endpoint | 용도 |
| --- | --- | --- |
| GET | `/streamers/{streamer_id}` | streamer profile (nickname + platform + follower_count + total_donations_krw) |
| GET | `/streamers/{streamer_id}/donations?limit=N` | 최근 도네이션 list (시각 DESC) |
| GET | `/donations/{donation_id}` | 단일 도네이션 상세 |
| GET | `/donations?donor={name}&limit=N` | donor_name substring 검색 |
| GET | `/streamers/{streamer_id}/stats/today` | 오늘 (KST 자정 기준) 누적 후원 총액 |
| POST | `/streamers/{streamer_id}/alerts/test` | OBS 위젯 테스트 알림 |

> placeholder base URL = `https://toon.at/api/v1`. 실 endpoint = 사용자 확정 의무.

---

## 3. ToonationClient method mapping

| method | 반환 type | graceful 반환 (httpx 부재 또는 api_key 부재) |
| --- | --- | --- |
| `get_streamer_profile(streamer_id)` | `Optional[ToonationStreamerProfile]` | `None` |
| `list_recent_donations(streamer_id, limit=20)` | `list[ToonationDonationRecord]` | `[]` |
| `get_donation_detail(donation_id)` | `Optional[ToonationDonationRecord]` | `None` |
| `search_donations_by_donor(donor_name, limit=50)` | `list[ToonationDonationRecord]` | `[]` |
| `get_total_donations_today(streamer_id)` | `int` | `0` |
| `post_alert_test(streamer_id, message)` | `bool` | `False` |

모든 method = async + ValueError validation (streamer_id 양수 + limit 양수 +
빈 문자열 차단).

env factory `build_default_client()` = `TOONATION_API_KEY` + `TOONATION_BASE_URL`
환경변수 binding (strip + None graceful).

---

## 4. customer_service_bot dispatch chain

`customer_service_bot.CustomerServiceBot.__init__` 의 신규 keyword arg
`toonation_client: Optional[ToonationClient] = None`.

dispatch keyword 8건 (`_TOONATION_DISPATCH_KEYWORDS`):

- 도네이션
- 후원 통계
- 후원자 검색
- 오늘 누적
- 오늘 후원
- 누적 후원
- donation
- donor

`answer(user_id, user_message, history)` 호출 시 `_matches_toonation_dispatch`
check → match → `_compose_toonation_block` 호출 → system_content append.

block 구성:

- API base URL 안내
- Phase 5 cycle 의 actual binding 안내
- placeholder streamer_id=1 의 `get_total_donations_today` graceful 결과
- 사용자 streamer_id session binding 의무 안내

---

## 5. 사용자 확정 의무 5건 (Phase 5 cycle 진입 전)

1. **실 Toonation REST base URL** — placeholder `https://toon.at/api/v1` 의
   actual production endpoint 확정.
2. **API key 발급 절차** — Toonation 의 official API key issuance flow 확정
   (OAuth2 또는 static API key 중 택일).
3. **streamer_id session binding** — TooTalk 사용자 의 Toonation streamer_id
   mapping table (users 의 별개 column 또는 별개 user_toonation_link table).
4. **rate limit policy** — Toonation 의 의 per-key rate limit 확정 + 클라이언트
   의 retry / circuit breaker 정책.
5. **webhook endpoint** — real-time donation push 수신 endpoint 의 host +
   path + signature 검증 secret 확정.

---

## 6. Phase 5 본격 cycle 진입 의무

cycle 140 직후 의무:

1. 사용자 manual 의 §5 5건 확정 chat
2. `app/bot/toonation_client.py` 의 actual REST binding (httpx AsyncClient)
3. `users_toonation_link` table migration 또는 `users` 의 `toonation_streamer_id`
   column 신설
4. `customer_service_bot` 의 dispatch chain 의 streamer_id session binding
5. `tests/app/bot/test_toonation_client.py` 의 real HTTP mock (respx 등) 통합
6. webhook handler (별개 cycle — `app/server/toonation_webhook.py` 신설)
7. README + History + ARCHITECTURE 의 §6 Phase 5 progress 갱신

---

마지막 갱신: cycle 140 (2026-05-19, KST).
