---
title: "다음 세션 인계 — cycle 169.853 (avatar M1~M7 완결 + 한글 주석 페이즈 M2 완료)"
owner: oneticket99
status: active
created: 2026-05-27
last_verified: 2026-05-27
---

# 다음 세션 인계 — cycle 169.853

> 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) · 운영: [CLAUDE.md](../../../CLAUDE.md) · 맵: [AGENTS.md](../../../AGENTS.md)
> 본 문서 = 다음 세션이 **즉시 이어받을** 상태 + 첫 응답 지시 + 잔여 큐. main HEAD = `39c6a01`.

---

## 1. TL;DR (현 상태)

- **HEAD = `39c6a01`**, tree clean, 전 CI/hook 게이트 GREEN. 전체 약 2605 passed(server 642 + app 1963) 회귀 0.
- **avatar 이미지 picker — M1~M7 코드+문서 완결** (`fb13fed` 시점). 잔존 = **G-final 사용자 실 webcam visual ack**(headless 대체 불가, 사용자 직접 — 체크리스트 [avatar Exec Plan §14.1](2026-05-26-avatar-image-picker-upload.md)).
- **한글 주석 상세화 페이즈 — M2(repo 21/21) + M3(server API handler 19/19) 완료** (`d416d81`·`09b2f78`, cycle 169.854 b1~b8). 진행 중 품질 트랙(기능 diff 0). 카탈로그 컨벤션 정정 다수(rooms 6→7·friends 6→8·auth 5→15·folder 4→5·read 2→3). 런타임 string(streaming HTML·auth register log) 미변경 백로그.
- **평가 staleness sweep + dereliction 회수 완료** (`160a5ec`·`39c6a01`) — 평가 2종 md+html + current-review HEAD 마커 + token-usage-30d 재산출(staleness hook 해소) + dereliction MEDIUM 2건 회수(평가 §5/§6/§8 full-section sweep + WBS 169.853 16 row backfill). 점수 7.6/8.4 무변동(diff 0).
- 부수 도구: `tools/verify_comment_only.py`(주석 전용 게이트 — docstring 재귀 제거 후 ast.dump 비교).

---

## 2. 다음 세션 첫 응답 (바로 이것부터)

**한글 주석 상세화 페이즈 M4 — `app/net/*_client.py` (13 파일) 주석 보강** 부터 이어간다.

- blast radius 역순 순서(§5 [comment Exec Plan](2026-05-26-korean-comment-enrichment-phase.md)): M2(완료) → M3 handler(완료) → **M4 net** → M5 rtc → M6 ui → M7 test(e2e) → G-final.
- M4 의 핵심 = client REST/WS 계약 docstring 에 **재시도/타임아웃/SSL 우회 의도 / QThread worker 생명주기 / signal emit 부작용** 명시(T-5).
- M2 에서 정착시킨 동일 패턴을 그대로 적용:
  1. 영역 batch(2~3 파일) 단위로 module/class/함수 docstring(의도/Parameters/Returns/Raises/부작용) + inline "왜" 보강.
  2. **기능 diff 0 게이트** — `python3 tools/verify_comment_only.py HEAD <파일들>` PASS 의무(주석/docstring 외 동작 라인 변경 0).
  3. **pytest 무변경** — 관련 영역 + 전량 회귀 0.
  4. **언어 위생** — BPE U+CE21 단독 0 + self/other 지칭 대명사 0 + "의 의" 이중조사 0. PostToolUse hook 이 자동 차단.
  5. batch commit + `SKIP_PREPUSH=1 git push origin main` + M2 README/M3 History prepend + Exec Plan 진척 갱신.
- M3 의 핵심 = endpoint docstring 에 **인증 요구 / 검증 순서 / 오류 코드 매핑 / 부작용(DB write·broadcast)** 명시.

---

## 3. 잔여 큐 (한글 주석 페이즈)

| 마일스톤 | 영역 | 파일 수 | 상태 |
|---|---|---|---|
| M1 | 주석 표준 §4 D-1~D-6 + 본보기 friends.py | 1 + 표준 | ✅ (reviewer PASS, HIGH 회수) |
| M2 | `server/db/repositories/*.py` | 21 | ✅ **완료** (전수 diff-0 + server 642 무변경) |
| M3 | `server/api/*_handlers.py` | 19 | ✅ **완료** (b1~b8, 전수 diff-0 + server 642 무변경, 카탈로그 정정 다수) |
| **M4** | `app/net/*_client.py` | **13** | **다음** |
| M5 | `app/rtc/*.py` | 7 | 큐 |
| M6 | `app/ui/_*_mixin.py`(22) + `*_dialog.py`(29) | 51 | 큐 (filler `한글 주석` 74 파일 — 의도 기반 전환) |
| M7 | `tests/app`(155) + `tests/server`(48) + `tests/e2e`(9) | 256 | 큐 (사용자 directive — e2e 포함) |
| G-final | 전 영역 누계 diff-0 + pytest 무변경 + 사용자 ack | — | 큐 |

> M6 ui 는 offscreen pytest(`QT_QPA_PLATFORM=offscreen`) + skip 기준선 고정 의무(B-4). M7 test 도 assert/fixture 동작 라인 불변(docstring/inline 만).

---

## 4. M2 에서 확립한 핵심 교훈 (M3+ 에 그대로 적용)

1. **함수/SQL 카탈로그 컨벤션 (§4 D-1)** — module docstring 의 함수 목록은 **실 심볼명** + 개수 일치. 약칭/단수복수 불일치 금지(reviewer T-2 HIGH). rooms("10 SQL"→실 15 함수)·bot_escalations(부재 list_by_agent 제거) 전례.
2. **ValueError 등 런타임 문자열은 docstring 아님 — 절대 미변경** — error message 를 "다듬으면" AST Constant 변경 = 기능 diff 0 위반. `verify_comment_only.py` 가 검출·차단(streaming_oauth_tokens 전례). 주석/docstring 만 touch.
3. **과잉 주석 금지** — 이미 모범 docstring 보유 파일(avatars/users/reclaim_atomic 등)은 표준 gap(계층 §E + invariant)만 보강. 자명 코드 1:1 재진술 금지.
4. **평가 staleness sweep — 2 경로 + full-section 의무** — (a) commit 5건마다 `hook_assessment_freshness.sh`(임계 5), (b) `hook_assessment_token_rewrite_trigger.sh` 가 **12h staleness**(cap 6h) 도 Stop block(본 세션 `160a5ec` 가 (b)로 발화). 기능 diff 0 라 점수 무변동이나 sweep 의무. **가드레일 `feedback_assessment_full_section_sweep` = §1+§2+§3+§5+§6+§8 6 영역 전면 sweep**(2회차 비판 회수, 다음 위반 시 Stop hook 강제) — §1 row + §2 prepend 만 = 위반. dereliction-detector 가 §5/§6/§8 미터치를 MEDIUM 검출하므로 무변동이라도 "cycle N 무변동 근거" 1줄 sweep 노트 필수(`39c6a01` 전례). PASS 수치 drift(2770/2521 같은 stale)도 sweep 시 단일 값 정합 의무.
5. **HTML mirror 동시성** — 평가 md 편집 시 html 동반(PostToolUse `hook_html_mirror_consistency.sh` 차단, **md 단독 편집마다 fire**). 평가 2 pair = last_verified + 사이클 N fingerprint 정합. md 전부 편집 후 html 일괄 동기 → 최종 commit 에서 dirty-together 통과.
6. **dereliction auto-spawn + 회수** — 작업 완료 보고 직후 dereliction-detector spawn(`run_in_background`). WBS = `data/wbs.sqlite`(gitignore, 로컬) **directive 1건 = 1 row** — M2 batch 누적 시 row 누락 detect 빈발(본 세션 12 row backfill, 16/16 done). post-commit 후 PENDING row 의 commit_sha 갱신 의무.

---

## 5. avatar 이미지 picker — G-final 만 잔존 (사용자 직접)

- M1~M7 코드+문서 완결. 유일 잔존 = **실 webcam visual ack**(headless 자동 검증 불가).
- 7단계 수동 검증 체크리스트 = [avatar Exec Plan §14.1](2026-05-26-avatar-image-picker-upload.md). 사용자 GO/NO-GO 후 `active/`→`completed/` 이동.
- 백로그(비차단): reviewer MEDIUM-A — `_MemberRow` 가 `avatar_cache().avatar_ready` 에 connect 하나 disconnect 부재(ref-match 가드로 기능 무해, 위생 차원 — MemberListWidget 1곳 connect 로 축소 권장).

---

## 6. 부수 잔존 (별개 트랙)

- codex §4.6 잔여 하드코딩 수렴 — stun / OAuth redirect / bot sender id (avatar/주석 페이즈와 별개).
- §8-4 배포 smoke — manual, 사용자 직접 영역.

---

## 7. 주요 commit 참조 (cycle 169.852~853)

| commit | 내용 |
|---|---|
| `fb13fed` | avatar M1~M7 완결 (G-final 체크리스트) |
| `93d77b9` | 주석 페이즈 active + e2e scope + `verify_comment_only.py` |
| `428f85a`·`4d42059` | M1 본보기 friends.py + reviewer HIGH 회수 |
| `525f7ff`~`d416d81` | M2 server repository 21/21 (batch 1~9) |
| `3c2efcc` | 다음 세션 인계 자료 (본 문서) |
| `160a5ec` | 평가 2종+current-review+token-usage staleness sweep (M2 21/21 반영) |
| `39c6a01` | 평가 §5/§6/§8 full-section sweep — dereliction MEDIUM-2 회수 + WBS 16 row backfill |

---

마지막 갱신: 2026-05-27 20:45 KST (cycle 169.854 — 주석 페이즈 M3 server API handler 19/19 전수 완료(b1~b8). avatar M1~M7 완결 + 주석 M2 21/21 + M3 19/19. HEAD `09b2f78`. 다음 = M4 app/net 13)
