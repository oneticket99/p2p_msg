#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 통화 사운드 WAV 생성 — cycle 169.91 신설.

사용자 directive 2026-05-20 — "통화 시에는 통화 연결음 사운드를 만들어야해".

산출:
    app/sound/wav/tootalk_ringback.wav     — outgoing 호출 ringback (4s loop)
    app/sound/wav/tootalk_ringtone.wav     — incoming 통화 ring (4s loop)
    app/sound/wav/tootalk_call_connect.wav — 통화 연결 신호 (0.3s)
    app/sound/wav/tootalk_call_end.wav     — 통화 종료 신호 (0.5s)

format = mono 16-bit PCM 44.1kHz (QSoundEffect 호환).
외부 binary 부재 graceful — Python stdlib wave + struct + math.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

# 한글 주석 — WAV format 표준 = mono 16-bit PCM 44.1kHz
SAMPLE_RATE = 44100
SAMPLE_WIDTH_BYTES = 2
NUM_CHANNELS = 1
AMPLITUDE_MAX = int(0.6 * 32767)  # 통화음 = signature sound 대비 음량 down


def _envelope_ramp(t: float, duration: float, fade: float = 0.02) -> float:
    """한글 주석 — fade-in/out 의 click 차단."""
    if t < fade:
        return t / fade
    if t > duration - fade:
        return max(0.0, (duration - t) / fade)
    return 1.0


def _silence(duration: float) -> list[int]:
    """한글 주석 — silence pad — ring cycle 안 off 구간."""
    return [0] * int(SAMPLE_RATE * duration)


def _gen_dual_tone(
    freq1: float,
    freq2: float,
    duration: float,
    weight1: float = 0.5,
    weight2: float = 0.5,
) -> list[int]:
    """한글 주석 — 2 tone mix (PSTN ringback 표준 440+480 또는 한국 1300Hz 등)."""
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[int] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = _envelope_ramp(t, duration)
        mixed = weight1 * math.sin(2 * math.pi * freq1 * t) + weight2 * math.sin(2 * math.pi * freq2 * t)
        value = int(AMPLITUDE_MAX * env * mixed)
        samples.append(max(-32767, min(32767, value)))
    return samples


def _gen_sweep(freq_start: float, freq_end: float, duration: float) -> list[int]:
    """한글 주석 — 주파수 sweep — connect/end 신호용."""
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[int] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = _envelope_ramp(t, duration)
        freq = freq_start + (freq_end - freq_start) * (t / duration)
        value = int(AMPLITUDE_MAX * env * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32767, min(32767, value)))
    return samples


def gen_ringback() -> list[int]:
    """한글 주석 — outgoing ringback — 한국 PSTN 표준 등가 (440+480Hz 1s on / 2s off pattern).

    총 4초 — 1s tone + 2s silence + 1s tone (loop friendly).
    """
    return (
        _gen_dual_tone(440.0, 480.0, 1.0)
        + _silence(2.0)
        + _gen_dual_tone(440.0, 480.0, 1.0)
    )


def gen_ringtone() -> list[int]:
    """한글 주석 — incoming ringtone — 따뜻한 2 tone chord (660+880Hz) pattern.

    0.4s on / 0.2s off / 0.4s on / 2s off — 총 ~3.0s loop.
    """
    return (
        _gen_dual_tone(660.0, 880.0, 0.4, 0.5, 0.5)
        + _silence(0.2)
        + _gen_dual_tone(660.0, 880.0, 0.4, 0.5, 0.5)
        + _silence(2.0)
    )


def gen_call_connect() -> list[int]:
    """한글 주석 — 통화 연결 — 600Hz → 1000Hz upward sweep 300ms (긍정 신호)."""
    return _gen_sweep(600.0, 1000.0, 0.300)


def gen_call_end() -> list[int]:
    """한글 주석 — 통화 종료 — 1000Hz → 400Hz downward sweep 500ms (종료 신호)."""
    return _gen_sweep(1000.0, 400.0, 0.500)


def _write_wav(path: Path, samples: list[int]) -> None:
    """한글 주석 — mono 16-bit PCM WAV 의 stdlib wave 의 직접 기록."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(NUM_CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(SAMPLE_RATE)
        frames = b"".join(struct.pack("<h", s) for s in samples)
        wf.writeframes(frames)


GENERATORS = {
    "tootalk_ringback.wav": gen_ringback,
    "tootalk_ringtone.wav": gen_ringtone,
    "tootalk_call_connect.wav": gen_call_connect,
    "tootalk_call_end.wav": gen_call_end,
}


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "app" / "sound" / "wav"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[gen_call_sounds] out_dir = {out_dir}")
    for fname, gen in GENERATORS.items():
        samples = gen()
        path = out_dir / fname
        _write_wav(path, samples)
        duration = len(samples) / SAMPLE_RATE
        size_kb = path.stat().st_size / 1024
        print(f"  {fname:30s} {duration:5.2f}s  {size_kb:7.1f}KB")


if __name__ == "__main__":
    main()
