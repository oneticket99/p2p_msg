---
title: "session handoff — cycle 169.826~838 manifest (다음 session 진입)"
owner: oneticket99
last_verified: 2026-05-26T07:05:00+09:00
status: active
---

# Session Handoff — cycle 169.826~838 (2026-05-26 신설)

> 본 doc = 본 session 종료 시점 다음 session 진입 첫 액션 manifest. dogfooding 회수 + in-app 모달 전환 chain 압축 발췌 + 잔존 task 직접 진입 명령 정의.

---

## 1. 30초 TL;DR

본 session = dogfooding 발견 버그 + UX 정합 회수 chain (169.826~838). 데모 서버 복구부터 전 dialog 모달 통일까지.

| 묶음 | cycle | 산출 |
|---|---|---|
| A. 데모 서버 502 회수 + SFU 재가용 | 826~828 | aiortc graceful optional import + requirements 추가 |
| B. OTP 메일 + dogfooding 버그 6종 + i18n 5언어 | 834~835 | SMTP sasldb 동기 + 스크롤 dedup + 친구 pending 모델 + 메뉴 auth 토글 |
| C. 그룹 멤버 UX + 수신음 정정 | 836~837 | 멤버 보기 모달 + 원형 아바타 행 통합 + 메뉴 stub 전수 제거 |
| D. **전 dialog in-app overlay 모달 전환** | 838 | 별도 OS 윈도우 제거 + "방 입장" 폐지 + ConfirmDialog 얼럿창 in-app 화 |

핵심 milestone:
- **전 dialog in-app overlay 모달 통일** — `_exec_dialog_centered`(차단) / `_embed_dialog_centered`(비차단 async) / `_modal_helper.exec_modal`(nested parent 체인 walk) 3 진입 경로 확립
- **별도 OS 윈도우 예외 4종 명문화** (FRONTEND.md §16): 원격 데스크탑 제어 상대화면 창 · startup auth bootstrap · tray 재인증(switch code 2/3 손실) · HamburgerDrawer(QFrame overlay shim)
- **"방 입장"(room_id 직접 입력) 전수 제거** — 그룹방 = "그룹 만들기" + 멤버 초대로만 생성
- **ConfirmDialog 정적 헬퍼(show_info/warning/critical/ask) in-app 화** — 40+ 호출 사이트 무변경 (헬퍼 내부 exec_modal 캡슐화)
- **CI e2e chromium 회귀 회수** — self-hosted 러너 playwright 미설치 → `playwright install chromium` step 추가 (ci.yml)
- reviewer-gate **2차 PASS** (M1 BLOCKER + HIGH 3 + MEDIUM 1 + OBSERVATION 1 전건 회수)
- 빌드 2 platform PASS — macOS .app (198M, zip 80M, sha256 `6885c2b8…`) + Windows .exe (build.yml runId 26421331883)
- 평가 snapshot 838 동기 (productization 7.6/10 · vibe-coding 8.4/10 유지)

main HEAD = `3b1a6dd` (PR #26 squash merge).

---

## 2. 첫 응답 템플릿 (다음 session 진입)

```text
이전 session handoff (cycle 169.826~838) 정독 완료. 데모 서버 복구 + 전 dialog in-app 모달 통일 마무리.

본 session 진입 우선순위:
1. group-flow e2e/isolated test 재설계 — 방장 그룹만들기 + 참가자 초대 진입 방식 (방번호 입력 폐지 정합)
2. 사용자 dogfooding ack — cycle838 in-app 모달 빌드 (dist/TooTalk.app) 실행 + 시각 verify
3. manual visual ack 일괄 시연 (실 OS / 다중 화면 / 원격 M4 / SFU G4 — 후반 일괄, feedback_visual_ack_batched_later)
```

---

## 3. 잔존 task (우선순위 순)

### 3-1. group-flow e2e/isolated test 재설계 (최우선, 본 session 미착수)
- **현 상태**: 서버측 create/join/invite/kick 는 integration test 존재 (`tests/integration/test_room_create_join_leave_e2e.py` · `test_room_invite_kick_e2e.py`).
- **요청 directive**: "e2e isolated test 방식 = 방장이 그룹만들기로 그룹 추가 → 참가자 추가 → 초대를 통해 진입하는 방식". 즉 방번호 입력(`_on_open_room_dialog` 폐지)이 아닌 client UI 전 flow.
- **착수점**: `tests/app/ui/test_main_window_rooms.py` 의 `room_entered.emit(N)` 직접 trigger 방식을 "그룹 만들기 wizard(`_on_drawer_new_group`) → `group_created` signal → 멤버 초대" 체인으로 재구성. NewGroupDialog + 초대 flow 검증.
- **주의**: offscreen 가드(`_exec_dialog_centered` non-blocking) 정합 유지.

### 3-2. 사용자 dogfooding ack — cycle838 빌드
- `open dist/TooTalk.app` (로컬 빌드, 198M). in-app 모달 시각 확인: 멤버 보기·연락처·설정·프로필·통화·얼럿(ConfirmDialog) 전부 메인 레이아웃 안 overlay 인지.
- "방 입장" 메뉴 제거 확인. 새창 = 원격제어 상대화면 창만.

### 3-3. manual visual ack 일괄 시연 (후반, 비차단)
- feedback_visual_ack_batched_later — 실 OS / 다중 화면 / 원격 M4(G3) / SFU G4(다중 미디어 캡처). dev 증분 비차단, 후반 일괄.

### 3-4. (보류) streaming
- project_streaming_deprioritized — chzzk/kick/twitch + oauth + receive_loop 가장 후순위. youtube_client 삭제 완료. 당장 불필요.

---

## 4. 활성 가드레일/directive (본 session 신규·강화)

- **전 dialog in-app overlay 모달** — 새창 = 원격 데스크탑 제어 상대화면 창 1개뿐 (FRONTEND.md §16 정본).
- **완성 후 테스트 요청** — 미구현 항목 없는지 체크 후에만 사용자 테스트 요청 (feedback_complete_before_test_handoff).
- **사용자 개입 최소화** — manual `!` 떠넘기기 금지. SSH 배포 = `Bash(ssh -i ~/.ssh/tootalk_deploy*)` permission 등록 완료 → main session 직접 (feedback_minimize_user_involvement).
- **redeploy 후 nginx restart 필수** — web/ws recreate → upstream IP stale → 502 (feedback_redeploy_nginx_restart).
- **reviewer-gate = 모든 feat 의무** — 자동검증 구간 포함, 면제 부재 (feedback_reviewer_gate_all_feat_mandatory).
- **텍스트 레이블 배경 투명** — 모든 QLabel `background: transparent;` (feedback_text_label_transparent_bg).

---

## 5. 직접 진입 명령

```bash
# 현 위치 확인
cd /Users/1ticket/Documents/vscode_work/p2p_msg && git log --oneline -3

# group-flow test 재설계 착수 — 현 rooms test + 그룹 만들기 flow 파악
grep -n 'room_entered.emit\|_on_drawer_new_group\|group_created' tests/app/ui/test_main_window_rooms.py app/ui/_drawer_mixin.py

# in-app 모달 정본 정독
sed -n '/## 16. 다이얼로그 모달 정책/,/## 17/p' FRONTEND.md

# 빌드 dogfooding
open dist/TooTalk.app
```

---

## 6. 참조

- [FRONTEND.md §16](../../../FRONTEND.md) — 다이얼로그 모달 정책 (in-app overlay + 별도 윈도우 예외 4종)
- [main handoff 2026-05-17](2026-05-17-session-handoff.md) — 누계 manifest 정본
- [productization snapshot](../../assessments/productization.md) · [vibe-coding snapshot](../../assessments/vibe-coding.md) — cycle 838 동기
- 가드레일 인덱스: `~/.claude/projects/-Users-1ticket-Documents-vscode-work-p2p-msg/memory/MEMORY.md`
