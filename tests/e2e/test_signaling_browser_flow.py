# SPDX-License-Identifier: GPL-3.0-or-later
"""Playwright 브라우저 WebSocket 기반 원격 signaling E2E.

원격 테스트 서버(``114.207.112.73`` 기본값) 를 대상으로 브라우저 안 native
``WebSocket`` 두 개(Alice/Bob)가 JOIN/OFFER/ANSWER/ICE/LEAVE 흐름을 통과한다.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.e2e


def test_browser_websocket_join_offer_answer_ice_leave(
    page,
    live_signaling_server_url: str,
) -> None:
    """Alice/Bob 실제 브라우저 WebSocket 2개 의 원격 happy path 검증."""

    page.goto(live_signaling_server_url.replace("ws://", "http://").replace("/ws", "/health"))

    result = page.evaluate(
        """
        async ({ url }) => {
          const connect = (name) => new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => reject(new Error(`${name} open timeout`)), 3000);
            ws.onopen = () => {
              clearTimeout(timer);
              resolve(ws);
            };
            ws.onerror = () => {
              clearTimeout(timer);
              reject(new Error(`${name} socket error`));
            };
          });

          const waitForMessage = (ws, predicate, label) => new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error(`${label} timeout`)), 3000);
            const handler = (event) => {
              const msg = JSON.parse(event.data);
              if (predicate(msg)) {
                clearTimeout(timer);
                ws.removeEventListener("message", handler);
                resolve(msg);
              }
            };
            ws.addEventListener("message", handler);
          });

          const alice = await connect("alice");
          const bob = await connect("bob");
          const room = `browser-e2e-${Date.now()}`;

          try {
            const alicePeersPromise = waitForMessage(
              alice,
              (msg) => msg.type === "PEERS" && Array.isArray(msg.peers),
              "alice PEERS"
            );
            alice.send(JSON.stringify({ type: "JOIN", room, peer_id: "alice" }));
            const alicePeers = await alicePeersPromise;

            const aliceJoinedPromise = waitForMessage(
              alice,
              (msg) => msg.type === "PEER_JOINED" && msg.peer_id === "bob",
              "alice PEER_JOINED bob"
            );
            const bobPeersPromise = waitForMessage(
              bob,
              (msg) => msg.type === "PEERS" && msg.peers.includes("alice"),
              "bob PEERS alice"
            );
            bob.send(JSON.stringify({ type: "JOIN", room, peer_id: "bob" }));
            const [bobPeers, aliceJoined] = await Promise.all([
              bobPeersPromise,
              aliceJoinedPromise,
            ]);

            const bobOfferPromise = waitForMessage(
              bob,
              (msg) => msg.type === "OFFER" && msg.from === "alice" && msg.to === "bob",
              "bob OFFER"
            );
            alice.send(JSON.stringify({
              type: "OFFER",
              to: "bob",
              sdp: "v=0\\r\\no=- 0 0 IN IP4 127.0.0.1\\r\\n",
            }));
            const offer = await bobOfferPromise;

            const aliceAnswerPromise = waitForMessage(
              alice,
              (msg) => msg.type === "ANSWER" && msg.from === "bob" && msg.to === "alice",
              "alice ANSWER"
            );
            bob.send(JSON.stringify({
              type: "ANSWER",
              to: "alice",
              sdp: "v=0\\r\\no=- 1 1 IN IP4 127.0.0.1\\r\\n",
            }));
            const answer = await aliceAnswerPromise;

            const bobIcePromise = waitForMessage(
              bob,
              (msg) => msg.type === "ICE" && msg.from === "alice" && msg.to === "bob",
              "bob ICE"
            );
            alice.send(JSON.stringify({
              type: "ICE",
              to: "bob",
              candidate: {
                candidate: "candidate:0 1 udp 2122252543 127.0.0.1 9 typ host",
                sdpMid: "0",
                sdpMLineIndex: 0,
              },
            }));
            const ice = await bobIcePromise;

            const aliceLeftPromise = waitForMessage(
              alice,
              (msg) => msg.type === "PEER_LEFT" && msg.peer_id === "bob",
              "alice PEER_LEFT bob"
            );
            bob.send(JSON.stringify({ type: "LEAVE", room, peer_id: "bob" }));
            const left = await aliceLeftPromise;

            return {
              alicePeers: alicePeers.peers,
              bobPeers: bobPeers.peers,
              aliceJoinedPeer: aliceJoined.peer_id,
              offerFrom: offer.from,
              answerFrom: answer.from,
              iceCandidate: ice.candidate.candidate,
              leftPeer: left.peer_id,
            };
          } finally {
            alice.close();
            bob.close();
          }
        }
        """,
        {"url": live_signaling_server_url},
    )

    assert result["alicePeers"] == []
    assert result["bobPeers"] == ["alice"]
    assert result["aliceJoinedPeer"] == "bob"
    assert result["offerFrom"] == "alice"
    assert result["answerFrom"] == "bob"
    assert "candidate:" in result["iceCandidate"]
    assert result["leftPeer"] == "bob"


def test_browser_websocket_protocol_errors(
    page,
    live_signaling_server_url: str,
) -> None:
    """원격 브라우저 WebSocket 에서 protocol error 2종 의 ERROR envelope 검증."""

    page.goto(live_signaling_server_url.replace("ws://", "http://").replace("/ws", "/health"))

    result = page.evaluate(
        """
        async ({ url }) => {
          const ws = await new Promise((resolve, reject) => {
            const socket = new WebSocket(url);
            const timer = setTimeout(() => reject(new Error("open timeout")), 3000);
            socket.onopen = () => {
              clearTimeout(timer);
              resolve(socket);
            };
            socket.onerror = () => {
              clearTimeout(timer);
              reject(new Error("socket error"));
            };
          });

          const waitForError = (code) => new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error(`${code} timeout`)), 3000);
            const handler = (event) => {
              const msg = JSON.parse(event.data);
              if (msg.type === "ERROR" && msg.code === code) {
                clearTimeout(timer);
                ws.removeEventListener("message", handler);
                resolve(msg);
              }
            };
            ws.addEventListener("message", handler);
          });

          try {
            const unknownPromise = waitForError("UNKNOWN_TYPE");
            ws.send(JSON.stringify({ type: "HELLO", room: "r", peer_id: "x" }));
            const unknown = await unknownPromise;

            const notJoinedPromise = waitForError("NOT_JOINED");
            ws.send(JSON.stringify({ type: "OFFER", to: "bob", sdp: "v=0\\r\\n" }));
            const notJoined = await notJoinedPromise;

            return {
              unknownCode: unknown.code,
              notJoinedCode: notJoined.code,
              notJoinedMessage: notJoined.message,
            };
          } finally {
            ws.close();
          }
        }
        """,
        {"url": live_signaling_server_url},
    )

    assert result["unknownCode"] == "UNKNOWN_TYPE"
    assert result["notJoinedCode"] == "NOT_JOINED"
    assert "JOIN" in result["notJoinedMessage"]
