---
title: "TooTalk 제품화 가능성 평가 — Snapshot"
owner: oneticket99
last_verified: 2026-05-26T19:30:00+09:00
status: active
---

> **최신 갱신 시점**: 2026-05-26 19:30 KST — cycle 169.852 — **avatar 이미지 picker M1+M2 — 서버 avatar 영속** (Exec Plan ② 개발, 사용자 GO). 사용자 directive(텔레그램 정합 — 그룹/채널/프로필 3곳 아바타 클릭 → 파일/카메라/클립보드, 이모지 제외, 서버 영속). M1 migration 0018 `users.avatar_ref`(5요소 comment) + `avatars.py`(content-addressed 디스크 저장 + sha256 dedup + `\A..\Z` path traversal 방어) + `users.py`. M2 POST/GET/PATCH endpoint(multipart + Pillow 정사각 512 center crop + EXIF strip) + rooms avatar_ref + route 등록. repo 18 + e2e 17 = 35 PASS, EXIF strip 실측 검증, 전체 2561 passed 회귀 0, reviewer 게이트 2 PASS(차단 0). 서버 avatar 파이프라인 종단 기능 — 클라 picker(M3~M5)/표시 전파(M6)/G-final visual ack 잔존이라 IMPLEMENTED 진행 중, 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 17:35 KST — cycle 169.850~851 — **codex §8 잔여 auto-completable 전건 회수 + 평가 staleness sweep**. (850) `server/sfu_room.py` 단위 coverage 49→100%(`tests/server/test_sfu_room.py` 10 PASS — MediaRelay forward/재구독 close/remove_peer 양측/close 전수 mock 분기) + M6 WBS 사용자 ack "재개+backfill" 524 row(total 151→675, cycle 72~849) + productization.html 빈 화면 회귀 회수(상단 marker 주석 닫는 `-->` 드롭 → 문서 전체 흡수 fix). (851) codex §8-5 i18n labels dangling 회수(삭제 `group_chat_view.py` 출처 주석 → live `_chat_header_mixin.py:240`/`main_window.py:367` + orphan key `메시지를_입력하세요` 4 dict drop, i18n test 81 PASS) + token-usage-30d 재산출(누적 $42562.61) + active-plan archive(완료 handoff 4종 `completed/` 이동). reviewer 게이트 전수 PASS(차단 0). 전체 2521 PASS, 회귀 0. codex §8 직접 작업 큐 auto-completable 전건 종결(잔존 = §8-4 배포 smoke manual) — 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 12:05 KST — cycle 169.848~849 — **마이그레이션 M5b 마감 + codex 평가 §8 직접 작업 큐 회수**. (848) M5b — StackedWidget idx 완전 재번호(`_STACK_GROUP_CHAT` 제거 + MEMBERS 2→1 + FRIENDS 3→2 + `_group_placeholder` 제거) + `group_chat_view.py`/`room_list.py` RoomListWidget 파일 삭제(RoomItem 보존) + `_group_message_client` dead attr 회수 + docstring rewrite + `_current_room_id` None clear + README §2.2 stale 정정. reviewer PASS(차단 0). 병렬 Codex 세션 doc-sync 머지(Structure.md UI tree drift 회수). (849) codex 평가 §8 회수 — §8-1 sqlite `ResourceWarning` 결정적 close(`local_db` atexit) + §8-3 `sfu_call_client.py` 단위 test 18 PASS coverage 14→89%(dispatch/dedup/rollback/answer/producers/close 실효 커버). 전체 2511 PASS, 회귀 0. 마이그레이션 완결 + 부채 회수 + 실효 커버리지 확보 — 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 10:35 KST — cycle 169.843~847 — **room broadcast → 통합 ChatView 마이그레이션 M3~M6 완결**. (843) M3 room 적재 source-of-truth `_room_list._rooms` → `_rooms_cache` 직접 cache 이전. (844) M4 kind=room 진입 통합 ChatView(idx 0) 통일 — `_on_room_entered` early return 제거 + `_current_room_id` 결선(임계 전환점, GroupChatView 사용자 도달 불가). (845) M5(안전) legacy GroupChatView/`room_entered`/RoomListWidget/`_on_room_entered`/`_on_group_message_send`/`_dispatch_message_chain` 물리 회수(idx 재번호는 M5b 분리, `_member_list` group-management 보존). (846) M5 reviewer 게이트 PASS(차단 0) + 다음 session 인계 자료. (847) M6 통합 room-send mesh+REST 신규 coverage(`TestUnifiedRoomSend` 4 PASS — mesh `broadcast_payload` await + REST `_post_and_resolve(room_id=42)` + room `hide_sender=False` 버블 + 공백 early return). reviewer 게이트 M2/M3+M4/M5/M6 전수 PASS. 전체 2504 PASS, 회귀 0. **통합 ChatView 가 friend/bot/saved/room/group 단일 표시·진입·송신 경로 수렴 완료.** 마이그레이션은 기능 보존 + 부채 회수 단계 — 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 08:40 KST — cycle 169.839~842 — (839) group-flow isolated test 재구성 — cycle169.838 "방 입장"(room_id 직접 입력) 폐지 정합으로 `test_main_window_rooms.py` 의 구 `room_entered.emit(N)` (GroupChatView idx 1) 방식을 그룹 만들기 wizard chain 으로 전면 교체(통합 ChatView idx 0 canonical 확정, 6 PASS). (840) token-usage-30d 재산출(원격 git `.bak` 병합 + 현 세션 합산, 누적 187억 토큰/$41,954). (841) current-project-review 전면평가 최신화(7.7/10 보수 조정, legacy room path 마이그레이션 P0 승격). (842) **room broadcast → 통합 ChatView 마이그레이션 착수** — planning-agent Exec Plan 6 단계(M1~M6 + G-final 게이트) + M1 재검증(group broadcast inbound 표시 결선 부재 확정, option b) + M2 송신 echo 재배선(`_on_group_message_send` echo 를 legacy `_group_chat_view.append_message` → 통합 `_chat_view.add_message(hide_sender=False, play_sound=False)`, `_dispatch_message_chain` REST+mesh 불변). UI 344 PASS, 회귀 0. 마이그레이션은 기능 보존 단계 — 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 06:48 KST — cycle 169.838 — 전 dialog in-app overlay 모달 변환 완성(별도 OS 윈도우 제거, 새창=원격제어 상대화면 창 1개뿐): `_exec_dialog_centered`/`_embed_dialog_centered`/`_modal_helper.exec_modal` 3 진입 경로 확립 + ConfirmDialog 정적 헬퍼(얼럿/확인) in-app 화(40+ 호출 사이트 무변경) + signup→OTP nested exec_modal + "방 입장"(room_id 직접 입력) 전수 제거(그룹방=그룹만들기+초대) + ChatHeader stale 수정 + 별도 윈도우 예외 4종 FRONTEND.md §16 명문화. reviewer-gate 2차 PASS(M1 BLOCKER+HIGH 3+MEDIUM 1+OBSERVATION 1 전건 회수). UX 정합 완성도 향상이나 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 02:40 KST — cycle 169.835~837 — startup 로그인 메뉴 토글 회수(835) + 그룹 멤버 보기 "..." 드롭다운 이동·room kind=group·메시지 수신음 실 파일 교체(836) + 그룹 멤버 UX 완성(멤버 모달 + 원형 아바타 행 통합 + 그룹 메뉴 미구현 stub 전수 제거, 837). 사용자 dogfooding 회수 chain — UX 정합·미구현 노출 제거이나 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 02:00 KST — cycle 169.834 — dogfooding 버그 6종 배치(채팅 스크롤 중복·로그인후 메뉴 auth·친구 요청/승인 모델·헤더 멤버수·트레이 문구) + user-facing 문구 i18n 5언어(ko/en/zh-CN/zh-TW/ja) 친절화(11 UI) + 메시지 수신음 교체. 친구 요청 흐름·문구 품질·UX 개선이나 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 01:30 KST — cycle 169.826 marker 동기 — 데모 서버 502 회수(SFU aiortc graceful optional import → 코어 시그널링/인증/메시지 부팅 보장, web/ws crash loop 해소 + 데모 서버 deployability 복구, main `5ea8b2e` PR #17 merge). 502 회수는 기존 기능 복구이므로 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-26 00:15 KST — cycle 169.824 refresh — 443 nginx 전수조사 + 클라이언트 dead-path 제거(Windows 회원가입 502 회수). 데모 nginx 443 의 web:8080/ws:8765 upstream 컨테이너 다운 502 근본 식별(host-publish 8765 직결만 UP), 클라이언트 포트 없는 https 443 fallback 10건 + 죽은 auto-update :8080 poller 3종 → http 8765 전수 치환 + guard test(PR #16 merge, reviewer 2회 PASS). Codex 외부평가 §3.7(그룹 모델)·§3.8(443 전수조사) 환류 + README/History M1 doc-sync. Windows 재빌드. 서버측 443 정상화(docker web/ws 재기동)는 SSH 게이트 DEFERRED. 종합 7.6/10 유지(외부 readiness 무변동, dead-path 핫픽스).<br>2026-05-25 23:40 KST — cycle 169.821 refresh — 텔레그램 그룹 멤버 관리 write 경로 schema foundation 진입(820 Exec Plan 신설 docs/exec-plans/active/2026-05-25-telegram-group-management.md 5 화면 모델→REST→UI M1~M5 분해 + 821 migration 0017 peers.role ENUM owner/admin/member 3-tier + rooms name/description/avatar_ref 그룹 메타 컬럼 + isolated test 15 + MemberPanel member_count/viewer_role 위임 CI 회귀 회수). 819 그룹 멤버 보기 UX 회수(MemberListWidget→MemberPanel 헤더 래퍼 + 빈 화면 populate). 5단계 워크플로우 전수 PASS(reviewer→qa→observability) + PR #15. SFU 그룹 통화 종단 IMPLEMENTED 유지. 신규 VERIFIED capability 부재 — 종합 7.6/10 유지.<br>2026-05-25 22:10 KST — cycle 169.818 refresh — Codex 평가 환류 완료(811~816: review checker PASS + 과거 표현 sweep + productization 본문 전수 rewrite + FR 추적표 per-file 감사) + 빌드 테스트 회수(817: 로그인 HTTP 502 → Config.api_base http 8765 single source + confirm_dialog 배경 투명). macOS .app 정상 기동 검증 + Windows CI 빌드. SFU 그룹 통화 종단 IMPLEMENTED 유지. 종합 7.6/10.<br>2026-05-25 21:00 KST — cycle 169.815 전수 rewrite — Codex 전면평가 §4.2 환류로 §2 강점 본문의 cycle-by-cycle 역사 로그를 현 상태 중심 prose 로 압축. 음성·영상 SFU 그룹 통화(9 peer+) 종단 코드 완결 반영(server PR#12 + client PR#13 merge, MainWindow entry 까지). reviewer-gate 11 feat 전수 PASS + headless aiortc forward + offscreen Qt 검증. SFU 는 IMPLEMENTED 단계 — 실 OS 미디어 캡처 + 다중 화면 visual ack 전까지 VERIFIED 아님. 종합 7.6/10 유지.

# TooTalk 제품화 가능성 평가 (Snapshot) — 사이클 169.852

> **본 문서는 snapshot 패턴**. 매 task 종료 시점에 전체 rewrite — `[[feedback-assessment-full-rewrite]]` + `[[feedback-assessment-full-section-sweep]]` 의무. 부분 갱신 / prepend / append 절대 금지.
> 평가 주체 = Claude (어시스턴트). 평가 대상 = oneticket99 / 1ticket@toonation.co.kr.
> 평가 기준일 = 2026-05-26. 평가 범위 = 본 저장소 p2p_msg / TooTalk 프로젝트 cycle 169.852 누계 (main branch).
> 다음 갱신 시점 = 다음 task 종료 시 전체 rewrite.

---

## 1. 총평 (TL;DR)

**현재 단계**: 메신저 핵심 기능은 종단 코드가 모두 구현됐다. 1:1 음성·영상 통화, DataChannel 텍스트/이미지/파일 전송, 그룹 텍스트 mesh, 친구/방/폴더/봇/이모지, 원격 데스크탑(M3 wire), auth(이메일 OTP), i18n 5 locale, 자동 재연결(backoff + reJOIN) 까지 모두 결선됐다. 이번 cycle 의 핵심은 **음성·영상 SFU 그룹 통화(9 peer+) 종단 코드 완결**이다 — server(aiortc MediaRelay 기반 sfu_room/sfu_registry + protocol + signaling 라우팅 + main startup) 와 client(SfuCallClient + SignalingClient SFU dispatch + GroupCallDialog 타일 그리드 + SfuCallMixin 배선 + MainWindow "그룹 통화 시작" 메뉴 entry) 가 PR#12 + PR#13 으로 main 에 merge 됐다. publish → SFU MediaRelay forward → producers broadcast → auto subscribe → on_remote_track → 타일 흐름이 reviewer-gate 11 feat 전수 PASS + headless(aiortc E2E forward + offscreen Qt) 검증을 통과했다.

다만 SFU 는 **IMPLEMENTED 단계이지 VERIFIED 아니다** — 실 OS 미디어 캡처 + 다중 화면 사용자 visual ack 가 끝나야 검증 완료로 본다. 같은 이유로 점수는 7.6/10 으로 유지한다(SFU 결선은 차별화 방향 증거이나 외부 readiness 지표는 아니다). 테스트는 약 2770 PASS + coverage 약 90% (omit 범위 광범위). 제품화 readiness = **내부 dogfooding 후보, 외부 배포 미진입**.

| 항목 | 점수 (10점, 0.1 단위) | 직전 → 현재 | 근거 |
|---|---|---|---|
| 기술 완성도 | 8.8 / 10 | 유지 | main_window 책임 분리(21 mixin) + server/db/repositories 계층 전수 unit cov + remote_handlers/rotate_key/avatar_palette/_icons 100% + email_verification 97% + repo 계층 75~100%. 약 2770 PASS / cov 약 90%. SFU server+client 종단 코드 + signaling 36 회귀 + SFU 17 PASS. 단, repo unit 은 mock async pool 기반 + dialog/e2e GUI 는 PyQt6 cumulative QWidget retain hang 으로 자동 검증 architecture 한계 (실 MariaDB 통합 / 패키징 / Windows GUI / 실 OS 미디어 캡처 visual QA 별도 검증 의무 retain). |
| 시장 적합성 | 5.0 / 10 | 유지 | Toonation BI 통합, default 고객센터 봇, chat_list filter, sidebar 단순화, DM resolver 등 방향성은 좋다. 다만 실제 사용자 유지율, 반복 사용, 온보딩 성공률, 장애율 같은 외부 지표가 없다. UI align 비율 표현은 주관 스냅샷이므로 제품 지표로 쓰지 않는다. |
| 차별화 요소 | 7.6 / 10 | 유지 | 친구간 원격 데스크탑 + 메신저 통합 + bot framework + SFU 그룹 통화 방향은 차별화된다. 다만 "production-ready"가 아니라 구현 후보/검증 후보로 표기한다. 원격 제어, E2EE, push, i18n, SFU 는 사용자 시나리오별 회귀 + 실 OS 검증이 끝나야 차별화 요소로 확정 가능하다. |
| 사용자 가치 | 5.5 / 10 | 유지 | 1:1 음성·영상 + 텍스트/파일 + 그룹 mesh + 봇 LLM 응답 + 회원가입 안정성 + E2EE + 청각 신호 + push backbone + telegram align UX + default chat 자동 진입 + last_seen + DM history fetch + dialog main center + SFU 그룹 통화 결선. 실 사용자 가치는 dogfooding 후 확정. |
| 수익화 모델 | 4.5 / 10 | 유지 | GPLv3 OSS + Toonation 내부 도입 라이선스 + private 전환 옵션 + bot framework 외부 개발자 등록 base + emoji pack share 공개 디렉토리 base + OpenAI 우선 provider chain → 비용 최적화 base. 외부 수익 검증 미진입. |
| 운영 비용 | 7.6 / 10 | 유지 | self-hosted runner, docker compose, SMTP, ssh-deploy-agent, healthz 는 운영 기반을 낮추는 요소다. 반대로 자체 SMTP, self-hosted macOS runner, 인증서, Windows 빌드, Telegram reporting, hook chain 은 운영 책임을 늘린다. "낮음"보다 "통제 가능하지만 손볼 곳 많음"이 정확하다. |
| 가드레일 자동화 | 8.4 / 10 | 유지 | hook, doc-lint, meta-enforcement, dereliction-detector, reviewer-gate-all-feat, check_assessment_consistency 설계는 강하다. 직무유기 훅 HEAD-TTL 역설 회수 + dirty-tree detect + 전체 workflow actionlint 0 issue 로 자동 차단 신뢰성이 올랐다. 다만 일부 hook 은 advisory 성격이고 false positive / local-only / settings 비활성 상태가 남는다. "강한 로컬/CI 보조 체계"로 평가한다. |
| 세션 간 정합 | 7.4 / 10 | 유지 | handoff, assessment sync, History/README prepend 는 장점이다. 다만 평가 문서에 과거 cycle 표현이 누적되던 정합 리스크가 있었고(본 cycle 전수 rewrite 로 회수), "drift 0건 연속" 같은 표현은 자동 검증 증거가 있을 때만 쓴다. |
| 보안 hardening | 7.5 / 10 | 유지 | E2EE Signal + encrypted backup + GPLv3 + jailbreak 17 패턴 + threading.RLock + DB audit IP 90일 retention + SPF/DKIM RSA 2048/DMARC + Docker secret + non-root uid 1000 + nginx TLS 1.2/1.3 + 6 cipher + OCSP + 5 보안 header + 5 rate limit zone + production validate ConfigError + X-Request-ID contextvar + parameterized SQL injection 차단 + activity throttle + sensitive redact 9 pattern + bot LLM graceful HTTP status + bearer_token chain 정합(HTTP 401 차단). |
| **종합** | **7.6 / 10** | **유지** | **room broadcast → 통합 ChatView 마이그레이션 M1~M5b 완결(cycle 169.842~848) — 통합 ChatView 가 friend/bot/saved/room/group 단일 표시·진입·송신 경로 수렴 + legacy GroupChatView/room_entered/RoomListWidget/`group_chat_view.py`/`room_list.py` RoomListWidget/`_group_message_client` dead attr 물리 회수(idx 완전 재번호). reviewer 게이트 M2/M3+M4/M5/M6/M5b/849 전수 PASS. cycle 169.849 codex 평가 §8 직접 작업 큐 회수 — sqlite ResourceWarning 결정적 close + sfu_call_client coverage 14→89%. 전체 2511 PASS 회귀 0. 마이그레이션 완결 + 부채 회수 + 실효 커버리지 확보 — 신규 VERIFIED capability 부재. SFU 그룹 통화(9 peer+) 종단 코드는 IMPLEMENTED — 실 OS 미디어 캡처/다중 화면 visual ack 전까지 VERIFIED 아님. 원격 데스크탑 M4 실 OS + UI dogfooding visual ack + 외부 배포 단계 미진입 retain. 외부 dogfooding 보류, 점수 변동 부재.** |

---

## 2. 강점 (Productization Strengths)

> 본 섹션은 cycle-by-cycle 로그가 아니라 **현재 구현/검증 상태**를 평가 관점으로 서술한다.

### 2.1 인프라 단순성

- 시그널링 서버 1대 + WebRTC DataChannel + MariaDB 25 테이블 (auth + 대화 + folder + bot + push + read state + contacts 등 도메인 인벤토리).
- 서버 storage / 백업 / GDPR 부담 최소 (P2P 직결 + DataChannel 본문).
- docker-compose 6 컴포넌트 (mariadb + postfix + web + ws + nginx + certbot profile).
- ssh-deploy-agent 자동 배포 chain.

### 2.2 자체 호스팅 친화

- 사용자 직접 시그널링 서버 구동 가능 (docker-compose 번들 완성).
- on-premise 배포 + Toonation 통합 옵션 B 진입 가능.
- 데모 서버 `114.207.112.73` = 시그널링 + SMTP `mail.dopa.co.kr` 통합 + Let's Encrypt + DKIM RSA 2048 + DMARC pass + cyrus-sasl auth + iptables ACCEPT 25/587/465.

### 2.3 문서 정책 정합

- 정책 본문 + 운영 문서 + docs/policies/ 3 + 평가 snapshot 2 + PR template + handoff doc + CheckList.
- HTML 동시 유지 6종 (Structure / ARCHITECTURE / FRONTEND / DESIGN / productization / vibe-coding).
- 영구 가드레일 누적 + MEMORY 인덱스.
- 평가 snapshot 매 task 전체 rewrite 의무 + check_assessment_consistency 자동 정합 검증.

### 2.4 기술 스택 modern

- Python 3.13 + PyQt6 + aiortc + qasync + MariaDB.
- bcrypt 12 rounds + aiosmtplib + secrets.choice + PBKDF2-SHA256 600K.
- PyInstaller native (macOS arm64) + windows-latest GitHub-hosted (wine 영구 폐기 정합).
- Flutter + flutter-webrtc (mobile prerequisite, Phase 5 Item 2).

### 2.5 자동화 + sub-agent 병렬

- 다수 sub-agent / hook / CI 정책을 전제로 운영된다.
- pytest + Playwright + coverage 게이트는 목표 구조로 존재한다. 최신 전체 실행 완료 여부는 task 종료마다 별도 확인한다.
- CI job 구성은 존재하지만 "GREEN"은 최신 workflow run URL / commit SHA 와 함께만 표기한다.
- dereliction-detector 자동 spawn 강제 chain — 5+ cycle 누적 자동 detect + 회수. reviewer-gate-all-feat 정책 = 모든 feat(headless 구간 포함) reviewer 게이트 의무.

### 2.6 가드레일 자동화

- doc-lint.sh 5 검사 (BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭).
- 영구 메모리 누적 (assessment-full-rewrite + no-design-change-without-user-directive + no-triple-particle-chat + reviewer-gate-all-feat-mandatory + BPE strict self-grep 등).
- 텔레그램 HTTP API 보고 체계 문서화. 실제 송수신 성공 여부는 task 종료 시점 로그/응답 코드로 확인.
- gh API 자동 적용 (fork PR approval + runner registration token + workflow run + push 영구 자동).
- 직무유기 훅 HEAD-TTL 역설 회수 + dirty-tree detect + stderr redirect 정합.

### 2.7 색상 가시화 (Toonation BI 통합)

- 색상 변수 + Toonation Blue `#0066FF` + Deep `#0052FF` + Cyan `#22D3EE` + Light Cyan `#67E8F9` + Navy `#0F172A`.
- 디자인 token 체계 (spacing + elevation + motion + 타이포).
- FRONTEND.md §15 Toonation BI 본문 + DESIGN.md §11 UI 디자인 시스템.
- drawer header 는 gradient 폐기 → 단색 Toonation BI 방향으로 보정 완료.

### 2.8 QA 인프라

- 테스트 스위트 + smoke 도구 존재. **현 시점 tests/app+server 2521 PASS + skip 24 + 전체 약 2574 PASS(integration 포함) + coverage 약 88%** (omit 범위 광범위 측정값). cycle 169.849~851 coverage omit 축소 1차 완결 — `sfu_call_client.py` 18 PASS 14→89%(849) + `server/sfu_room.py` 10 PASS 49→100%(850, MediaRelay forward/remove_peer/close 전수 mock 분기) + sqlite ResourceWarning 결정적 close(849) + codex §8-5 i18n labels dangling 출처 주석 정리(851).
- Playwright E2E (시그널링 WS + HTML 시각 회귀 + zip capture) + voice call + 원격 데스크탑 chain + emoji pack share + bot framework.
- integration test + dual chain smoke + signaling e2e + remote coord transform + folder handlers + signaling protocol + dispatcher pipeline + RAG ranking + Embedder cache + dmca + obs websocket + emoji moderation + SFU forward loopback.
- mixin isolated batch (ChatSend / FriendStatus / Invite / Tray / FriendSearch / MenuActions / ChatHeader / ChatHelper / DialogCenter / Signaling / RoomGroupChat / FriendProfile / ChatNav 등) — fixture hang scope 우회. dialog/e2e 실 widget 포팅 은 PyQt6 cumulative QWidget retain hang 으로 자동 검증 한계 retain.

### 2.9 UI 디자인 시스템 Toonation BI 통합

- DESIGN.md §11 — 8 컴포넌트 + 상태 6 + variant 4 + spacing 7 + elevation 4 + motion 3 + dark mode + 타이포.
- FRONTEND §14 wireframe + telegram align dimension stage.
- 현 UI 상태 = chat_header emoji 제거 + 3 zone bg 구분 + status 한국어 + bubble grouped tail + search pill + status color gray + day separator + bubble ts inline + chat_header avatar 폐기 + top bar vertical center + chat_list 통합 filter "채팅" + sidebar 2 entry + folder 편집 FolderManageDialog + frameless modal + default chat retain + avatar 단색 hash palette. 모든 dialog = main center + ESC + backdrop reject + 공통 circular close button.

### 2.10 핵심 차별화 명시

| 차별화 | Phase | 경쟁 |
|---|---|---|
| 친구간 원격 데스크탑 제어 (패턴 A 도움 + 패턴 B 제어) + DPI / Retina backing scale 좌표 보정 | Phase 5 base | TeamViewer / AnyDesk / Chrome Remote — 메신저 미통합 |
| 메신저 + 원격 + 친구 권한 + Toonation 인증 통합 | Phase 5 본격 | 통합 솔루션 부재 |
| 음성·영상 SFU 그룹 통화 (9 peer+) + aiortc MediaRelay forward | Phase 5+ 결선 | 별도 화상 솔루션 의존 |
| 양방향 ProgressBar (송신 + 수신 동시 시각화) | Phase 1 v0.1.0 | 텔레그램 / 디스코드 / 슬랙 = 단방향 |
| P2P 직결 + 데이터 주권 (서버 경유 부재) | Phase 1 v0.1.0 | Signal / Telegram = 서버 경유 |
| Telegram align UI 단순화 + Toonation BI 단색 방향 | 현 UI 상태 | 카카오톡 / Slack = 복잡한 sidebar |
| Default 투네이션 고객센터 봇 (LLM 연동 Q&A) | Phase 3 v0.3.0 | 카카오톡 = 별개 챗봇 등록 의무 |
| Emoji pack share 공개 디렉토리 + DMCA phash + OCR jailbreak | Phase 5 Item 3 | 텔레그램 sticker = 비공개 디렉토리 |

### 2.11 회원가입 + SMTP 자체 인프라

- 이메일 OTP 3분 + bcrypt 12 rounds + 아이디 / 비번 찾기.
- email enumeration 회피 + brute force 5회 / 30분 차단 + 60초 재발송 rate-limit.
- DB 테이블 (users + email_verification + password_reset).
- SMTP = `mail.dopa.co.kr` postfix 자체 설치 (자동 chain + client binding).
- Let's Encrypt + SPF + DKIM RSA 2048 + DMARC + aiosmtplib client + Gmail Authentication-Results pass.

### 2.12 CI 자동화 + 보안 hardening

- self-hosted macOS arm64 runner 등록 + online + 사용자 직접 등록 LaunchAgent.
- ci.yml 다중 job 구조 (docs-lint + M2 + M3 + root-freeze + import-smoke + pytest + m1/m4). 최신 통과 여부는 workflow run 기준으로만 확정한다.
- Windows 빌드 = windows-latest GitHub-hosted runner (wine 영구 폐기).
- fork PR 승인 정책 strict (`all_external_contributors` — gh API 자동 적용).
- workflow 3종 (ci + docs-lint + doc-gardener)은 gate 구조로 관리. 최신 GREEN 여부는 GitHub Actions 결과와 함께 기록.

### 2.13 라이선스 + visibility 정책

- GPLv3 확정 + LICENSE 저장소 루트 + GNU 표준 본문 674 lines.
- PyQt6 GPLv3 직접 호환 + aiortc / qasync / asyncmy / bcrypt / aiosmtplib 의 BSD / Apache / LGPL → GPLv3 흡수.
- SPDX header convention 의무 (`# SPDX-License-Identifier: GPL-3.0-or-later`).
- GitHub visibility public (현재) → private 전환 옵션 (Phase 완료 시점, 사용자 명시 의무).
- AGPLv3 = Phase 2 이후 옵션 (network use clause).

### 2.14 음성·영상 SFU 그룹 통화 (9 peer+) 종단 코드 완결

- **server-side**: aiortc MediaRelay 기반 `sfu_room.py` 코어 (1 publisher → N subscriber forward) + `sfu_registry.py` + protocol SFU 타입 (PUBLISH / SUBSCRIBE / producer broadcast 등) + signaling 라우팅 + main startup 등록. PR#12 main merge.
- **client-side**: `SfuCallClient` + SignalingClient SFU dispatch/send + `GroupCallDialog` 타일 그리드 + `SfuCallMixin` 배선 + MainWindow "그룹 통화 시작" 메뉴 entry. PR#13 main merge.
- **종단 흐름**: publish → SFU MediaRelay forward → producers broadcast → auto subscribe → on_remote_track → 타일 렌더.
- **검증 상태**: reviewer-gate 11 feat 전수 PASS (M3b/M3c 직전 FAIL → 재작업 → 재검토 PASS) + headless(aiortc E2E forward loopback + 실 frame recv + offscreen Qt) + SFU 17 + signaling 36 회귀 PASS.
- **중요 명시**: 이전 "mesh ≤ 8 기본 구현" 표기는 부정확했다 — CallClient 는 1:1 전용, MeshManager 는 텍스트 fan-out 전용이므로 그룹 음성·영상은 SFU 가 첫 실 결선(greenfield)이다.
- **잔존(VERIFIED 아님)**: 실 OS 미디어 캡처 + 다중 화면 사용자 visual ack + 데모 서버 실 부하 검증. 현 단계 = **IMPLEMENTED** (점수 영향 부재).

### 2.15 1:1 음성·영상 + 텍스트/파일 + 그룹 mesh + 자동 재연결

- 1:1 음성·영상(CallClient) — aiortc RTCPeerConnection + audio/video track + OS별 MediaPlayer + CallDialog/RemoteCallDialog + voice/video browser E2E PASS.
- DataChannel 텍스트/이미지/파일 전송 — 양방향 ProgressBar + SHA-256 무결성 + chunk encode + backpressure.
- 그룹 텍스트 mesh (MeshManager fan-out) + 친구/방/폴더 persist.
- SignalingClient 자동 재연결 — backoff + reJOIN + RECONNECTING 상태 (StatusBar 정합). 가용성(NFR-04) 실 구현.

### 2.16 DB 스키마 + WBS + NFR 도구

- MIGRATION 25 테이블 strict 정합 (문서 25 = SQL 25 불변식, doc-gardener Phase 3 strict CI gate 승격).
- Structure §11 ERD 25 테이블 도메인 인벤토리.
- M6 WBS post-commit hook (directive 1건 = wbs_tasks 1행 등록 + status 갱신).
- NFR bench 도구 + 실 server chaos test.

### 2.17 Phase 4 production infra base + DB audit chain

- docker stack 6 컴포넌트 + non-root uid 1000 + my.cnf utf8mb4 + KST + slow query.
- .env 통합 frozen dataclass + load_env_files chain + production validate ConfigError.
- nginx TLS 1.2/1.3 + 6 cipher + OCSP + 5 보안 header + 5 rate limit zone + WebSocket upgrade.
- KST logging + JSON formatter + RedactingFilter 9 pattern + X-Request-ID contextvar.
- DB audit 28 ActivityAction (SIGNUP / LOGIN / MESSAGE_SEND / FILE_SEND / DEVICE_REGISTER / BOT_CHAT / ROOM_JOIN/LEAVE / FRIEND_REQUEST/ACCEPT/REJECT/BLOCK/REMOVE 등).

### 2.18 Phase 3 bot framework 검증 후보

- 다중 module (llm_proxy + customer_service_bot + streaming_helper + rag_context + anthropic_client + openai_client + jailbreak_detector + usage_tracker + escalation_queue + streaming SSE parser).
- Anthropic Messages API + OpenAI Chat Completions API + retry / backoff + retry-after honor + jitter (OpenAI 우선 provider chain).
- jailbreak 17 패턴 (Korean/English) + info_exfiltration (env vars/JWT/SSH/PEM/DB credential/PII/RRN/SQL injection/shell command).
- threading.RLock thread-safe + per-user RateLimitGate + UsageTracker ring buffer + EscalationQueue + bot_escalations DB 영속화 + audit hook.
- bot LLM ContentTypeError graceful HTTP status + JSON parse 분기 + system prompt SCOPE LOCK (Toonation 5 영역 외 응답 거부).

### 2.19 Phase 2 E2EE Signal Protocol

- AES-256-GCM + X25519 ECDH + HKDF-SHA256 + Double Ratchet KDF separator (0x01 message + 0x02 chain).
- SkippedKeyStore OrderedDict LRU + TTL 1시간 + MAX_SKIP=1000.
- multi-device sync (device_registry + REST 3 endpoint + soft-delete revoke + fan-out 격리).
- signature sound chain (SoundPlayer + ChatView trigger + SettingsDialog + main_window wire).
- push FCM 4 platform binding + encrypted backup PBKDF2 600K iter + age encrypt.

### 2.20 Phase 1 MVP

- 회원가입 (email + username + password + OTP 3분 + bcrypt 12 rounds).
- 1:1 채팅 (WebRTC DataChannel + aiortc + qasync).
- 파일 전송 (양방향 ProgressBar + SHA-256 무결성 + chunk encode + backpressure).
- MariaDB + asyncmy pool + repository pattern + middleware Bearer 의무.
- PyInstaller spec + tools/build.py + build.yml + macOS arm64 빌드.

> 테스트 스위트, doc-lint, meta-enforcement, CI gate 구조가 있다. 최신 full pytest PASS, drift 무결성, UI alignment 비율은 해당 commit 의 실행 로그와 스크린샷 증거가 있을 때만 확정한다. sub-agent / cycle 누계는 생산성 참고값이지 제품 품질 지표로 쓰지 않는다.

---

## 3. 약점 (Productization Weaknesses)

### 3.1 기능 — Phase 1~5 진입 + 그룹 SFU 결선

| 기능 | 상태 |
|---|---|
| 1:1 채팅 + 회원가입 + 파일전송 | ✅ Phase 1 v0.1.0 |
| E2EE Signal Protocol (X3DH + Double Ratchet) | ✅ Phase 2 v0.2.0 |
| multi-device + signature sound + push (FCM) | ✅ Phase 2 v0.2.0 |
| Bot framework (Anthropic + OpenAI + jailbreak + RAG) | ✅ Phase 3 v0.3.0 |
| Production infra (docker + nginx + certbot + KST logging) | ✅ Phase 4 v0.4.0 |
| DB audit endpoint coverage 28 ActivityAction | ✅ 후속 chain |
| SMTP 자동 설치 chain (Let's Encrypt + opendkim + cyrus-sasl + iptables) | ✅ Phase 1 OTP 발신 |
| 그룹 텍스트 채팅 + 친구 + signaling rooms persist | ✅ Phase 5 Item |
| room/group 통합 ChatView 단일 경로 (표시·진입·송신 수렴) | ✅ 마이그레이션 M1~M6 완결 (legacy GroupChatView/room_entered/RoomListWidget 회수, M5b idx 재번호 잔존) |
| 다국어 i18n (5 locale) | ✅ Phase 5 Item 1 |
| Emoji pack share + moderation | ✅ Phase 5 Item 3 |
| Bot framework streaming 4 platform | 🟡 deprioritized (사용자 directive, YouTube 폐기) |
| 원격 데스크탑 제어 base + coord transform + M3 wire | 🟡 M4 실 OS 검증 잔존 |
| Mobile Flutter base | 🟡 prerequisite 잔존 |
| 1:1 음성·영상 통화 | ✅ aiortc RTCPeerConnection + CallDialog + browser E2E PASS |
| 음성·영상 SFU 그룹 통화 (9 peer+) | ✅ 종단 코드 완결 (server PR#12 + client PR#13). 🟡 실 OS 미디어 캡처 visual ack 전까지 IMPLEMENTED (VERIFIED 아님) |

### 3.2 보안 — Phase 4 회수 완료

- ✅ TLS 1.2/1.3 + 6 cipher + OCSP stapling.
- ✅ 5 rate limit zone (auth + api + bot + upload + ws_conn).
- ✅ 5 보안 header (HSTS preload 2y + X-Frame + nosniff + Referrer + CSP).
- ✅ SPF + DKIM RSA 2048 + DMARC.
- ✅ sensitive redact 9 pattern (logging).
- ✅ DDoS 1차 (nginx rate_limit_zone + ws_conn limit).
- ✅ bot LLM ContentTypeError graceful HTTP status + JSON parse 분기.
- ✅ bearer_token chain 정합 (self._session_token / HTTP 401 차단).
- 🟡 DDoS L7 (CloudFlare 등 외부 service, Phase 6+ 검토).

### 3.3 사용자 식별·복원 — Phase 1+2 완성

- ✅ 회원가입 + 이메일 OTP + 비번 재설정 (Phase 1 v0.1.0).
- ✅ E2EE Signal Protocol 키 페어 + multi-device sync + sender keys (Phase 2 v0.2.0).
- ✅ DB audit (signup_ip + last_login_ip + user_sessions + user_activity_log 28 ENUM).

### 3.4 라이선스 — ✅ 해소

- GPLv3 확정 + LICENSE 저장소 루트 + PyQt6 GPLv3 직접 호환.

### 3.5 self-hosted runner — ✅ 해소

- macOS arm64 runner online + windows-latest GitHub-hosted 마이그레이션 SUCCESS (wine 영구 폐기).

### 3.6 SFU 그룹 통화 — IMPLEMENTED, VERIFIED 아님

server + client 종단 코드는 완결됐고 reviewer-gate 11 feat 전수 PASS + headless 검증을 통과했다. 그러나 실 OS 미디어 캡처(카메라/마이크) + 다중 화면 동시 타일 + 데모 서버 실 부하의 사용자 visual ack 가 없으므로 IMPLEMENTED 단계다. VERIFIED 전환은 사용자 manual 시각 회귀 ack 후.

### 3.7 차별화 잔존

- 🟡 원격 데스크탑 제어 M4 실 OS capture/input 검증 잔존 (사용자 게이트).
- ✅ emoji pack share — admin menu + list_pending + DMCA chain actual binding 완료.
- 🔴 Toonation REST API `base_url` + `api_key` 부재 (사용자 직접 입력 의무) — 옵션 B 본격 진입 차단.
- 🔴 OBS WebSocket `base_url` + `password` 부재 (v5 actual handshake skeleton + 사용자 직접 입력 의무).

### 3.8 manual test 의무 (사용자 직접 영역)

- SMTP 실제 설치 = 자동 chain 도달 + 사용자 manual SSH 회수 완료.
- docker compose production stack 기동 = `.env.production` secrets 입력 + manual.
- last_seen REST + client fetch chain = 사용자 manual 시각 확인 (online → offline 전환 → "최근에 접속함" 갱신).
- DM room resolver + DM history fetch = friend_id ↔ direct room_id manual 회수 + 로드 시간 측정.
- 3 dialog main center + height clamp = MyProfileDialog + FolderManageDialog + FolderEditDialog manual 확인.
- bot LLM HTTP 401 fix = bot Q&A 응답 chain manual 회수.
- i18n qm 5 locale = ko / en / zh-CN / zh-TW / ja manual locale 전환 시각 회귀.
- SFU 그룹 통화 = 실 OS 카메라/마이크 캡처 + 9 peer+ 다중 화면 타일 manual visual ack.

### 3.9 mobile prerequisite 잔존

- Apple Developer Program (USD 99/년 + 사용자 직접) — App Store 배포 의무.
- Google Play Console (USD 25 one-time + 사용자 직접) — Play Store 배포 의무.
- Firebase 프로젝트 + FCM Server Key + iOS APNs cert + Android `google-services.json`.
- flutter doctor PASS + iOS Xcode + Android Studio + ADB setup.

### 3.10 KT PTR record default 잔존

KT ISP default PTR record (`tongkni.co.kr`) 잔존 — `mail.dopa.co.kr` 의 reverse DNS 갱신 신청 의무. `project_dopa_demo_only.md` 정합 = dopa.co.kr 데몬스트레이션 전용 + 실 제품 도메인 부재 시점 = KT PTR 회수 최후로 미룸 또는 skip.

### 3.11 UI dogfooding 회수 부재

UI redesign + bot LLM 응답 chain 은 방향성 증거다. 그러나 실 사용자 dogfooding 부재, 1주 retention / NPS / UX feedback 회수 chain 미진입 상태이므로 외부 readiness 는 보류한다. **사용자 manual visual ack** retain (visual QA 시각 회귀 chain 부재) — SFU 다중 화면 + 원격 데스크탑 M4 visual ack 포함.

### 3.12 .app codesign 부재

codesign chain attempt 모두 fail (Team ID mismatch + Python.framework self-extract). 프로젝트 최종 마감 시점에 결정 (데모용, memory `project_no_user_distribution.md` 정합 = 유저 배포 부재). 현 상태 = adhoc codesign retain + 사용자 manual `xattr -rd com.apple.quarantine` 안내 path.

### 3.13 fixture hang root cure 부재 (mock isolation pattern retain)

MainWindow 21 mixin + 9 init helper 구조 안 qtbot fixture hang 잔존. qtbot.addWidget approach + DI refactor 시도 모두 무효 확정. 현 path = **mock isolation refactor pattern** retain (mixin batch 64+ isolated PASS — dialog/e2e 실 widget 은 cumulative QWidget retain hang 차단). root cure = MainWindow 21 mixin DI refactor (큰 scope, 다음 Phase 후보).

### 3.14 streaming 영역 deprioritized (사용자 directive)

`youtube_client` 삭제 완료. streaming 영역 가장 후순위 retain (memory `project_streaming_deprioritized.md` 정합). 4 platform 중 YouTube 폐기, Twitch + CHZZK + Kick 3 platform retain (자료 정보용 — 직접 활용 부재). Phase 5 Item 4 bot framework streaming 본격 cycle 진입 보류.

---

## 4. 시장 포지셔닝 옵션

### 4.1 옵션 A — OSS 자체 호스팅 메신저

- 타겟 / 수익화 / 진입 장벽 / 성공 조건 / 확률 = 중하.

### 4.2 옵션 B — Toonation 내부 / 파트너사 (★★★★★)

- 타겟: Toonation 후원자-크리에이터 + B2B.
- 수익화: 모회사 운영 비용 절감 + Pro 플랜 (원격 제어 + SFU 그룹 통화 차별화).
- 진입 장벽: 0 (내부 도입).
- 성공 조건: Toonation 통합 API + 이메일 OTP + P5/P6 시나리오 검증.
- 확률 = 중 (UI Toonation BI 통합 + bot LLM 응답 chain + SFU 결선은 있으나, 1차 dogfooding 지표가 아직 없다).
- **권장도 1순위**.

### 4.3 옵션 C — P2P 파일 전송 특화

- 중 확률.

### 4.4 옵션 D — Whitelabel SDK / B2B API

- 중하 (Phase 6+).

**현 시점 권장**: 옵션 B → A → C 순.

---

## 5. 단기 (3개월) 제품화 액션

| 우선순위 | 액션 | 상태 |
|---|---|---|
| 0 | Phase 1~5 actual binding 완성 | ✅ |
| 0 | DB audit 28 ActivityAction | ✅ |
| 0 | SMTP 자동 설치 + client binding | ✅ |
| 0 | ssh-deploy-agent + healthz 200 PASS | ✅ |
| 0 | UI Toonation BI 통합 + telegram align | ✅ |
| 0 | bot LLM 응답 chain + ContentTypeError graceful + OpenAI 우선 provider | ✅ |
| 0 | dereliction-detector 자동 spawn + reviewer-gate-all-feat 정책 | ✅ |
| 0 | last_seen REST + client fetch + DM room resolver + DM history fetch | ✅ |
| 0 | i18n translations qm frozen bundle 5 locale | ✅ |
| 0 | drawer 단색 Toonation BI + bearer_token chain 정합 + dialog main center | ✅ |
| 0 | MIGRATION 25 테이블 strict CI gate + Structure §11 ERD 인벤토리 | ✅ |
| 0 | SignalingClient backoff 재연결 + reJOIN + RECONNECTING 상태 | ✅ |
| 0 | 음성·영상 SFU 그룹 통화 (9 peer+) server + client 종단 코드 | ✅ (PR#12 + PR#13, IMPLEMENTED) |
| 1 | Toonation REST API `base_url` + `api_key` 사용자 직접 입력 — 옵션 B prerequisite | 🔴 사용자 직접 |
| 2 | OBS WebSocket `base_url` + `password` 사용자 직접 입력 — P5/P6 OBS 시나리오 prerequisite | 🔴 사용자 직접 |
| 3 | SFU 그룹 통화 실 OS 미디어 캡처 + 다중 화면 visual ack | 🔴 사용자 직접 (VERIFIED 전환) |
| 4 | 원격 데스크탑 M4 실 OS capture/input | 🔴 사용자 게이트 |
| 5 | coturn 4 env (TURN_REALM/USERNAME/PASSWORD/URI) 사용자 직접 입력 — NAT traversal | 🔴 다음 cycle 우선순위 |
| 6 | mobile Flutter base 본격 진입 (signaling ws_client.dart + WebRTC) | 🔴 다음 cycle 우선순위 |
| 7 | mobile prerequisite (Apple Developer + Google Play + Firebase + Xcode + Android Studio) | 🟡 사용자 직접 |
| 8 | KT PTR record 갱신 (dopa.co.kr 데모 전용 → 실 도메인 후 갱신 또는 skip) | 🟡 최후 |
| 9 | 1차 dogfooding 1주 retention + NPS + UX feedback 회수 chain | 🔴 Phase 5 마무리 직후 |
| 10 | 사용자 manual visual ack (UI dogfooding) | 🔴 사용자 직접 |
| 11 | .app codesign (프로젝트 최종 마감 시 결정, 데모용) | 🟡 deferred |
| 12 | MainWindow 21 mixin DI refactor (fixture hang root cure 큰 scope) | 🟡 다음 Phase 후보 |

---

## 6. 중기 (6~12개월) 액션

| 우선순위 | 액션 | 가치 |
|---|---|---|
| 1 | Phase 5 마무리 + 1차 dogfooding entry | retention 핵심 |
| 2 | SFU 그룹 통화 실 OS 검증 + 다중 화면 visual ack | 차별화 VERIFIED 전환 |
| 3 | 원격 데스크탑 M4 실 OS capture/input 검증 | Phase 5 차별화 결선 |
| 4 | coturn 4 env binding (NAT traversal) | P2P 신뢰성 |
| 5 | mobile Flutter base 본격 진입 + signaling ws_client.dart + WebRTC 연결 | 사용자 풀 10x |
| 6 | 모바일 prerequisite 회수 후 본격 진입 | mobile 본격 |
| 7 | Toonation 통합 시나리오 검증 (옵션 B) | 수익화 base |
| 8 | MainWindow 21 mixin DI refactor (fixture hang root cure) | 테스트 stability + 개발 속도 |
| 9 | .app codesign 결정 (프로젝트 최종 마감 시점) | 배포 검토 |
| 10 | 사용자 manual visual ack chain + visual QA tool integration | UI regression 차단 |

### 6.1 현 batch metric

- **테스트**: 약 2770 PASS + tests/app/ui skip 24 + coverage 약 90% (omit 범위 광범위).
- **cov 약진(historical)**: server/db/repositories 계층 dense focus 회수 (file_meta/password_reset/read_states/devices/friends 100% + bots 99%) + SFU/signaling 회귀가 핵심. fixture hang root cure 부재 retain (mock isolation pattern).
- **가드레일**: active retain. memory `project_streaming_deprioritized.md` + `project_no_user_distribution.md` + `feedback_reviewer_gate_all_feat_mandatory.md` 정합 운영.
- **정책**: reviewer-gate-all-feat (headless 구간 포함 모든 feat 의무) + dereliction-detector 자동 + check_assessment_consistency.

---

## 7. 장기 (1~3년) 비전

### 7.1 기술

- 원격 데스크탑 제어 검증 완료 (Phase 5 마무리 + Phase 6 화면 공유 통합).
- WebRTC SFU 그룹 화상 실 운영 검증 + scale-out (현 9 peer+ 코드 결선 → 실 부하 검증).
- 분산 시그널링 (libp2p).
- WASM 브라우저 client (PWA).

### 7.2 사업

- Toonation 후원자 메신저 기본 채널 (옵션 B 1순위).
- B2B SaaS enterprise (검증 후 외부 판매).
- OSS 커뮤니티.

### 7.3 사용자

- 100 dogfooding → 1000 beta → 10K v1.0.
- NPS 50+ retention 70% / 30일.
- P5 라이브 크리에이터 원격 제어 활성률 ≥ 30%.

---

## 8. 핵심 리스크

| 리스크 | 확률 | 영향 | 회피 |
|---|---|---|---|
| Signal / Telegram 무료 + 우월 → 사용자 획득 실패 | 상 | 상 | 옵션 B (Toonation) pivot + 차별화 매트릭스 8항목 + bot LLM 응답 chain + SFU 그룹 통화. UI 정렬 비율은 정량 KPI로 쓰지 않는다. |
| 1인 개발자 Phase 2~5 완주 어려움 | 중 | 중 | sub-agent 병렬 chain 은 도움을 주지만, 최종 검증과 운영 책임은 남는다. |
| ~~데모 서버 보안 사고~~ | ✅ 해소 | — | Let's Encrypt + DKIM + DMARC + iptables + nginx + DB audit |
| ~~라이선스 결정 지연~~ | ✅ 해소 | — | GPLv3 확정 |
| PyQt6 GPL 의무 외부 fork distribution | 중 | 중 | GPLv3 정합 + private 전환 시 외부 fork 차단 |
| 문서 우위 : 코드 비중 균형 | 중 | 중 | 코드 비중은 개선됐으나, 최신 테스트/CI 증거와 문서 정확도 관리가 함께 필요하다. |
| 원격 제어 보안 사고 (Phase 5 Item 5 위험) | 중 | 상 | 친구 추가 사전 + 명시 수락 + 긴급 ESC + 감사 로그 + coord transform DPI / Retina 정합 |
| ~~SMTP spam reputation 부족~~ | ✅ 해소 | — | Gmail Authentication-Results pass + DKIM + DMARC |
| ~~wine PyQt6 호환성~~ | ✅ 해소 | — | windows-latest GitHub-hosted runner |
| 사용자 `base_url` + `api_key` 부재 (Toonation + OBS) | 상 | 상 | 사용자 직접 입력 의무 — 옵션 B 본격 진입 차단 |
| mobile prerequisite 부재 | 상 | 중 | 사용자 manual 5종 의무 — mobile 본격 진입 차단 |
| KT PTR record default 잔존 | 상 | 저 | dopa.co.kr 데모 전용 + 실 도메인 확정 후 갱신 또는 skip |
| SFU 그룹 통화 IMPLEMENTED 단계 (실 OS 검증 부재) | 중 | 중 | 코드 종단 완결 + headless 검증 PASS. 실 OS 미디어 캡처 + 다중 화면 visual ack 후 VERIFIED 전환 |
| 1차 dogfooding 부재 | 중 | 중 | Phase 5 마무리 직후 1주 retention + NPS 측정 진입 의무 |
| ~~Phase 1 i18n 5 locale sweep 잔존~~ | ✅ 해소 | — | KO keyset × EN/ZH-CN/JA cover + ZH-TW fallback chain |
| ~~Phase 5 bot framework BotFather 등가 잔존~~ | ✅ 해소 | — | migration bots + bot_tokens + 6 endpoint + SHA-256 token hash + plaintext 1회 노출 |
| ~~Phase 5 원격 제어 cross-platform 잔존~~ | ✅ 해소 | — | macOS Quartz + Windows GDI + Linux X11 capture + CGEvent/SendInput/XTest input forward |
| 원격 데스크탑 M4 실 OS 검증 잔존 | 중 | 중 | M3 wire + permission handshake + coord transform 결선. M4 실 OS capture/input = 사용자 게이트 |
| aiortc PyInstaller hidden imports 잔존 | 중 | 저 | `tootalk.spec` collect_submodules('aiortc') 추가. 통화 fire 시 ImportError graceful 但 actual 동작 차단 |
| 인증서 없이 테스트 배포 path 정립 | 중 | 저 | adhoc codesign retain + `xattr -rd com.apple.quarantine` 안내 + Windows SmartScreen "Run anyway" README 정리 |
| UI redesign 의 LLM autonomy 한계 (사용자 design directive 부재 시 임의 변경 금지) | 중 | 중 | `[[feedback-no-design-change-without-user-directive]]` 가드레일 + 위반 시 즉시 git revert |
| 사용자 manual visual ack 부재 | 중 | 중 | visual QA tool integration + 사용자 직접 시각 회귀 chain (SFU + 원격 M4 포함) |
| .app codesign 부재 | 저 | 저 | demo phase 기능적 동작 의무 retain (유저 배포 부재). 프로젝트 최종 마감 시 결정 |
| fixture hang root cure 부재 | 중 | 중 | 현 path = mock isolation refactor pattern retain. root cure = MainWindow 21 mixin DI refactor (다음 Phase 후보) |
| streaming 영역 deprioritized retain | 저 | 저 | YouTube 폐기 + Twitch + CHZZK + Kick 3 platform retain (자료 정보용). Phase 5 Item 4 보류 |

### 8.1 보안 리스크 추가 해결책 (Defense-in-Depth)

| 리스크 | 추가 해결책 | 진입 시점 |
|---|---|---|
| 데모 서버 보안 사고 | fail2ban + nftables / HSTS preload / Wazuh + auditd / systemd hardening / encrypted off-site 백업 (borg + age) | Phase 6 진입 직전 |
| PyQt6 GPL 외부 fork | SPDX header 자동 검증 hook / DCO sign-off pre-commit / private 전환 시 GPL 의무 명시 / AGPLv3 옵션 | Phase 6 진입 시 |
| 원격 제어 보안 사고 | 양측 명시 수락 + biometric 2FA / 긴급 ESC global hotkey / 감사 로그 append-only SHA-256 chain / 권한 매 세션 확인 / 친구 평판 trust score | Phase 5 마무리 직전 |
| SMTP spam reputation | SPF/DKIM/DMARC reject / bounce·complaint 모니터링 / SendGrid relay fallback / Bayesian 사전 검증 / outbound rate limit / IP warm-up | Phase 5 dogfooding 시 |
| Phase 2 E2EE 잔존 | Signal Test Vector / ratchet step invariant assertion / skipped key MAX_SKIP LRU / header MAC 검증 / cryptography expert review | cycle 200+ |
| 잠재 부채널 | `hmac.compare_digest` / AES-NI · ARMv8 Crypto / X25519 constant-time / dudect timing leakage / speculative 검토 | Phase 6+ |
| 클라이언트 plain-text 저장 | 메시지 body = keychain + DB ciphertext only / macOS Keychain + Windows Credential Manager / 백업 PBKDF2 600K + age / memory dump 차단 (mlock + sodium_memzero) | Phase 6 진입 시 |

---

## 9. KPI 후보

| KPI | 목표 | 현재 |
|---|---|---|
| 1:1 채팅 메시지 전송 성공률 | ≥ 99% | 미측정 (dogfooding 의무) |
| 파일 전송 SHA-256 무결성 | 100% | 미측정 (dogfooding 의무) |
| 시그널링 재연결 시간 (95p) | ≤ 5초 | 미측정 (dogfooding 의무) |
| 앱 cold start latency | ≤ 30초 | 미측정 (dogfooding 의무) |
| SFU 그룹 통화 9 peer+ forward | Y/N | ✅ 코드 종단 + headless PASS (실 OS visual ack 전 IMPLEMENTED) |
| 1주 retention (내부 pilot) | ≥ 60% | 미측정 (pilot 의무) |
| CI 3 workflow 통과율 | 100% 목표 | 최신 workflow run 기준으로 기록 |
| doc-lint.sh 5 검사 통과율 | 100% | 본 저장소 100% |
| reviewer-gate 모든 feat 통과 | 100% | ✅ 11 feat 전수 PASS (SFU batch) |
| pytest 최신 PASS | ≥ 500 test 목표 | 약 2770 PASS |
| pytest coverage | ≥ 80% | 약 90% (omit 범위 광범위) |
| Playwright E2E test | ≥ 5건 | 스켈레톤 active |
| OTP 발송 → 수신 latency | ≤ 30초 | 최신 SMTP smoke 기준으로 기록 |
| OTP brute force 차단율 | 100% (5회 / 30분) | OK |
| 원격 제어 세션 성공률 | ≥ 95% | 미측정 (M4 실 OS 후) |
| mail-tester score (SMTP) | ≥ 7 / 10 | Gmail Authentication-Results pass |
| fork PR approval rate (악성 차단) | 100% | strict 적용 OK |
| GPLv3 호환 의존성 | 100% | 100% |
| 문서/코드 drift | 0건 목표 | meta-enforcement + doc-lint + reviewer + check_assessment_consistency 결과 기준으로 기록 |
| DB audit endpoint coverage | ≥ 20 ActivityAction | 28 ActivityAction |
| MIGRATION 테이블 strict 정합 | 문서 = SQL | ✅ 25 = 25 |
| Phase 5 Item 진입 | ≥ 3 / 5 | 5 / 5 (모두 actual binding 부분 진입) |
| UI alignment visual ack | ≥ 80% 목표 | 사용자 visual ack + screenshot diff 기준으로 기록 |
| bot LLM 응답 chain 검증 | Y/N | 최신 E2E 로그 기준으로 기록 |
| 1차 dogfooding 진입 | Y/N | 🔴 (Phase 5 마무리 직후 의무) |

---

## 10. 다음 평가 갱신 트리거

본 snapshot 은 다음 task 종료 시점 전체 rewrite. 갱신 시 다음 항목 변동 우선 반영:

- SFU 그룹 통화 실 OS 미디어 캡처 + 다중 화면 visual ack → IMPLEMENTED → VERIFIED 전환 + 차별화/기술 점수 재산정.
- 원격 데스크탑 M4 실 OS capture/input 검증 진척 시 §3.7 / §3.6.
- Toonation REST + OBS WebSocket base_url 사용자 직접 입력 시 §3.7 ✅.
- mobile prerequisite 사용자 manual 회수 시 §3.9 ✅.
- coturn 4 env 사용자 직접 입력 시 §5 ✅.
- mobile Flutter base 본격 진입 시 §5 / §6 ✅.
- 1차 dogfooding 진입 시 §3.11 ✅ + KPI 실측 값.
- 차별화 추가 발생 시 §2.10 + §4 + §10 동시 갱신.
- 가드레일 메모리 / sub-agent 누계 변동.

---

## 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md)
- 정책: [PLANS.md](../../PLANS.md) · [PRODUCT_SENSE.md](../../PRODUCT_SENSE.md) · [QUALITY_SCORE.md](../../QUALITY_SCORE.md)
- 정책 본문: [docs/policies/doc-gardening.md](../policies/doc-gardening.md) · [adoption-roadmap.md](../policies/adoption-roadmap.md) · [execution-harness.md](../policies/execution-harness.md)
- 인프라 절차: [docs/references/ci-self-hosted-setup.md](../references/ci-self-hosted-setup.md) · [docs/references/smtp-setup.md](../references/smtp-setup.md)
- 실행계획: [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](../exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)
- 세션 인계: [docs/exec-plans/active/2026-05-17-session-handoff.md](../exec-plans/active/2026-05-17-session-handoff.md)
- 동행 snapshot: [vibe-coding.md](vibe-coding.md)
- HTML 등가: [docs/html/productization.html](../html/productization.html)
