// SPDX-License-Identifier: GPL-3.0-or-later
// TooTalk Phase 5 Item 2 mobile entry — cycle 147 skeleton.
// 본격 화면 chain (회원가입 + 로그인 + OTP + ChatList + ChatRoom) = cycle 188~192 본격.

import 'package:flutter/material.dart';

// 앱 진입점 — Flutter runApp 으로 TooTalkApp 위젯 마운트
void main() {
  runApp(const TooTalkApp());
}

// 최상위 앱 위젯 — MaterialApp + theme + 진입 라우트 정의
class TooTalkApp extends StatelessWidget {
  const TooTalkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TooTalk',
      // TooTalk 의 brand seed color (DESIGN.md §11 정합 — 짙은 청색 계열)
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1B3A66)),
        useMaterial3: true,
      ),
      home: const _LoginScreen(),
    );
  }
}

// 임시 로그인 화면 placeholder — cycle 188 본격 진입 시 LoginScreen 으로 대체
class _LoginScreen extends StatelessWidget {
  const _LoginScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('TooTalk')),
      body: const Center(
        // 본 cycle 은 skeleton — Phase 5 본격 cycle → actual UI 신설
        child: Text('Phase 5 mobile skeleton (cycle 147)'),
      ),
    );
  }
}
