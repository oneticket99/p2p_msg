# SPDX-License-Identifier: GPL-3.0-or-later
"""Playwright 브라우저 native ``RTCPeerConnection`` + DataChannel E2E.

cycle 169.617 의 aiortc python-only direct bench 다음 단계. 브라우저 2 context
(Alice + Bob) 안 native ``RTCPeerConnection`` 의 SDP offer/answer + DataChannel
"hello" send/recv chain 검증. FR-02 (text DataChannel send/recv) 정합.

원격 signaling server (``114.207.112.73:8765``) 경유 OFFER/ANSWER/ICE relay.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.e2e


def test_browser_datachannel_offer_answer_recv(
    page,
    signaling_server_url: str,
) -> None:
    """Alice 의 createOffer + Bob 의 createAnswer + DataChannel "hello" → "world" 왕복."""

    page.goto("about:blank")

    result = page.evaluate(
        """
        async ({ url }) => {
          const connect = (name) => new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => reject(new Error(`${name} open timeout`)), 3000);
            ws.onopen = () => { clearTimeout(timer); resolve(ws); };
            ws.onerror = () => { clearTimeout(timer); reject(new Error(`${name} socket error`)); };
          });

          const waitForMessage = (ws, predicate, label) => new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error(`${label} timeout`)), 5000);
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

          // 한글 주석 — RTC config STUN 만 (TURN 부재 환경 정합).
          const rtcConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
          const alice = await connect("alice");
          const bob = await connect("bob");
          const room = `dc-e2e-${Date.now()}`;

          try {
            const alicePc = new RTCPeerConnection(rtcConfig);
            const bobPc = new RTCPeerConnection(rtcConfig);

            // 한글 주석 — alice → bob DataChannel
            const aliceDc = alicePc.createDataChannel("chat");
            const aliceOpen = new Promise((resolve) => { aliceDc.onopen = () => resolve(); });
            const aliceMsgPromise = new Promise((resolve) => {
              aliceDc.onmessage = (e) => resolve(e.data);
            });

            const bobDcPromise = new Promise((resolve) => {
              bobPc.ondatachannel = (ev) => {
                const dc = ev.channel;
                dc.onmessage = (msg) => {
                  if (msg.data === "hello") dc.send("world");
                };
                resolve(dc);
              };
            });

            // 한글 주석 — ICE candidate relay chain
            alicePc.onicecandidate = (ev) => {
              if (ev.candidate) {
                alice.send(JSON.stringify({
                  type: "ICE", room, to: "bob", candidate: ev.candidate.toJSON()
                }));
              }
            };
            bobPc.onicecandidate = (ev) => {
              if (ev.candidate) {
                bob.send(JSON.stringify({
                  type: "ICE", room, to: "alice", candidate: ev.candidate.toJSON()
                }));
              }
            };

            // 한글 주석 — bob ws 안 OFFER/ICE 수신 chain
            bob.addEventListener("message", async (ev) => {
              const msg = JSON.parse(ev.data);
              if (msg.type === "OFFER") {
                await bobPc.setRemoteDescription({ type: "offer", sdp: msg.sdp });
                const answer = await bobPc.createAnswer();
                await bobPc.setLocalDescription(answer);
                bob.send(JSON.stringify({
                  type: "ANSWER", room, to: "alice", sdp: bobPc.localDescription.sdp
                }));
              } else if (msg.type === "ICE" && msg.candidate) {
                await bobPc.addIceCandidate(msg.candidate);
              }
            });

            // 한글 주석 — alice ws 안 ANSWER/ICE 수신 chain
            alice.addEventListener("message", async (ev) => {
              const msg = JSON.parse(ev.data);
              if (msg.type === "ANSWER") {
                await alicePc.setRemoteDescription({ type: "answer", sdp: msg.sdp });
              } else if (msg.type === "ICE" && msg.candidate) {
                await alicePc.addIceCandidate(msg.candidate);
              }
            });

            // 한글 주석 — JOIN room (alice/bob)
            alice.send(JSON.stringify({ type: "JOIN", room, peer_id: "alice" }));
            bob.send(JSON.stringify({ type: "JOIN", room, peer_id: "bob" }));
            await waitForMessage(alice, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "alice JOIN");
            await waitForMessage(bob, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "bob JOIN");

            // 한글 주석 — alice createOffer + 송신
            const offer = await alicePc.createOffer();
            await alicePc.setLocalDescription(offer);
            alice.send(JSON.stringify({
              type: "OFFER", room, to: "bob", sdp: alicePc.localDescription.sdp
            }));

            // 한글 주석 — DataChannel open + send "hello" + recv "world" 왕복
            await aliceOpen;
            await bobDcPromise;
            aliceDc.send("hello");
            const reply = await Promise.race([
              aliceMsgPromise,
              new Promise((_, reject) => setTimeout(() => reject(new Error("recv timeout")), 8000))
            ]);
            return { ok: true, reply };
          } finally {
            try { alice.close(); } catch (e) {}
            try { bob.close(); } catch (e) {}
          }
        }
        """,
        {"url": signaling_server_url},
    )
    assert result["ok"] is True
    assert result["reply"] == "world"
