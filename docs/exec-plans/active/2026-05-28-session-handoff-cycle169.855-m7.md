---
title: "세션 인계 자료 — 한글 주석 페이즈 M7 진행 (cycle 169.855)"
owner: oneticket99
status: active
created: 2026-05-28
last_verified: 2026-05-28
related_code: ["tests/server/**/*.py", "tests/app/**/*.py", "tests/e2e/**/*.py"]
---

# 세션 인계 자료 — 한글 주석 페이즈 M7 (cycle 169.855)

> 정본 정합: [한글 주석 Exec Plan](2026-05-26-korean-comment-enrichment-phase.md) · [CLAUDE.md](../../../CLAUDE.md) · [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md)
> 본 문서는 다음 세션 **단일 진입점**. 첫 응답 = §2 의 M7 server s2 batch 부터 착수.

---

## 1. TL;DR — 어디까지 왔나

**한글 주석 상세화 페이즈(기능 diff 0 주석 전용 트랙)** 진행 중. HEAD = `2cfdf8e`(s1 직후 평가 sweep 완료).

| 마일스톤 | 범위 | 상태 |
| --- | --- | --- |
| M2 server repository | 21 | ✅ 완료 |
| M3 server API handler | 19 | ✅ 완료 |
| M4 app/net | 16 | ✅ 완료 |
| M5 app/rtc | 8 | ✅ 완료 |
| M6 app/ui | mixin 22 + dialog 29 = 51 | ✅ **완료** |
| **M7 e2e** | 9 | ✅ **완료** (사용자 directive "e2e 부터" 우선) |
| **M7 server** | 48 | 🔄 **3/48** (s1 완료) |
| **M7 app** | 155 | ⬜ 0/155 |
| G-final | 사용자 ack | ⬜ |

**M7 진척 = test 12/256** (e2e 9 + server 3).

---

## 2. 첫 응답 = M7 server s2 batch

다음 세션 첫 작업 = **tests/server 잔여 45 파일** batch 3개씩 진행(s2~s16). server test 우선 → 이후 tests/app 155(a1~).

### 2.1 server 잔여 45 (s1 처리분 3 제외)

```
test_avatars_repo · test_bot_handlers · test_bots_repo · test_config ·
test_contacts_app_versions_repo · test_devices_handlers ·
test_email_verification_devices_repo · test_email_verification_retry ·
test_emoji_moderation_handlers · test_emoji_packs_schema ·
test_file_meta_password_reset_repo · test_folder_handlers_integration ·
test_folder_repository · test_friends_handlers · test_friends_repo ·
test_health_handlers · test_logging_setup · test_main_integration ·
test_messages_handlers · test_messages_repo · test_middleware_activity ·
test_middleware_chain_integration · test_middleware_request_id ·
test_migration_0017_group_meta · test_peers_remote_handlers · test_protocol ·
test_reactions_handlers · test_read_states_repo · test_register_otp_integration ·
test_register_validation · test_remaining_repos · test_remote_handlers_audit ·
test_repo_dataclass_validation · test_reset_password_otp_integration ·
test_rooms_handlers · test_sfu_registry · test_sfu_room ·
test_signaling_room_audit · test_signaling_rooms_e2e ·
test_signaling_rooms_integration · test_smtp_client · test_users_repo_methods ·
test_version_handlers · test_version_handlers_admin · __init__
```

### 2.2 batch cadence (M2~M7 일관 — 절대 변경 금지)

```text
1. read 3 파일 module docstring head + SPDX 유무 확인
2. SPDX 부재 시 추가 (M4 signaling 선례 — 주석 라인, diff-0 안전)
3. module docstring 선존 양호 판단 (test 대상·전략 명시 여부)
4. Python filler sed: filler prefix(한글 주석 dash/colon 형) → 제거
5. 위생 grep: 대명사 2종 + 이중조사 + BPE 단독 글자 (§5 명령 — 런타임 문구 false-positive 배제)
6. diff-0: python3 tools/verify_comment_only.py HEAD <files>
7. 실 pytest: .venv/bin/python3 -m pytest <대상 파일> -q  (server = browser 무관, 실행됨)
8. ledger: README(M2 prepend 30행 trim) + History(M3 역순 prepend) + Exec Plan T-7 진척 + WBS row
9. doc-lint: bash tools/doc-lint.sh
10. commit + SKIP_PREPUSH=1 git push origin main + WBS commit_sha 갱신
```

> filler sed 실 명령은 §5 의 코드 블록 참조(본 단계 설명문에는 금지 토큰 리터럴 미포함 — PostToolUse hook 정합).

---

## 3. 핵심 함정 (반드시 숙지)

### 3.1 test 파일 JS-string `// 한글 주석` 은 diff-0 보호 — 절대 변경 금지

- e2e 파일(`tests/e2e/test_datachannel_*`, `test_*_call_*`)의 `// 한글 주석` 은 **Playwright `page.evaluate()` JS 문자열 내용** = AST Constant.
- 변경 시 `verify_comment_only` FAIL (기능 diff). **sed 패턴이 Python 주석 prefix(샵+공백) 만 매치하므로 JS 슬래시(`//`) 는 자동 보존** — 의도적 sed 패턴 유지.
- Python 주석(`# 한글 주석`)만 전환 대상.

### 3.2 런타임 string false-positive — "문의 의무" 등

- `"운영자 문의 의무"`(error dict 값) 같은 런타임 string 의 "의 의"(문의+의무 = 별개 단어)는 **이중조사 아님 + AST Constant** → 미변경 보존.
- 위생 grep 시 `grep -v '문의 의무'` 로 false-positive 배제.

### 3.3 선존 이중조사 "의 의"(comment/docstring) 는 정정 대상

- comment/docstring 안 진짜 이중조사("의 의")는 diff-0 안전하게 정정(M6 dialog 다수 정정 선례).

### 3.4 평가 freshness sweep — 5 commit threshold

- `tools/hook_assessment_freshness.sh` = productization.md/vibe-coding.md 마지막 갱신 후 **5 commit 누적 시 Stop hook block(exit 2)**.
- **현재 freshness = 0/5** (마지막 sweep `2cfdf8e` — s1 직후 갱신 완료). 다음 5 commit 누적 시 sweep 재발화.
- sweep 대상: productization.md(§1 종합/§3.1/§8 marker + footer) + vibe-coding.md(marker + §8) + **HTML mirror 2종 동시**(hook_html_mirror_consistency 가 .md 단독 갱신 차단). 점수 무변동(diff-0 트랙 — productization 7.6/10, vibe-coding 8.4/10).
- sweep commit = freshness counter reset.

### 3.5 HTML mirror 동시 갱신 의무

- 평가 .md 갱신 시 `docs/html/productization.html` + `docs/html/vibe-coding.html` marker(line 8) + last_verified(line 30) + footer(line ~527/480) **동시 갱신** 안 하면 PostToolUse hook block.

---

## 4. 가드레일 + 정본 (우선순위)

1. 가드레일 26건 — `~/.claude/.../memory/MEMORY.md`. 특히:
   - `feedback_no_korean_chuck_token` (BPE 단독 글자 금지)
   - `feedback_no_self_other_pronoun` (1인칭/3인칭 대명사 금지)
   - `feedback_no_triple_particle_chat` + 이중조사 "의 의"
   - `feedback_assessment_full_section_sweep` (평가 전면 sweep)
   - `feedback_skip_prepush_permanent_approval` (`SKIP_PREPUSH=1 git push origin main` 영구 GO)
   - `feedback_per_file_immediate_push` (batch 즉시 push)
2. 정본 CLAUDE_HARNESS_IMPORTANT.md (M1~M7 + Watcher)
3. [한글 주석 Exec Plan](2026-05-26-korean-comment-enrichment-phase.md) §4 주석 표준 D-1~D-6

---

## 5. 검증 명령 모음

```bash
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg

# diff-0 게이트
python3 tools/verify_comment_only.py HEAD <files>

# server test 실 실행 (oracle)
.venv/bin/python3 -m pytest tests/server/<file> -q

# app test (offscreen 의무 — cumulative QWidget hang 차단)
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/app -q   # 1963 passed 기준

# 위생 = PostToolUse hook(hook_post_write_inspect.sh)이 Write/Edit 직후 자동 강제
#   - 대명사 2종 + 이중조사 + BPE 단독 글자 패턴 자동 검출 → 위반 시 block
#   - 런타임 문구 false-positive(별개 단어 조합)는 comment/docstring 아니면 무시
#   - 별도 수동 grep 불필요 (hook 통과 = 위생 PASS)

# freshness count (5 도달 시 평가 sweep)
git rev-list --count 2cfdf8e..HEAD

# push
SKIP_PREPUSH=1 git push origin main
```

---

## 6. WBS

- `data/wbs.sqlite` `wbs_tasks` — directive 1건 = 1 row. commit 전 PENDxxx placeholder → push 후 commit_sha UPDATE.
- s1 row = commit_sha `ff85fb6`.

---

## 7. commit 참조 (본 세션 M5~M7 누계)

- M5 rtc 완료: `fc9aa33`/`ccba466`/`d010639`
- M6 mixin b1~b8: `24fe2f2`~`bc58cd3` (drawer = 22/22 완료)
- M6 dialog d1~d9: `beea2cc`~`ca14f78` (29/29 완료)
- 평가 sweep: `efdc582`(직전세션) / `f30dc94` / `7b7876b` / `80e0f40` / `2cfdf8e`(s1 직후)
- M7 e2e e1~e2: `47c070b`/`e41616d` (9/9 완료)
- M7 server s1: `ff85fb6` (3/48)
- 인계 자료 + sweep: `0da36b4`/`2cfdf8e`

---

마지막 갱신: 2026-05-28 (cycle 169.855 — M7 server s1 + 평가 sweep 직후, HEAD `2cfdf8e`)
