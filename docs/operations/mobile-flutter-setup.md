<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- TooTalk Phase 5 Item 2 mobile Flutter setup 운영 가이드 — cycle 147 신설 -->

# Mobile Flutter Setup — Phase 5 Item 2 본격 진입 prerequisite

> 본 가이드는 TooTalk Phase 5 Item 2 — mobile client 본격 cycle (181~200) 진입 prerequisite 으로 사용자 가 manual setup 의무 인 절차 만 다룬다.
> cycle 147 skeleton 은 file 신설 만 — 실 Flutter SDK install + `flutter create` scaffold + binding 은 본 가이드 의 절차 완료 후 본격 cycle 의 진입 신호.

---

## 1. 사전 환경

| 환경 | 요구 버전 | 비고 |
| --- | --- | --- |
| macOS | 14.0 (Sonoma) ↑ | iOS 빌드 의무 |
| Xcode | 15.0 ↑ | App Store Connect signing |
| Android Studio | Hedgehog 2023.1.1 ↑ | Android SDK 34 |
| Flutter SDK | 3.22.0 ↑ | `pubspec.yaml` `environment.flutter` 정합 |
| Dart SDK | 3.4.0 ↑ | Flutter 의 bundled |

---

## 2. Flutter SDK install

### 2-1. macOS (Apple Silicon + Intel 공용)

```bash
# Homebrew 경유 install (권장)
brew install --cask flutter

# 또는 공식 zip 경유 install
cd ~/development
curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_arm64_3.22.0-stable.zip
unzip flutter_macos_arm64_3.22.0-stable.zip
export PATH="$PATH:$HOME/development/flutter/bin"
```

`~/.zshrc` (또는 `~/.bashrc`) 에 PATH 영구 등록:

```bash
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.zshrc
source ~/.zshrc
```

### 2-2. 설치 검증

```bash
flutter --version
# Flutter 3.22.x • channel stable • https://github.com/flutter/flutter.git
# Framework • revision <hash>
# Engine • revision <hash>
# Tools • Dart 3.4.x • DevTools 2.34.x
```

---

## 3. flutter doctor — 환경 진단

```bash
flutter doctor -v
```

본 가이드 cycle 181 본격 진입 prerequisite — 다음 5 항목 GREEN 의무:

- `[✓] Flutter` — SDK install OK
- `[✓] Android toolchain` — Android SDK 34 + accept license
- `[✓] Xcode` — iOS toolchain OK
- `[✓] Chrome` — Web 영역 debug 용 (선택)
- `[✓] Android Studio` — IDE binding

문제 발생 시 `flutter doctor --android-licenses` 명령으로 accept.

---

## 4. iOS 빌드 환경

### 4-1. Xcode + CocoaPods

```bash
# CocoaPods install
sudo gem install cocoapods

# iOS simulator 확인
xcrun simctl list devices
```

### 4-2. iOS signing — App Store Connect

- Apple Developer 계정 의무 ($99/year).
- App Store Connect 안에서 TooTalk app 등록 + bundle id `com.tootalk.mobile`.
- APNs key 등록 — Phase 5 cycle 188~190 FCM binding prerequisite.

---

## 5. Android 빌드 환경

### 5-1. Android Studio + SDK Manager

- Android Studio install → SDK Manager → Android 14 (API 34) + Android 13 (API 33) install.
- AVD Manager 안에서 Pixel 7 emulator 신설.

### 5-2. Android signing — Play Store

- Google Play Console 계정 의무 ($25 일회).
- `mobile/android/key.properties` 신설 (gitignore 정합):

```properties
storePassword=<keystore 비밀번호>
keyPassword=<key 비밀번호>
keyAlias=tootalk
storeFile=/path/to/tootalk-release.keystore
```

- keystore 신설:

```bash
keytool -genkey -v -keystore ~/keystores/tootalk-release.keystore \
  -keyalg RSA -keysize 2048 -validity 10000 -alias tootalk
```

---

## 6. Flutter project scaffold (본격 cycle 181 진입 시)

본 cycle 147 은 skeleton — `flutter create` scaffold 는 cycle 181 본격 진입 시 의 사용자 manual ack 후.

```bash
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg/mobile/

# 본 skeleton 의 file 4종 (pubspec.yaml + lib/main.dart + lib/signaling/ws_client.dart + .gitignore) 보존
# Flutter scaffold 의 ios/ + android/ + test/ + analysis_options.yaml 추가 생성
flutter create --org com.tootalk --project-name tootalk_mobile .

# dependency install
flutter pub get
```

---

## 7. libsignal-dart binding (cycle 183 본격)

```bash
flutter pub add libsignal_protocol_dart
```

- desktop `app/security/e2ee_session.py` (libsignal Python) 와 동등한 X3DH + Double Ratchet 흐름 binding.
- prekey bundle + identity key 관리 + session save → LocalStorage / SQLite persistence.

---

## 8. flutter-webrtc DataChannel binding (cycle 184~187 본격)

```bash
# pubspec.yaml 에 이미 선언 됨 — install 만
flutter pub get

# iOS permission — ios/Runner/Info.plist
# NSCameraUsageDescription + NSMicrophoneUsageDescription 추가
```

---

## 9. Firebase Cloud Messaging (cycle 188~190 본격)

```bash
# FlutterFire CLI install
dart pub global activate flutterfire_cli

# Firebase project 신설 + config 자동 생성
flutterfire configure --project=tootalk-phase5
```

- iOS APNs key 등록 — Apple Developer + Firebase Console 연동.
- Android `google-services.json` 자동 생성 + `mobile/android/app/` 경로에 배치.

---

## 10. 빌드 + release (cycle 195~200 본격)

### 10-1. iOS release (App Store)

```bash
flutter build ipa --release
# Xcode 안에서 Archive → Upload → App Store Connect → TestFlight → 심사 → 출시
```

### 10-2. Android release (Play Store)

```bash
flutter build appbundle --release
# Google Play Console → Internal Testing → Closed Testing → Production
```

---

## 11. 절대 금지

- 본 가이드 의 절차 사용자 manual setup ack 없이 cycle 181 본격 진입 차단.
- Flutter SDK 자체 install 자동화 차단 (사용자 manual).
- iOS / Android signing 인증서 자동 신설 차단 (사용자 Apple / Google 계정 의무).
- Firebase project 자동 신설 차단 (사용자 Google 계정 의무).
- 본 가이드 무시 + 본격 cycle 진입 = 가드레일 위반.

---

## 12. 참조

- [`../../mobile/README.md`](../../mobile/README.md) — Phase 5 Item 2 mobile base 안내.
- [`../../mobile/pubspec.yaml`](../../mobile/pubspec.yaml) — Flutter dependency 선언.
- [`../../mobile/lib/main.dart`](../../mobile/lib/main.dart) — 앱 진입점 skeleton.
- [`../../mobile/lib/signaling/ws_client.dart`](../../mobile/lib/signaling/ws_client.dart) — signaling WS client placeholder.
- 가드레일: `project_phase5_mobile_last.md` — mobile = Phase 5 가장 마지막.

---

마지막 갱신: 2026-05-19 (cycle 147 — Phase 5 Item 2 mobile Flutter setup 가이드 신설)
