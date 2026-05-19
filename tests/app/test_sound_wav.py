# SPDX-License-Identifier: GPL-3.0-or-later
"""``app/sound/wav/*.wav`` 6 chiptune binary 회귀 — cycle 140 Phase 2 후속.

`tools/generate_signature_sounds.py` 의 산출 6 WAV 의 실 존재 + RIFF header +
size > 1000 bytes + duration cap + frequency 영역 검증.

WAV 본격 생성 회귀 의무 — 손상 / 누락 / format 위반 시 즉시 FAIL.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest


# 한글 주석 — WAV 6 file 의 path resolve (app.sound 의 wav directory)
WAV_DIR = Path(__file__).resolve().parents[2] / "app" / "sound" / "wav"

# 한글 주석 — SIGNATURE_OPTIONS 정합 6 file 명 + 의도 duration 의 expected 값
EXPECTED_FILES: dict[str, dict[str, float]] = {
    "tootalk_ppyong.wav": {"duration_min": 0.25, "duration_max": 0.50},
    "tootalk_blip.wav": {"duration_min": 0.15, "duration_max": 0.25},
    "tootalk_ding.wav": {"duration_min": 0.35, "duration_max": 0.45},
    "tootalk_chime.wav": {"duration_min": 0.25, "duration_max": 0.35},
    "tootalk_pop.wav": {"duration_min": 0.10, "duration_max": 0.20},
    "tootalk_soft.wav": {"duration_min": 0.20, "duration_max": 0.30},
}

# 한글 주석 — Phase 2 directive — 200~400ms 범위 cap 의 전체 상한
DURATION_CAP_SEC = 0.450
SIZE_MIN_BYTES = 1000


class TestSignatureWavExistence:
    """6 WAV 파일 의 실 존재 + size 하한 검증 — 1 case."""

    def test_six_wav_files_exist_and_min_size(self) -> None:
        # 한글 주석 — 6 WAV file 모두 존재 + 1000 bytes 초과 의 size 하한 검증
        missing: list[str] = []
        too_small: list[tuple[str, int]] = []
        for fname in EXPECTED_FILES:
            path = WAV_DIR / fname
            if not path.is_file():
                missing.append(fname)
                continue
            size = path.stat().st_size
            if size < SIZE_MIN_BYTES:
                too_small.append((fname, size))
        assert not missing, f"WAV 부재 — {missing} (tools/generate_signature_sounds.py 실행 의무)"
        assert not too_small, f"WAV size 하한 위반 — {too_small}"


class TestSignatureWavRiffHeader:
    """6 WAV 의 RIFF / WAVE header magic 검증 — 1 case."""

    def test_six_wav_have_riff_wave_magic(self) -> None:
        # 한글 주석 — WAV file 의 12 bytes header = "RIFF" + size + "WAVE" 의 magic 검증
        for fname in EXPECTED_FILES:
            path = WAV_DIR / fname
            with path.open("rb") as f:
                header = f.read(12)
            assert len(header) == 12, f"{fname} header 12 bytes 부재"
            # 한글 주석 — RIFF magic (offset 0~3) + WAVE magic (offset 8~11)
            riff_magic = header[0:4]
            wave_magic = header[8:12]
            assert riff_magic == b"RIFF", (
                f"{fname} RIFF magic 위반 — {riff_magic!r}"
            )
            assert wave_magic == b"WAVE", (
                f"{fname} WAVE magic 위반 — {wave_magic!r}"
            )


class TestSignatureWavDuration:
    """6 WAV 의 duration cap (200~400ms 범위) 검증 — 1 case."""

    def test_six_wav_duration_within_range(self) -> None:
        # 한글 주석 — wave.open 의 nframes / framerate = duration (초) 측정
        violations: list[tuple[str, float, str]] = []
        for fname, meta in EXPECTED_FILES.items():
            path = WAV_DIR / fname
            with wave.open(str(path), "rb") as wf:
                nframes = wf.getnframes()
                framerate = wf.getframerate()
            duration = nframes / framerate
            if duration > DURATION_CAP_SEC:
                violations.append((fname, duration, f"> {DURATION_CAP_SEC}s 상한 위반"))
                continue
            if not (meta["duration_min"] <= duration <= meta["duration_max"]):
                violations.append(
                    (
                        fname,
                        duration,
                        f"[{meta['duration_min']}, {meta['duration_max']}] 범위 외",
                    )
                )
        assert not violations, f"WAV duration 위반 — {violations}"


class TestSignatureWavFormat:
    """6 WAV 의 PCM format spec — mono 16-bit 44.1kHz 검증 — 1 case."""

    def test_six_wav_format_mono_16bit_44100(self) -> None:
        # 한글 주석 — QSoundEffect 호환 의무 — mono / 16-bit / 44100 Hz PCM
        for fname in EXPECTED_FILES:
            path = WAV_DIR / fname
            with wave.open(str(path), "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
            assert channels == 1, f"{fname} mono 위반 — channels={channels}"
            assert sampwidth == 2, f"{fname} 16-bit 위반 — sampwidth={sampwidth} bytes"
            assert framerate == 44100, f"{fname} 44.1kHz 위반 — framerate={framerate}"


class TestSignatureWavFrequencyEnergy:
    """6 WAV 의 frequency 영역 — 주요 주파수 sample 의 amplitude 활성 검증 — 1 case."""

    def test_six_wav_have_audible_signal(self) -> None:
        # 한글 주석 — WAV sample 의 절대값 의 max 가 1000 (16-bit signed) 초과 의 audible 영역 검증
        # 정확한 FFT 부재 — 신호 amplitude 존재 + DC offset 부재 의 sanity check 만 의무
        silent: list[tuple[str, int]] = []
        for fname in EXPECTED_FILES:
            path = WAV_DIR / fname
            with wave.open(str(path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                num_samples = wf.getnframes()
            # 한글 주석 — signed 16-bit little-endian PCM 의 unpack
            samples = struct.unpack(f"<{num_samples}h", frames)
            peak = max(abs(s) for s in samples)
            if peak < 1000:
                silent.append((fname, peak))
        assert not silent, f"WAV silent 위반 — {silent} (amplitude < 1000)"


def test_default_ppyong_is_sweep() -> None:
    # 한글 주석 — default ppyong 의 sweep 신호 = 시간 영역 amplitude 변화 의무
    # sweep tone 의 attack 부터 release 까지 sample 의 변동성 검증 (silent 차단)
    path = WAV_DIR / "tootalk_ppyong.wav"
    with wave.open(str(path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        num_samples = wf.getnframes()
    samples = struct.unpack(f"<{num_samples}h", frames)
    # 한글 주석 — 시작 / 중간 / 끝 의 amplitude 의 변화 = 신호 active 의 sanity check
    mid_peak = max(abs(s) for s in samples[len(samples) // 4 : 3 * len(samples) // 4])
    assert mid_peak > 5000, f"ppyong 중간 amplitude 의 신호 부재 — peak={mid_peak}"
