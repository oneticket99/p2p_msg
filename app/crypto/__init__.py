# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) Phase 2 E2EE 패키지.
#
# 의존: `cryptography` (PyCA, ChaCha20-Poly1305 + AES-GCM + X25519 + HKDF).
# 본 디렉토리 = libsignal-protocol wrapping 의 첫 단계 — AES-GCM + X25519 ECDH helper.
# 완전 Signal Protocol (Double Ratchet + 3-DH) 통합 = 별도 cycle (libsignal_protocol_python wrap).
