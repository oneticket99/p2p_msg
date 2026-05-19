<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- TooTalk Phase 5 Item 2 mobile base 안내 — cycle 147 skeleton -->

# TooTalk Mobile (Phase 5 Item 2 — Flutter base skeleton)

> 본 디렉토리는 TooTalk 의 Phase 5 Item 2 — mobile client 의 **base skeleton** 만 담는다.
> 본격 binding (flutter-webrtc DataChannel + libsignal-dart E2EE + FCM push + iOS/Android build chain) 은 **cycle 181~200** 본격 진입 시 단계별 cycle 별 산출물 로 확장한다.
> 사용자 directive `project_phase5_mobile_last.md` 정합 — mobile = Phase 5 가장 마지막 단계. 이전 단계 (i18n + emoji pack + bot framework + 원격 제어) 완료 후 본격 진행 의무.

---

## 1. 본 skeleton 의 범위 (cycle 147 산출)

| 항목 | 산출 file | cycle 147 범위 | cycle 181~200 본격 범위 |
| --- | --- | --- | --- |
| Flutter manifest | `pubspec.yaml` | dependency 목록 선언 (flutter-webrtc + http + ws + firebase) | actual SDK install + `flutter pub get` 실 binding |
| Entry point | `lib/main.dart` | `MaterialApp` + placeholder login screen | 회원가입 + 로그인 + OTP + ChatList + ChatRoom 5 화면 chain |
| Signaling client | `lib/signaling/ws_client.dart` | `WebSocketChannel` placeholder class | aiortc 와 동등한 RTCPeerConnection + DataChannel binding |
| Git ignore | `.gitignore` | Flutter standard ignore | (변경 없음) |
| 운영 문서 | `../docs/operations/mobile-flutter-setup.md` | Flutter SDK install 명령 + flutter doctor + iOS/Android build 명령 | 실 release 빌드 sign + store upload 절차 |

> **본 cycle 은 file 신설 skeleton 만**. 실 Flutter SDK 설치 + `flutter create` scaffold + iOS / Android build 는 차후 cycle 의 사용자 manual setup ack 후 진행.

---

## 2. Flutter SDK 의무 (사용자 manual setup ack)

본 skeleton 은 Flutter SDK 가 **사전 설치돼 있다는 전제** 만 둔다. cycle 147 은 SDK 자체 설치를 차단한다 (skeleton 만).

- Flutter SDK 설치 + iOS / Android 환경 setup → `docs/operations/mobile-flutter-setup.md` 참조.
- 사용자 manual setup 완료 후 `flutter doctor` 의 GREEN 응답이 cycle 181 본격 진입 prerequisite.

---

## 3. 본격 cycle 181~200 prerequisite

| prerequisite | 검증 명령 | 담당 cycle |
| --- | --- | --- |
| Flutter SDK install (≥ 3.22) | `flutter --version` | cycle 181 직전 |
| iOS toolchain (Xcode 15+) | `flutter doctor` | cycle 181 직전 |
| Android toolchain (SDK 34+) | `flutter doctor` | cycle 181 직전 |
| libsignal-dart binding | `pub add libsignal_protocol_dart` | cycle 183 |
| flutter-webrtc DataChannel | `pub add flutter_webrtc` (이미 `pubspec.yaml` 선언) | cycle 184~187 |
| FCM iOS APNs + Android FCM | Firebase Console + APNs key 등록 | cycle 188~190 |
| Release build sign (App Store + Play Store) | `flutter build ipa` + `flutter build appbundle` | cycle 195~200 |

---

## 4. mobile / desktop 동등성 매핑

본 cycle 의 skeleton 은 desktop (`app/`) 기능을 mobile (`mobile/`) 영역에서 동일 흐름으로 binding 할 base 만 둔다. 본격 cycle → actual binding 범위 매핑:

| desktop 구현 (`app/`) | mobile 매핑 (`mobile/`) | 본격 cycle |
| --- | --- | --- |
| `app/network/signaling_client.py` | `lib/signaling/ws_client.dart` | cycle 181 |
| `app/security/e2ee_session.py` (libsignal Python) | `lib/security/signal_session.dart` (libsignal-dart) | cycle 183 |
| `app/network/rtc_manager.py` (aiortc) | `lib/network/rtc_manager.dart` (flutter-webrtc) | cycle 184~187 |
| `app/ui/login_view.py` | `lib/ui/login_screen.dart` | cycle 188 |
| `app/ui/chat_view.py` | `lib/ui/chat_room_screen.dart` | cycle 189~192 |
| `app/updater/` (PyInstaller swap) | App Store + Play Store 자체 update chain | cycle 195~200 |

---

## 5. 절대 금지 (본 cycle 범위)

- 실 Flutter SDK 설치 차단 (skeleton 만).
- `flutter create` scaffold 차단 (cycle 181 본격 진입 시).
- `flutter pub get` 실 binding 차단 (cycle 181 본격 진입 시).
- Firebase project 신설 + APNs key 등록 차단 (cycle 188~190 본격 진입 시).
- iOS / Android release build sign 차단 (cycle 195~200 본격 진입 시).
- 루트 마크다운 신규 생성 차단 — `mobile/README.md` = subdirectory 의 정합. 정본 §K (루트 18 동결) 준수.

---

## 6. 참조

- [`../CLAUDE.md`](../CLAUDE.md) — 세션 내 서브에이전트 호출 규약.
- [`../AGENTS.md`](../AGENTS.md) — 저장소 맵 + 5단계 워크플로우.
- [`../docs/operations/mobile-flutter-setup.md`](../docs/operations/mobile-flutter-setup.md) — Flutter SDK install + iOS / Android build 명령.
- 가드레일: `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_phase5_mobile_last.md` — mobile = Phase 5 가장 마지막 directive.

---

마지막 갱신: 2026-05-19 (cycle 147 — Phase 5 Item 2 mobile Flutter base skeleton 신설)
