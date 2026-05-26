# SPDX-License-Identifier: GPL-3.0-or-later
"""AvatarCache — avatar_ref 이미지의 memory+disk 캐시 + async fetch (cycle 169.852 M6, T-16).

표시 전파(6곳 — chat sender / drawer header / profile / group / channel / member_list)의 source.
avatar_ref(서버 content-addressed ``"avatars/<sha256>.<ext>"``)는 ``AvatarFetchWorker``(QThread)
로만 받을 수 있어 동기 렌더가 불가하다. 본 싱글톤이 그 간극을 메운다:

- 메모리(QImage) + disk(``<media_cache_dir>/avatars/``) 2단 캐시로 hit 시 즉시 제공.
- miss 시 1회만 async fetch(같은 ref 중복 요청은 dedup) → 저장 + ``avatar_ready(avatar_ref)`` emit.
- 위젯은 signal 을 구독해 자신의 ref 와 일치할 때만 재렌더(progressive enhancement, UI 블로킹 0).
- creds(base_url/token) 부재(로그인 전·headless) 면 fetch 를 생략하고 이니셜 fallback 으로 무손상 degrade.

avatar_ref 가 sha256 content-address 라 내용 변경 = ref 변경 → 캐시 무효화 로직이 필요 없다(불변 키).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPixmap

from app.ui._avatar_helper import make_initial_pixmap

# 한글 주석 — disk 캐시 파일명 화이트리스트(content-address sha + 확장자만 허용, path traversal 방어)
_SAFE_NAME = re.compile(r"\A[0-9a-fA-F]{8,64}\.(png|jpg|jpeg)\Z")


def _circular_from_image(image: QImage, size: int) -> QPixmap:
    """QImage → center 정사각 crop + size 다운스케일 + 원형 clip pixmap.

    picker 의 원형 preview 와 동일 규약(QPainterPath ellipse clip). 표시 site 공통 렌더.
    """
    width, height = image.width(), image.height()
    side = min(width, height) if width and height else 1
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = image.copy(left, top, side, side).scaled(
        size,
        size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawImage(0, 0, cropped)
    painter.end()
    return out


class _AvatarCache(QObject):
    """avatar_ref 이미지 memory+disk 캐시 + async fetch 싱글톤."""

    # 한글 주석 — fetch 완료(disk/mem 적재)된 avatar_ref — 위젯이 구독해 재렌더
    avatar_ready = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._base_url: str = ""
        self._token: str = ""
        self._mem: dict[str, QImage] = {}
        self._inflight: set[str] = set()
        self._workers: dict[str, object] = {}  # ref → QThread retain(GC 방지)
        self._disk_miss: set[str] = set()  # disk 부재 확인된 ref(반복 stat 방지, reviewer MEDIUM-1)
        self._cache_dir: Optional[Path] = None

    # ------------------------------------------------------------------
    # 설정 + 경로
    # ------------------------------------------------------------------

    def configure(self, base_url: str, token: str) -> None:
        """로그인 후 fetch creds 주입(이후 miss 시 async fetch 활성)."""

        self._base_url = base_url or ""
        self._token = token or ""
        # 한글 주석 — creds 변경 시 disk-miss negative 캐시 초기화(늦게 도착한 creds 로 retry 허용)
        self._disk_miss.clear()

    def _dir(self) -> Path:
        """disk 캐시 디렉토리(<media_cache_dir>/avatars/) — 최초 사용 시 생성."""

        if self._cache_dir is None:
            try:
                from app.core.config import load_config

                base = Path(load_config().media_cache_dir)
            except Exception:  # noqa: BLE001 - config 부재 시 상대 경로 fallback
                base = Path("./media_cache")
            self._cache_dir = base / "avatars"
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        return self._cache_dir

    @staticmethod
    def _safe_name(avatar_ref: str) -> Optional[str]:
        """avatar_ref → disk 파일명(basename, 화이트리스트 통과만). 부적합 None."""

        name = avatar_ref.rsplit("/", 1)[-1]
        return name if _SAFE_NAME.match(name) else None

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def pixmap(self, name: str, avatar_ref: Optional[str], size: int) -> QPixmap:
        """표시용 원형 pixmap — 캐시 hit 시 이미지, miss/부재 시 이니셜 fallback.

        avatar_ref 가 있고 캐시 miss 면 1회 async fetch 를 trigger 하고, 그 사이에는
        이니셜 pixmap 을 돌려준다. fetch 완료 시 ``avatar_ready`` 가 emit 돼 위젯이 재렌더.
        """
        if not avatar_ref:
            return make_initial_pixmap(name or "?", size=size)

        cached = self._mem.get(avatar_ref)
        if cached is None and avatar_ref not in self._disk_miss:
            cached = self._load_disk(avatar_ref)
        if cached is not None and not cached.isNull():
            return _circular_from_image(cached, size)

        # 한글 주석 — miss → async fetch trigger(creds 있을 때만) 후 이니셜 fallback
        self._maybe_fetch(avatar_ref)
        return make_initial_pixmap(name or "?", size=size)

    def has(self, avatar_ref: Optional[str]) -> bool:
        """해당 ref 이미지가 즉시 렌더 가능(mem/disk hit)한지."""

        if not avatar_ref:
            return False
        if avatar_ref in self._mem:
            return True
        if avatar_ref in self._disk_miss:
            return False  # 한글 주석 — disk 부재 확인됨(반복 stat 생략)
        return self._load_disk(avatar_ref) is not None

    def seed_image(self, avatar_ref: str, image: QImage) -> None:
        """업로드 직후 등 외부에서 얻은 이미지를 캐시에 즉시 적재(round-trip 절약)."""

        if avatar_ref and image is not None and not image.isNull():
            self._mem[avatar_ref] = image
            self._disk_miss.discard(avatar_ref)
            self._save_disk(avatar_ref, image)

    # ------------------------------------------------------------------
    # 내부 — disk I/O + fetch
    # ------------------------------------------------------------------

    def _load_disk(self, avatar_ref: str) -> Optional[QImage]:
        """disk 캐시 → QImage(있으면 mem 승격). 부재/실패 None."""

        safe = self._safe_name(avatar_ref)
        if safe is None:
            return None
        path = self._dir() / safe
        if not path.exists():
            self._disk_miss.add(avatar_ref)  # 한글 주석 — disk 부재 기록(반복 stat 방지)
            return None
        image = QImage(str(path))
        if image.isNull():
            self._disk_miss.add(avatar_ref)
            return None
        self._mem[avatar_ref] = image
        self._disk_miss.discard(avatar_ref)
        return image

    def _save_disk(self, avatar_ref: str, image: QImage) -> None:
        """QImage → disk 캐시(파일명 화이트리스트 통과 시)."""

        safe = self._safe_name(avatar_ref)
        if safe is None:
            return
        try:
            image.save(str(self._dir() / safe))
        except Exception:  # noqa: BLE001 - 캐시 쓰기 실패는 표시에 무영향
            pass

    def _maybe_fetch(self, avatar_ref: str) -> None:
        """creds 있고 in-flight 아니면 AvatarFetchWorker 1회 기동(중복 dedup)."""

        if not self._base_url or not self._token:
            return  # 한글 주석 — 로그인 전·headless → fetch 생략(이니셜 유지)
        if avatar_ref in self._inflight:
            return
        from app.net.avatars_client import AvatarFetchWorker

        worker = AvatarFetchWorker(self._base_url, self._token, avatar_ref, self)
        worker.finished_with_result.connect(self._on_fetched)
        worker.finished.connect(lambda r=avatar_ref: self._cleanup_worker(r))
        self._inflight.add(avatar_ref)
        self._workers[avatar_ref] = worker
        worker.start()

    def _on_fetched(self, ok: bool, avatar_ref: str, data: bytes) -> None:
        """fetch 결과 — 성공 시 mem+disk 적재 후 avatar_ready emit."""

        self._inflight.discard(avatar_ref)
        if not ok or not data:
            return
        image = QImage()
        if not image.loadFromData(data):
            return
        self._mem[avatar_ref] = image
        self._disk_miss.discard(avatar_ref)
        self._save_disk(avatar_ref, image)
        self.avatar_ready.emit(avatar_ref)

    def _cleanup_worker(self, avatar_ref: str) -> None:
        """worker 종료 시 retain 해제(메모리 누수 방지)."""

        self._inflight.discard(avatar_ref)
        worker = self._workers.pop(avatar_ref, None)
        if worker is not None:
            try:
                worker.deleteLater()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass


# 한글 주석 — 프로세스 단일 인스턴스(QApplication 생애주기와 동행)
_INSTANCE: Optional[_AvatarCache] = None


def avatar_cache() -> _AvatarCache:
    """AvatarCache 싱글톤 접근자."""

    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = _AvatarCache()
    return _INSTANCE
