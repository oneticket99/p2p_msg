// SPDX-License-Identifier: GPL-3.0-or-later
// TooTalk Phase 5 Item 2 mobile signaling WebSocket client placeholder.
// cycle 147 skeleton — 본격 binding (RTCPeerConnection + offer/answer + ICE) = cycle 181~187.

import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

/// signaling WebSocket client placeholder — desktop `app/network/signaling_client.py` 의 mobile 매핑.
///
/// 본격 cycle 181~187 의 binding 범위:
/// - aiohttp WS endpoint `/ws/signaling` 와 handshake
/// - JSON message routing (offer / answer / candidate / register / lookup)
/// - reconnect + ping/pong + JWT auth header
/// - flutter-webrtc 의 RTCPeerConnection 와 actual binding
class SignalingWsClient {
  /// signaling 서버 WS URL — 데모 서버 `114.207.112.73:5050` 기본
  final Uri serverUri;

  /// 인증 토큰 — Phase 1 회원가입 + 로그인 chain 의 발급
  final String? authToken;

  /// 실 WebSocket channel — connect 후 binding
  WebSocketChannel? _channel;

  /// 수신 stream subscription
  StreamSubscription<dynamic>? _subscription;

  /// 수신 메시지 stream — 외부 listener 가 구독
  final StreamController<Map<String, dynamic>> _messages =
      StreamController<Map<String, dynamic>>.broadcast();

  /// signaling 수신 stream 외부 노출
  Stream<Map<String, dynamic>> get messages => _messages.stream;

  SignalingWsClient({required this.serverUri, this.authToken});

  /// 서버 connect — 본 cycle 은 placeholder. 본격 binding cycle 181 에서 reconnect + auth header 추가.
  Future<void> connect() async {
    // skeleton — 실 connect 차단. cycle 181 본격 진입 시 actual binding.
    _channel = WebSocketChannel.connect(serverUri);
    _subscription = _channel!.stream.listen(
      _onMessage,
      onError: _onError,
      onDone: _onDone,
    );
  }

  /// 메시지 send — JSON encode + WS send
  void send(Map<String, dynamic> payload) {
    final channel = _channel;
    if (channel == null) {
      throw StateError('signaling channel not connected');
    }
    channel.sink.add(jsonEncode(payload));
  }

  /// 종료 — subscription cancel + channel close
  Future<void> close() async {
    await _subscription?.cancel();
    await _channel?.sink.close();
    await _messages.close();
  }

  // 수신 메시지 handler — JSON decode 후 stream emit
  void _onMessage(dynamic raw) {
    if (raw is String) {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        _messages.add(decoded);
      }
    }
  }

  // 오류 handler — cycle 181 의 reconnect chain 으로 확장 예정
  void _onError(Object error, StackTrace stackTrace) {
    _messages.addError(error, stackTrace);
  }

  // 종료 handler — cycle 181 의 reconnect chain 으로 확장 예정
  void _onDone() {
    _messages.add({'type': 'disconnect'});
  }
}
