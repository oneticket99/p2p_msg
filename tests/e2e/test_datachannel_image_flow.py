# SPDX-License-Identifier: GPL-3.0-or-later
"""Playwright 브라우저 DataChannel image binary + thumbnail header E2E.

FR-03 (이미지 송수신 + 썸네일 + 원본) 의 browser-side E2E. cycle 169.620 의 generic
1MB binary chunk verify 다음 단계 — image envelope (header JSON + thumbnail bytes +
원본 bytes) 의 multi-part chain.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.e2e


def test_browser_datachannel_image_header_thumb_full(
    page,
    signaling_server_url: str,
) -> None:
    """Alice → Bob image envelope: header JSON + 8KB thumbnail + 256KB 원본."""

    page.goto("about:blank")

    result = page.evaluate(
        """
        async ({ url }) => {
          const connect = (name) => new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => reject(new Error(`${name} timeout`)), 3000);
            ws.onopen = () => { clearTimeout(timer); resolve(ws); };
            ws.onerror = () => { clearTimeout(timer); reject(new Error(`${name} error`)); };
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
          const room = `img-e2e-${Date.now()}`;

          try {
            const alicePc = new RTCPeerConnection(rtcConfig);
            const bobPc = new RTCPeerConnection(rtcConfig);

            // 한글 주석 — image envelope = header JSON + thumbnail (8KB) + full (256KB)
            const thumbSize = 8 * 1024;
            const fullSize = 256 * 1024;
            const thumb = new Uint8Array(thumbSize);
            const full = new Uint8Array(fullSize);
            for (let i = 0; i < thumbSize; i += 65536) crypto.getRandomValues(thumb.subarray(i, Math.min(i + 65536, thumbSize)));
            for (let i = 0; i < fullSize; i += 65536) crypto.getRandomValues(full.subarray(i, Math.min(i + 65536, fullSize)));
            const header = JSON.stringify({ kind: "image", mime: "image/png", thumb_size: thumbSize, full_size: fullSize });

            const aliceDc = alicePc.createDataChannel("img");
            aliceDc.binaryType = "arraybuffer";
            const aliceOpen = new Promise((r) => { aliceDc.onopen = () => r(); });

            const recv = { header: null, thumb_bytes: 0, full_bytes: 0, phase: "header" };
            const recvDone = new Promise((resolve) => {
              bobPc.ondatachannel = (ev) => {
                const dc = ev.channel;
                dc.binaryType = "arraybuffer";
                dc.onmessage = (msg) => {
                  if (typeof msg.data === "string") {
                    if (recv.phase === "header") {
                      recv.header = JSON.parse(msg.data);
                      recv.phase = "thumb";
                    } else if (msg.data === "THUMB_EOF") {
                      recv.phase = "full";
                    } else if (msg.data === "FULL_EOF") {
                      resolve();
                    }
                    return;
                  }
                  if (recv.phase === "thumb") recv.thumb_bytes += msg.data.byteLength;
                  else if (recv.phase === "full") recv.full_bytes += msg.data.byteLength;
                };
              };
            });

            alicePc.onicecandidate = (e) => {
              if (e.candidate) alice.send(JSON.stringify({ type: "ICE", room, to: "bob", candidate: e.candidate.toJSON() }));
            };
            bobPc.onicecandidate = (e) => {
              if (e.candidate) bob.send(JSON.stringify({ type: "ICE", room, to: "alice", candidate: e.candidate.toJSON() }));
            };
            bob.addEventListener("message", async (ev) => {
              const m = JSON.parse(ev.data);
              if (m.type === "OFFER") {
                await bobPc.setRemoteDescription({ type: "offer", sdp: m.sdp });
                const a = await bobPc.createAnswer();
                await bobPc.setLocalDescription(a);
                bob.send(JSON.stringify({ type: "ANSWER", room, to: "alice", sdp: bobPc.localDescription.sdp }));
              } else if (m.type === "ICE" && m.candidate) {
                await bobPc.addIceCandidate(m.candidate);
              }
            });
            alice.addEventListener("message", async (ev) => {
              const m = JSON.parse(ev.data);
              if (m.type === "ANSWER") await alicePc.setRemoteDescription({ type: "answer", sdp: m.sdp });
              else if (m.type === "ICE" && m.candidate) await alicePc.addIceCandidate(m.candidate);
            });

            alice.send(JSON.stringify({ type: "JOIN", room, peer_id: "alice" }));
            bob.send(JSON.stringify({ type: "JOIN", room, peer_id: "bob" }));
            await waitForMessage(alice, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "alice JOIN");
            await waitForMessage(bob, (m) => m.type === "PEERS" || m.type === "PEER_JOINED", "bob JOIN");

            const offer = await alicePc.createOffer();
            await alicePc.setLocalDescription(offer);
            alice.send(JSON.stringify({ type: "OFFER", room, to: "bob", sdp: alicePc.localDescription.sdp }));

            await aliceOpen;
            const CHUNK = 16 * 1024;
            aliceDc.send(header);
            for (let off = 0; off < thumbSize; off += CHUNK) {
              aliceDc.send(thumb.slice(off, Math.min(off + CHUNK, thumbSize)).buffer);
            }
            aliceDc.send("THUMB_EOF");
            for (let off = 0; off < fullSize; off += CHUNK) {
              aliceDc.send(full.slice(off, Math.min(off + CHUNK, fullSize)).buffer);
            }
            aliceDc.send("FULL_EOF");

            await Promise.race([
              recvDone,
              new Promise((_, reject) => setTimeout(() => reject(new Error("recv timeout")), 20000))
            ]);
            return {
              ok: true,
              header_kind: recv.header.kind,
              header_mime: recv.header.mime,
              thumb_sent: thumbSize,
              thumb_recv: recv.thumb_bytes,
              full_sent: fullSize,
              full_recv: recv.full_bytes,
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
    assert result["header_kind"] == "image"
    assert result["header_mime"] == "image/png"
    assert result["thumb_recv"] == result["thumb_sent"]
    assert result["full_recv"] == result["full_sent"]
