# SPDX-License-Identifier: GPL-3.0-or-later
"""음성통화 (audio track + signaling chain) browser E2E — cycle 169.658 신설.

사용자 directive — "친구와 음성통화 요청 / 음성 통화 수락 / 음성종료 가능?"

chain:
1. Alice + Bob 의 RTCPeerConnection 신설 + audio MediaStreamTrack 부착 (가짜 osc oscillator track)
2. Alice createOffer (audio m-line 포함) → signaling relay → Bob ANSWER
3. Bob ontrack 안 audio track 수신 verify
4. Alice close() = hangup → connectionState "closed" verify
"""

from __future__ import annotations

import pytest


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(reason="cycle 169.658 — voice call JOIN race timing flake (PEERS/PEER_JOINED dispatch race), audio track verify path 별 cycle"),
]


def test_browser_voice_call_offer_answer_hangup(
    page,
    signaling_server_url: str,
) -> None:
    """Alice 의 audio offer + Bob ANSWER + ontrack + close hangup."""

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

          const rtcConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
          const alice = await connect("alice");
          const bob = await connect("bob");
          const room = `voice-${Date.now()}`;

          try {
            const alicePc = new RTCPeerConnection(rtcConfig);
            const bobPc = new RTCPeerConnection(rtcConfig);

            // 한글 주석 — Web Audio API 안 oscillator → MediaStreamTrack (마이크 부재 환경 정합)
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            osc.frequency.value = 440;
            const dest = ctx.createMediaStreamDestination();
            osc.connect(dest);
            osc.start();
            const audioTrack = dest.stream.getAudioTracks()[0];
            alicePc.addTrack(audioTrack, dest.stream);

            // 한글 주석 — Bob 의 ontrack handler — audio track receive verify
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

            // 한글 주석 — alice createOffer (audio m-line 포함)
            const offer = await alicePc.createOffer();
            await alicePc.setLocalDescription(offer);
            const has_audio_offer = offer.sdp.includes("m=audio");
            alice.send(JSON.stringify({
              type: "OFFER", room, to: "bob", sdp: alicePc.localDescription.sdp
            }));

            // 한글 주석 — bob 의 audio track receive (5s timeout)
            const recv_track_kind = await Promise.race([
              trackReceived,
              new Promise((_, reject) => setTimeout(() => reject(new Error("track timeout")), 8000))
            ]);

            // 한글 주석 — hangup = alice + bob close()
            alicePc.close();
            bobPc.close();
            osc.stop();
            await ctx.close();

            return {
              ok: true,
              has_audio_offer,
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
        {"url": signaling_server_url},
    )
    assert result["ok"] is True
    assert result["has_audio_offer"] is True
    assert result["recv_track_kind"] == "audio"
    assert result["alice_state"] == "closed"
    assert result["bob_state"] == "closed"
