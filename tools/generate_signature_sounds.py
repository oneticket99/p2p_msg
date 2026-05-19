#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk signature sound — 6 chiptune WAV 생성 script (cycle 140 Phase 2 후속).

본 script 의 직접 실행 — `python3 tools/generate_signature_sounds.py`
산출물 — `app/sound/wav/tootalk_{ppyong,blip,ding,chime,pop,soft}.wav` 6 file.

외부 binary 부재 graceful — Python stdlib `wave` + `struct` + `math` 만 사용.
PyQt6.QtMultimedia QSoundEffect 호환 = mono 16-bit PCM 44.1kHz WAV 표준 format.

cycle 140 사용자 directive — placeholder 회수 + 8-bit retro chiptune 본격 생성.
"""

from __future__ import annotations

import argparse
import logging
import math
import struct
import sys
import wave
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# 한글 주석 — WAV format 표준 = mono 16-bit PCM 44.1kHz (QSoundEffect 호환)
SAMPLE_RATE = 44100
SAMPLE_WIDTH_BYTES = 2  # 16-bit
NUM_CHANNELS = 1  # mono
# 한글 주석 — 16-bit signed PCM max amplitude 의 80% (clipping 회피)
AMPLITUDE_MAX = int(0.8 * 32767)


def _envelope_ar(t: float, duration: float, attack: float = 0.01, release: float = 0.05) -> float:
    """한글 주석 — Attack-Release envelope — click 차단 + fade-out.

    t = 현재 시간 (초), duration = 전체 길이 (초).
    attack 구간 = 선형 fade-in, release 구간 = 선형 fade-out, 중간 = 1.0.
    """
    if t < attack:
        return t / attack
    if t > duration - release:
        return max(0.0, (duration - t) / release)
    return 1.0


def _envelope_decay(t: float, duration: float, attack: float = 0.005) -> float:
    """한글 주석 — Attack + exponential decay — ding / pop 류 의 자연 감쇠."""
    if t < attack:
        return t / attack
    # 한글 주석 — exponential decay 의 e^(-4t/duration) — duration 끝 ~= 2% 잔존
    return math.exp(-4.0 * (t - attack) / max(duration - attack, 1e-6))


def _envelope_sine_fade(t: float, duration: float) -> float:
    """한글 주석 — sine half-wave envelope — soft 류 의 부드러운 fade-in/out."""
    if duration <= 0:
        return 0.0
    # 한글 주석 — sin(pi * t/duration) — 0 → 1 → 0 의 매끄러운 종형
    return math.sin(math.pi * t / duration)


def _gen_sweep(
    freq_start: float,
    freq_end: float,
    duration: float,
    envelope: Callable[[float, float], float] = _envelope_ar,
) -> list[int]:
    """한글 주석 — 주파수 sweep tone — start → end Hz 선형 보간 + envelope.

    `ppyong` / `pop` 용 — sweep 의 chiptune retro 느낌.
    """
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[int] = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 한글 주석 — 선형 frequency 보간 + phase 누적 (불연속 차단)
        freq = freq_start + (freq_end - freq_start) * (t / duration)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        env = envelope(t, duration)
        value = int(AMPLITUDE_MAX * env * math.sin(phase))
        samples.append(max(-32767, min(32767, value)))
    return samples


def _gen_tone(
    freq: float,
    duration: float,
    envelope: Callable[[float, float], float] = _envelope_ar,
) -> list[int]:
    """한글 주석 — 단일 주파수 sine tone + envelope — blip / soft 용."""
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[int] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = envelope(t, duration)
        value = int(AMPLITUDE_MAX * env * math.sin(2.0 * math.pi * freq * t))
        samples.append(max(-32767, min(32767, value)))
    return samples


def _gen_harmonic(
    freqs: list[float],
    weights: list[float],
    duration: float,
    envelope: Callable[[float, float], float] = _envelope_decay,
) -> list[int]:
    """한글 주석 — 복수 주파수 harmonic mix + envelope — ding / chime 용.

    freqs = 주파수 list, weights = 각 주파수 amplitude 비중 (합 1.0 권장).
    """
    if len(freqs) != len(weights):
        raise ValueError("freqs / weights 의 길이 일치 의무")
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[int] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = envelope(t, duration)
        mixed = 0.0
        for f, w in zip(freqs, weights):
            mixed += w * math.sin(2.0 * math.pi * f * t)
        value = int(AMPLITUDE_MAX * env * mixed)
        samples.append(max(-32767, min(32767, value)))
    return samples


def _write_wav(path: Path, samples: list[int]) -> None:
    """한글 주석 — mono 16-bit PCM 44.1kHz WAV 의 stdlib wave 직접 기록."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(NUM_CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(SAMPLE_RATE)
        # 한글 주석 — signed 16-bit little-endian PCM frame 의 struct pack
        frames = b"".join(struct.pack("<h", s) for s in samples)
        wf.writeframes(frames)


def gen_ppyong() -> list[int]:
    """한글 주석 — ppyong (default) — 800Hz → 1200Hz sweep 300ms — TooTalk 시그니처."""
    return _gen_sweep(800.0, 1200.0, 0.300, envelope=_envelope_ar)


def gen_blip() -> list[int]:
    """한글 주석 — blip — 1000Hz 단음 200ms — 깔끔한 단음."""
    return _gen_tone(1000.0, 0.200, envelope=_envelope_ar)


def gen_ding() -> list[int]:
    """한글 주석 — ding — 1500Hz + 2000Hz harmonic 400ms decay — 종소리."""
    return _gen_harmonic(
        freqs=[1500.0, 2000.0],
        weights=[0.6, 0.4],
        duration=0.400,
        envelope=_envelope_decay,
    )


def gen_chime() -> list[int]:
    """한글 주석 — chime — 880Hz + 1320Hz 2 tone 300ms — 차임벨."""
    return _gen_harmonic(
        freqs=[880.0, 1320.0],
        weights=[0.5, 0.5],
        duration=0.300,
        envelope=_envelope_decay,
    )


def gen_pop() -> list[int]:
    """한글 주석 — pop — 200Hz → 600Hz sweep 150ms — 풍선 터지는 소리."""
    return _gen_sweep(200.0, 600.0, 0.150, envelope=_envelope_decay)


def gen_soft() -> list[int]:
    """한글 주석 — soft — 660Hz sine 250ms fade-in/out — 부드러운 알림."""
    return _gen_tone(660.0, 0.250, envelope=_envelope_sine_fade)


# 한글 주석 — 6 옵션 generator dispatch table (filename 의 SIGNATURE_OPTIONS 정합)
GENERATORS: dict[str, Callable[[], list[int]]] = {
    "tootalk_ppyong.wav": gen_ppyong,
    "tootalk_blip.wav": gen_blip,
    "tootalk_ding.wav": gen_ding,
    "tootalk_chime.wav": gen_chime,
    "tootalk_pop.wav": gen_pop,
    "tootalk_soft.wav": gen_soft,
}


def generate_all(out_dir: Path) -> dict[str, dict[str, float | int]]:
    """한글 주석 — 6 WAV 일괄 생성 + metadata 반환 (filename / size / duration / sample 수)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, float | int]] = {}
    for fname, gen in GENERATORS.items():
        samples = gen()
        path = out_dir / fname
        _write_wav(path, samples)
        size = path.stat().st_size
        duration = len(samples) / SAMPLE_RATE
        results[fname] = {
            "size_bytes": size,
            "duration_sec": round(duration, 4),
            "num_samples": len(samples),
        }
        log.info(
            "[gen] %s — size=%d bytes duration=%.3fs samples=%d",
            fname,
            size,
            duration,
            len(samples),
        )
    return results


def main(argv: list[str] | None = None) -> int:
    """한글 주석 — entry point — out-dir 인자 + 6 WAV 생성 + summary 출력."""
    parser = argparse.ArgumentParser(description="TooTalk signature sound 6 WAV 생성")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "app" / "sound" / "wav",
        help="WAV 산출 directory (default = app/sound/wav)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="상세 logging 출력",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    out_dir: Path = args.out_dir
    print(f"[gen] WAV 6 file 산출 directory = {out_dir}")
    results = generate_all(out_dir)
    print(f"[gen] 산출 완료 — {len(results)} file:")
    for fname, meta in results.items():
        print(
            f"  - {fname}: {meta['size_bytes']} bytes, "
            f"{meta['duration_sec']}s, {meta['num_samples']} samples"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
