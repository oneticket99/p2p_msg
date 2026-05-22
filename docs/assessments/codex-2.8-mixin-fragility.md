---
title: "codex 2.8 — mixin MRO fragility risk"
owner: oneticket99
last_verified: 2026-05-23T06:50:00+09:00
status: active
cycle: 169.534
---

# codex 2.8 — 21 mixin MRO fragility risk (cycle 169.534 신설)

> **본 문서 = cavecrew-reviewer agent (cycle 169.534 spawn, agentId `a4e453b1cf68fe30a`) 의 의무 finding 정리**. main_window 책임 분리 phase 본격 종료 후 신규 risk detect — 1 🔴 + 19 🟡 의무 reco.

---

## 1. 검증 baseline

- main_window.py = 600 line + 21 mixin 다중 상속
- MainWindow.__mro__ resolution verify (cycle 169.534): **22 cross-mixin method ALL resolved at runtime** ✅
- PyQt6 offscreen instantiation smoke PASS (cycle 169.533)

**결론**: 1 🔴 finding = hypothetical risk (실 break X). 19 🟡 = "MRO order-dependent" 정합 — 본 단계 = 의무 X, 의무 awareness 의 의무 retain.

---

## 2. reviewer 의무 finding 20건 (cycle 169.534)

### 2.1 🔴 main_window.py:125 — MRO fragile linear chain

**finding**: 21-mixin MRO linear chain. 8 cross-mixin method call without defensive hasattr guard. Single mixin reordering breaks at runtime.

**검증 결과**: 실 instantiation smoke PASS (cycle 169.533). 22 method ALL resolved. **risk = hypothetical** (신규 mixin 추가 시점 의무 awareness 의무).

**의무 fix candidate** (다음 cycle 위탁):
- A. `typing.Protocol` 안 cross-mixin dependency 명시 (strict type hint)
- B. mixin docstring 안 explicit dependency declaration 강화
- C. `hasattr` guard 추가 (가장 conservative, code churn 큰 변경)
- D. test smoke regression (`tests/ui/test_main_window_mixin_mro.py` 신설 reco)

### 2.2 🟡 cross-mixin method call 17건 (MRO order-dependent)

| caller mixin | called method | resolver mixin |
|---|---|---|
| ChatHelperMixin | `_mark_room_read` | RestPostMixin |
| ChatSendMixin | `_kind_room_local` | ChatHelperMixin |
| ChatSendMixin | `_post_and_resolve` | RestPostMixin |
| ChatSendMixin | `_send_bot_message` | BotChatMixin |
| ChatSendMixin | `_send_saved_message_rest` | RestPostMixin |
| ChatNavigationMixin | `_fetch_user_status` | FriendStatusMixin |
| ChatNavigationMixin | `_fetch_dm_history` | ChatHelperMixin |
| ChatNavigationMixin | `_fetch_bot_history` | BotChatMixin |
| ChatNavigationMixin | `_load_local_history` | ChatHelperMixin |
| ChatNavigationMixin | `_kind_room_local` | ChatHelperMixin |
| LifecycleEventsMixin | `_cancel_update_task` | UpdateLifecycleMixin |
| FriendSearchMixin | `_post_login_refresh` | AuthChainMixin |
| BotChatMixin | `_append_dm_message` | ChatSendMixin |
| RoomGroupChatMixin | `_exec_dialog_centered` | DialogCenterMixin |
| RoomGroupChatMixin | `_post_and_resolve` | RestPostMixin |
| RoomGroupChatMixin | `_dispatch_message_chain` | RestPostMixin |
| AuthChainMixin | `_refresh_chat_list_panel`/`_fetch_unread_counts`/`_refresh_pending_badge` | ChatNavigationMixin/ChatHelperMixin/FriendSearchMixin |

**검증**: 모든 17 call resolved at runtime (cycle 169.534 verify). MRO order = MainWindow class signature 의무 보장 (cycle 169.529 final).

### 2.3 🟡 attribute init order 3건 (low risk)

- `main_window.py:237` — `_sound_player` init in `_init_state` (line 237) + 사용 in line 321. **검증**: 9 helper 순서 의무 (state → window → splitter → sidebar → chatlist → right → input → finalize → status) 의 의무 정합. line 321 = `_init_status_and_startup_chain` 안 의무 — 호출 순서 의무 보장.
- `main_window.py:403` — `_tray_quit_requested` init + `_tray_hint_shown` lazy create (LifecycleEventsMixin line 59). **awareness**: lazy attribute 의무 pattern — `getattr(self, "_tray_hint_shown", False)` graceful 정합.
- `_auth_chain_mixin.py:93-97` — `getattr(self, "_friends_client", None)` 다음 line 96 직접 attribute access. **검증**: line 95 `if fc is not None` guard 의무 정합 PASS.

---

## 3. 다음 cycle (169.535+) fix 의무 reco

**Priority HIGH**:
- 신규 mixin 추가 시점 의무 — class signature 의 의무 위치 의무 carefully (MRO 정합 의무 break 회피).
- `tests/ui/test_main_window_mixin_mro.py` 신설 (cycle 169.534+): MainWindow class signature 의무 22 method present assert.

**Priority MED**:
- mixin docstring 안 의무 "Dependencies:" 섹션 명시 강화 (caller / callee MRO order 의무 explicit declaration).
- `typing.Protocol` 안 의무 cross-mixin contract 강제 (mypy 안 의무 strict check).

**Priority LOW**:
- `hasattr` guard 추가 (현 state = PASS, churn 큰 변경 회피).

---

## 4. 본 cycle 결론

- main_window 책임 분리 phase 본격 종료 (cycle 169.526~530) + PyQt6 smoke PASS (169.533) + codex 2.7 재 평가 (169.533).
- codex 2.8 reviewer finding 20건 = 실 runtime break X (MRO stable).
- **awareness retain + 다음 cycle test smoke 신설 의무**.
- 본 cycle = doc record 만. fix 직접 진입 X (낭비 churn 회피).

---

## 5. 참조

- cavecrew-reviewer finding raw — agentId `a4e453b1cf68fe30a` 의 임시 artifact 경로 기록. 저장소 밖 `/private/tmp/claude-501/.../tasks/a4e453b1cf68fe30a.output` 산출물이라 markdown 링크로 보존하지 않음.
- main_window.py:125 — MainWindow class signature 의무 (MRO 21 mixin 다중 상속)
- cycle 169.530 — `__init__` 9 helper split commit `bb705cf`
- cycle 169.533 — PyQt6 offscreen instantiation smoke commit `6f1cd0f`
