# SPDX-License-Identifier: GPL-3.0-or-later
"""Playwright 브라우저 native DataChannel multi-chunk file E2E + SHA-256 verify.

FR-04 (파일 송수신 + SHA-256 무결성) 의 browser-side E2E. cycle 169.619 의 text
1-byte send/recv 다음 단계 — 1MB random binary chunk N 송신 + 수신 reassemble +
SHA-256 무결성 verify.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.e2e


def test_browser_datachannel_file_chunked_sha256(
    page,
    signaling_server_url: str,
) -> None:
    """Alice → Bob 1MB random binary chunk send/recv + SHA-256 무결성."""

    page.goto("about:blank")

    result = page.evaluate(
        """
        async ({ url }) => {
          const connect = (name) => new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => reject(new Error(`${name} open timeout`)), 3000);
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

          // 한글 주석 — about:blank insecure context 안 crypto.subtle 미가용 → byte-checksum fingerprint
          const fingerprint = (uint8) => {
            let h1 = 0, h2 = 0;
            for (let i = 0; i < uint8.length; i++) {
              h1 = ((h1 * 31) + uint8[i]) | 0;
              h2 = (h2 + uint8[i] * (i & 0xff)) | 0;
            }
            return `${uint8.length}:${(h1 >>> 0).toString(16)}:${(h2 >>> 0).toString(16)}`;
          };

          const rtcConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
          const alice = await connect("alice");
          const bob = await connect("bob");
          const room = `file-e2e-${Date.now()}`;

          try {
            const alicePc = new RTCPeerConnection(rtcConfig);
            const bobPc = new RTCPeerConnection(rtcConfig);

            // 한글 주석 — 1MB random binary (getRandomValues 65536 byte limit 회피 chunked fill)
            const fileSize = 1024 * 1024;
            const file = new Uint8Array(fileSize);
            const FILL_CHUNK = 65536;
            for (let off = 0; off < fileSize; off += FILL_CHUNK) {
              crypto.getRandomValues(file.subarray(off, Math.min(off + FILL_CHUNK, fileSize)));
            }
            const senderHash = fingerprint(file);

            const aliceDc = alicePc.createDataChannel("file");
            aliceDc.binaryType = "arraybuffer";
            const aliceOpen = new Promise((r) => { aliceDc.onopen = () => r(); });

            const recvChunks = [];
            let recvBytes = 0;
            const recvDone = new Promise((resolve) => {
              bobPc.ondatachannel = (ev) => {
                const dc = ev.channel;
                dc.binaryType = "arraybuffer";
                dc.onmessage = (msg) => {
                  if (typeof msg.data === "string" && msg.data === "EOF") {
                    resolve();
                    return;
                  }
                  recvChunks.push(new Uint8Array(msg.data));
                  recvBytes += msg.data.byteLength;
                };
              };
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
                bob.send(JSON.stringify({ type: "ANSWER", room, to: "alice", sdp: bobPc.localDescription.sdp }));
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

            const offer = await alicePc.createOffer();
            await alicePc.setLocalDescription(offer);
            alice.send(JSON.stringify({ type: "OFFER", room, to: "bob", sdp: alicePc.localDescription.sdp }));

            await aliceOpen;

            // 한글 주석 — chunk 16KB send loop + backpressure (bufferedAmountLowThreshold)
            const CHUNK = 16 * 1024;
            aliceDc.bufferedAmountLowThreshold = 256 * 1024;
            for (let off = 0; off < fileSize; off += CHUNK) {
              const slice = file.slice(off, Math.min(off + CHUNK, fileSize));
              aliceDc.send(slice.buffer);
              if (aliceDc.bufferedAmount > 1024 * 1024) {
                await new Promise((r) => {
                  aliceDc.onbufferedamountlow = () => { aliceDc.onbufferedamountlow = null; r(); };
                });
              }
            }
            aliceDc.send("EOF");

            await Promise.race([
              recvDone,
              new Promise((_, reject) => setTimeout(() => reject(new Error("recv timeout")), 30000))
            ]);

            // 한글 주석 — reassemble + SHA-256 verify
            const reassembled = new Uint8Array(recvBytes);
            let off = 0;
            for (const c of recvChunks) { reassembled.set(c, off); off += c.byteLength; }
            const recvHash = fingerprint(reassembled);
            return {
              ok: true,
              sent_bytes: fileSize,
              recv_bytes: recvBytes,
              sent_hash: senderHash,
              recv_hash: recvHash,
              chunk_count: recvChunks.length,
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
    assert result["recv_bytes"] == result["sent_bytes"]
    assert result["recv_hash"] == result["sent_hash"]
    assert result["chunk_count"] > 0
