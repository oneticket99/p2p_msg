# SPDX-License-Identifier: GPL-3.0-or-later
"""영상통화 (video track + signaling chain) browser E2E — cycle 169.668 신설.

사용자 directive — 잔존 E2E 확장 = video call (voice 패턴 확장).

chain:
1. Alice + Bob 의 RTCPeerConnection 신설 + video MediaStreamTrack 부착 (canvas captureStream)
2. Alice createOffer (video m-line 포함) → signaling relay → Bob ANSWER
3. Bob ontrack 안 video track 수신 verify
4. Alice close() + Bob close() = hangup → connectionState "closed" verify

cycle 169.659 의 buffered message + sticky listener 패턴 재사용.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.e2e


def test_browser_video_call_offer_answer_hangup(
    page,
    live_signaling_server_url: str,
) -> None:
    """Alice 의 video offer + Bob ANSWER + ontrack + close hangup."""

    page.goto(live_signaling_server_url.replace("ws://", "http://").replace("/ws", "/health"))

    result = page.evaluate(
        """
        async ({ url }) => {
          // 한글 주석 — buffered message + sticky listener (JOIN race 회수).
          const connect = (name) => new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            ws._buffer = [];
            ws._handlers = [];
            ws.addEventListener("message", (event) => {
              const msg = JSON.parse(event.data);
              ws._buffer.push(msg);
              ws._handlers.forEach((h) => h(msg));
            });
            const timer = setTimeout(() => reject(new Error(`${name} open timeout`)), 3000);
            ws.onopen = () => { clearTimeout(timer); resolve(ws); };
            ws.onerror = () => { clearTimeout(timer); reject(new Error(`${name} socket error`)); };
          });
          const waitForMessage = (ws, predicate, label) => new Promise((resolve, reject) => {
            const existing = ws._buffer.find(predicate);
            if (existing) return resolve(existing);
            const timer = setTimeout(() => reject(new Error(`${label} timeout`)), 5000);
            const handler = (msg) => {
              if (predicate(msg)) {
                clearTimeout(timer);
                ws._handlers = ws._handlers.filter((h) => h !== handler);
                resolve(msg);
              }
            };
            ws._handlers.push(handler);
          });

          const rtcConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
          const alice = await connect("alice");
          const bob = await connect("bob");
          const room = `video-${Date.now()}`;

          try {
            const alicePc = new RTCPeerConnection(rtcConfig);
            const bobPc = new RTCPeerConnection(rtcConfig);

            // 한글 주석 — canvas captureStream → video MediaStreamTrack (카메라 부재 환경 정합)
            const canvas = document.createElement("canvas");
            canvas.width = 16;
            canvas.height = 16;
            const cctx = canvas.getContext("2d");
            cctx.fillStyle = "red";
            cctx.fillRect(0, 0, 16, 16);
            // 한글 주석 — 1초 = 1 frame stream
            const stream = canvas.captureStream(1);
            const videoTrack = stream.getVideoTracks()[0];
            alicePc.addTrack(videoTrack, stream);

            // 한글 주석 — Bob ontrack handler — video track receive verify
            const trackReceived = new Promise((resolve) => {
              bobPc.ontrack = (ev) => resolve(ev.track.kind);
            });

            alicePc.onicecandidate = (e) => {
              if (e.candidate) alice.send(JSON.stringify({
                type: "ICE", room, to: "bob", candidate: e.candidate.toJSON()
              }));
            };
            bobPc.onicecandidate = (e) => {
              if (e.candidate) bob.send(JSON.stringify({
                type: "ICE", room, to: "alice", candidate: e.candidate.toJSON()
              }));
            };

            bob.addEventListener("message", async (ev) => {
              const m = JSON.parse(ev.data);
              if (m.type === "OFFER") {
                await bobPc.setRemoteDescription({ type: "offer", sdp: m.sdp });
                const a = await bobPc.createAnswer();
                await bobPc.setLocalDescription(a);
                bob.send(JSON.stringify({
                  type: "ANSWER", room, to: "alice", sdp: bobPc.localDescription.sdp
                }));
              } else if (m.type === "ICE" && m.candidate) {
                await bobPc.addIceCandidate(m.candidate);
              }
            });

            alice.addEventListener("message", async (ev) => {
              const m = JSON.parse(ev.data);
              if (m.type === "ANSWER") {
                await alicePc.setRemoteDescription({ type: "answer", sdp: m.sdp });
              } else if (m.type === "ICE" && m.candidate) {
                await alicePc.addIceCandidate(m.candidate);
              }
            });

            alice.send(JSON.stringify({ type: "JOIN", room, peer_id: "alice" }));
            bob.send(JSON.stringify({ type: "JOIN", room, peer_id: "bob" }));
            await waitForMessage(alice, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "alice JOIN");
            await waitForMessage(bob, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "bob JOIN");

            // 한글 주석 — alice createOffer (video m-line 포함)
            const offer = await alicePc.createOffer();
            await alicePc.setLocalDescription(offer);
            const has_video_offer = offer.sdp.includes("m=video");
            alice.send(JSON.stringify({
              type: "OFFER", room, to: "bob", sdp: alicePc.localDescription.sdp
            }));

            // 한글 주석 — bob video track receive (8s timeout)
            const recv_track_kind = await Promise.race([
              trackReceived,
              new Promise((_, reject) => setTimeout(() => reject(new Error("track timeout")), 8000))
            ]);

            // 한글 주석 — hangup
            alicePc.close();
            bobPc.close();

            return {
              ok: true,
              has_video_offer,
              recv_track_kind,
              alice_state: alicePc.connectionState,
              bob_state: bobPc.connectionState,
            };
          } finally {
            try { alice.close(); } catch (e) {}
            try { bob.close(); } catch (e) {}
          }
        }
        """,
        {"url": live_signaling_server_url},
    )
    assert result["ok"] is True
    assert result["has_video_offer"] is True
    assert result["recv_track_kind"] == "video"
    assert result["alice_state"] == "closed"
    assert result["bob_state"] == "closed"
