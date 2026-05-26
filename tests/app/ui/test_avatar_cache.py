# SPDX-License-Identifier: GPL-3.0-or-later
"""AvatarCache + make_avatar_pixmap 단위 test — cycle 169.852 M6 (T-16).

네트워크 없이 결정적 검증 — fetch 핸들러(`_on_fetched`)를 합성 PNG byte 로 직접 호출하고,
creds 부재 시 fetch 생략(이니셜 fallback) + seed_image hit + path traversal 방어를 cover.
실 서버 round-trip 은 G-final 사용자 ack 영역(headless 대체 불가).
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage

from app.ui._avatar_cache import _AvatarCache, avatar_cache
from app.ui._avatar_helper import make_avatar_pixmap

_VALID_REF = "avatars/" + ("a" * 64) + ".png"


def _png_bytes(color: int = 0x3366CC) -> bytes:
    # 한글 주석 — 합성 PNG byte (fetch 결과 모사)
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(color)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


@pytest.fixture
def cache(tmp_path, monkeypatch) -> _AvatarCache:
    # 한글 주석 — disk 캐시를 tmp 격리(실 media_cache 오염 차단)
    c = _AvatarCache()
    monkeypatch.setattr(c, "_cache_dir", tmp_path / "avatars")
    (tmp_path / "avatars").mkdir(parents=True, exist_ok=True)
    return c


def test_no_ref_returns_initials(qapp, cache) -> None:
    # 한글 주석 — avatar_ref 부재 → 이니셜 fallback (size 정합, 비 null)
    pm = cache.pixmap("홍원표", None, 48)
    assert not pm.isNull()
    assert pm.width() == 48
    assert cache.has(None) is False


def test_no_creds_skips_fetch(qapp, cache) -> None:
    # 한글 주석 — creds 부재(로그인 전/headless) → fetch 생략 + 이니셜 fallback
    pm = cache.pixmap("guest", _VALID_REF, 40)
    assert not pm.isNull()
    assert _VALID_REF not in cache._inflight
    assert cache.has(_VALID_REF) is False


def test_seed_image_hit_circular(qapp, cache) -> None:
    # 한글 주석 — seed_image → mem+disk 적재 → pixmap 원형 이미지 hit
    cache.seed_image(_VALID_REF, QImage(100, 100, QImage.Format.Format_RGB32))
    assert cache.has(_VALID_REF) is True
    pm = cache.pixmap("이름", _VALID_REF, 36)
    assert not pm.isNull()
    assert pm.width() == 36


def test_on_fetched_caches_and_emits(qapp, cache) -> None:
    # 한글 주석 — fetch 성공 핸들러 → mem 적재 + avatar_ready emit
    fired: list[str] = []
    cache.avatar_ready.connect(lambda ref: fired.append(ref))
    cache._on_fetched(True, _VALID_REF, _png_bytes())
    assert fired == [_VALID_REF]
    assert cache.has(_VALID_REF) is True
    assert _VALID_REF not in cache._inflight


def test_on_fetched_failure_no_emit(qapp, cache) -> None:
    # 한글 주석 — fetch 실패(ok=False/빈 data) → 미적재 + 미emit (graceful)
    fired: list[str] = []
    cache.avatar_ready.connect(lambda ref: fired.append(ref))
    cache._on_fetched(False, _VALID_REF, b"")
    cache._on_fetched(True, _VALID_REF, b"")
    assert fired == []
    assert cache.has(_VALID_REF) is False


def test_safe_name_whitelist(qapp, cache) -> None:
    # 한글 주석 — path traversal/부적합 ref → disk 파일명 거부(None)
    assert cache._safe_name(_VALID_REF) == ("a" * 64) + ".png"
    assert cache._safe_name("avatars/../../etc/passwd") is None
    assert cache._safe_name("avatars/evil.sh") is None
    assert cache._safe_name("avatars/" + ("a" * 64) + ".gif") is None


def test_maybe_fetch_dedup(qapp, cache, monkeypatch) -> None:
    # 한글 주석 — creds 주입 + 동일 ref 2회 → worker 1회만(중복 dedup)
    starts: list[str] = []

    class _FakeWorker:
        def __init__(self, *a, **k) -> None:
            self.finished_with_result = _Sig()
            self.finished = _Sig()

        def start(self) -> None:
            starts.append("start")

    class _Sig:
        def connect(self, *_a, **_k) -> None:
            pass

    monkeypatch.setattr("app.net.avatars_client.AvatarFetchWorker", _FakeWorker)
    cache.configure("http://demo:8765", "tok")
    cache._maybe_fetch(_VALID_REF)
    cache._maybe_fetch(_VALID_REF)
    assert starts == ["start"]
    assert _VALID_REF in cache._inflight


def test_make_avatar_pixmap_delegates(qapp) -> None:
    # 한글 주석 — public API → 싱글톤 위임 (no ref → 이니셜, size 정합)
    pm = make_avatar_pixmap("테스트", None, 48)
    assert not pm.isNull()
    assert pm.width() == 48
    assert avatar_cache() is avatar_cache()  # 싱글톤 동일성
