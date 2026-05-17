# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) — 통합 테스트 패키지 (aiortc 실 통합)
#
# 본 디렉토리 의 모든 test = pytest marker `integration` 부착.
# 기본 pytest 실행 시 deselect (pyproject.toml `-m "not integration and not e2e"`).
# 명시 실행 = `pytest -m integration`.
#
# av wheel build = ffmpeg 의존 — macOS 의 `brew install ffmpeg` 의무.
