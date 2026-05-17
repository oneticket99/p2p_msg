"""파일 수신기 — 청크 누적 + 주기적 ACK + Qt progress 신호.

본 모듈은 수신자 입장의 파일 전송 흐름을 캡슐화한다:

1. ``FILE_META`` 도착 → 임시 파일 생성 + 메타 보관
2. ``FILE_CHUNK`` (바이너리) 도착 → seq/payload 분해 후 디스크에 append
3. 누적 ``received_bytes`` 가 ack 간격을 넘으면 ``FILE_ACK`` 회신
4. ``FILE_END`` 도착 → 해시 검증 + 최종 파일 이동 + ``FILE_DONE`` 회신

수신은 일반적으로 ``Peer.set_message_handler(text=..., binary=...)`` 로
본 수신기의 ``on_text_message`` / ``on_binary_message`` 를 주입해 동작
시킨다. 본 수신기는 송신자의 ``Peer`` 와 동일한 DataChannel 참조를 받아
``FILE_ACK`` / ``FILE_DONE`` 회신 송신에 사용한다.

신호:

- ``progress(file_id, received_bytes, total)`` : 수신 진행률
- ``completed(file_id, path, hash_match)``      : 수신 종료 (성공/실패 모두)
- ``error(file_id, message)``                    : 오류
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Final, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from app.core.config import Config
from app.rtc import protocol

try:  # aiortc 는 선택적 의존성 — 타입 힌트용으로만 import
    from aiortc import RTCDataChannel  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    RTCDataChannel = Any  # type: ignore[assignment, misc]

try:  # aiofiles 는 선택적 의존성 — 미설치 시 to_thread 폴백
    import aiofiles  # type: ignore[import-not-found]

    _AIOFILES_AVAILABLE = True
except ImportError:  # pragma: no cover
    aiofiles = None  # type: ignore[assignment]
    _AIOFILES_AVAILABLE = False


log = logging.getLogger(__name__)


# 환경변수 override 가능 — 256 KB 마다 ACK 송신
_DEFAULT_ACK_INTERVAL_BYTES: Final[int] = 256 * 1024


def _env_int(key: str, default: int, *, min_value: int = 1) -> int:
    """``os.environ`` 정수 읽기 — 빈/잘못된 값은 default 폴백."""

    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
        if parsed < min_value:
            raise ValueError(f"{key} < min_value({min_value})")
        return parsed
    except ValueError:
        log.warning(
            "%s 환경변수 정수 변환 실패 — raw=%r 기본값 %d 사용",
            key,
            raw,
            default,
        )
        return default


def _safe_filename(name: str) -> str:
    """파일명 안전 정규화 — 경로 분리자/널바이트 제거.

    수신한 ``name`` 이 임의 디렉토리 트래버설(예: ``../../etc/passwd``) 을
    하지 못하도록 ``os.path.basename`` 으로 디렉토리 분리자 제거 + 빈값
    폴백을 적용한다. 추가적인 sanitization 은 OS 별 ``Path`` 가 거부.
    """

    base = os.path.basename(name or "").strip()
    base = base.replace("\x00", "")
    if not base or base in {".", ".."}:
        return "untitled.bin"
    return base


class _ReceiveContext:
    """수신 중인 파일 1개의 진행 상태 컨테이너 (내부 전용).

    Attributes
    ----------
    meta : FileMeta
        FILE_META 로 받은 메타 (불변).
    temp_path : Path
        디스크에 누적 쓰는 임시 파일 경로 (``.partial``).
    received_bytes : int
        지금까지 디스크에 기록된 바이트 수.
    last_seq : int
        마지막으로 처리된 청크 seq 번호 (-1 = 아직 없음).
    digest : hashlib._Hash
        진행 중 sha256 (점진적 update).
    bytes_since_ack : int
        직전 ACK 이후 추가 수신한 바이트 — ack_interval_bytes 도달 시 회신.
    """

    __slots__ = (
        "meta",
        "temp_path",
        "received_bytes",
        "last_seq",
        "digest",
        "bytes_since_ack",
    )

    def __init__(self, meta: protocol.FileMeta, temp_path: Path) -> None:
        self.meta: protocol.FileMeta = meta
        self.temp_path: Path = temp_path
        self.received_bytes: int = 0
        self.last_seq: int = -1
        self.digest = hashlib.sha256()
        self.bytes_since_ack: int = 0


class FileReceiver(QObject):
    """파일 수신기 — DataChannel 메시지 디스패처 + 디스크 append.

    Notes
    -----
    - 동일 인스턴스가 다중 file_id 를 동시에 처리 가능 (각 file_id 마다
      ``_ReceiveContext`` 분리).
    - 디스크 IO 는 모두 비동기 (aiofiles 또는 to_thread).
    - 본 인스턴스는 Qt slot 에서 호출되어도 안전한 직렬 흐름을 가정한다
      (qasync 단일 루프).
    """

    # Qt 신호
    progress = pyqtSignal(str, int, int)
    completed = pyqtSignal(str, Path, bool)
    error = pyqtSignal(str, str)

    # 환경변수 키 (외부 노출용 상수)
    ENV_ACK_INTERVAL_BYTES = "FILE_ACK_INTERVAL_BYTES"
    ENV_DEST_DIR = "FILE_RECEIVE_DIR"

    def __init__(
        self,
        config: Config,
        *,
        dest_dir: Optional[Path] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """수신기 인스턴스 생성.

        Parameters
        ----------
        config : Config
            ``.env`` 로딩 결과 — ``media_cache_dir`` 을 기본 수신 디렉토리로 사용.
        dest_dir : Path | None
            명시적 수신 디렉토리. None 이면 ``FILE_RECEIVE_DIR`` 환경변수,
            그래도 비어 있으면 ``config.media_cache_dir``.
        parent : QObject | None
            Qt 상위 객체.
        """

        super().__init__(parent)

        # 수신 디렉토리 결정 — 환경변수 > 인자 > Config 우선순위로 구성
        env_dir = os.environ.get(self.ENV_DEST_DIR, "").strip()
        chosen = dest_dir or (Path(env_dir) if env_dir else Path(config.media_cache_dir))
        self._dest_dir: Path = chosen
        self._dest_dir.mkdir(parents=True, exist_ok=True)

        self._ack_interval_bytes: int = _env_int(
            self.ENV_ACK_INTERVAL_BYTES, _DEFAULT_ACK_INTERVAL_BYTES
        )

        # in-flight 수신 컨텍스트 — file_id → _ReceiveContext
        self._contexts: dict[str, _ReceiveContext] = {}

    # ------------------------------------------------------------------
    # public — 메시지 디스패치 진입점 (Peer.set_message_handler 가 주입)
    # ------------------------------------------------------------------

    @property
    def dest_dir(self) -> Path:
        """수신 파일이 최종 저장되는 디렉토리."""

        return self._dest_dir

    async def on_text_message(
        self, channel: "RTCDataChannel", payload: str
    ) -> None:
        """DataChannel 텍스트 프레임 — JSON 파싱 후 type 분기.

        ``FILE_META`` / ``FILE_END`` 만 처리. 그 외 type 은 무시 (송신자의
        ACK/DONE 은 본 수신기 책임이 아님 — sender 가 처리).
        """

        try:
            msg = protocol.decode_text(payload)
        except ValueError:
            log.warning("[FileReceiver] JSON 파싱 실패 — 무시")
            return

        msg_type = msg.get("type")
        if msg_type == protocol.MSG_FILE_META:
            await self._handle_file_meta(channel, msg)
        elif msg_type == protocol.MSG_FILE_END:
            await self._handle_file_end(channel, msg)
        else:
            log.debug(
                "[FileReceiver] 비대상 텍스트 메시지 — type=%r 무시", msg_type
            )

    async def on_binary_message(
        self, channel: "RTCDataChannel", frame: bytes
    ) -> None:
        """DataChannel 바이너리 프레임 — 청크 디코딩 + 디스크 append."""

        try:
            file_id, seq, payload = protocol.decode_chunk(frame)
        except ValueError as exc:
            log.warning("[FileReceiver] 청크 디코딩 실패 — %s", exc)
            return

        ctx = self._contexts.get(file_id)
        if ctx is None:
            log.warning(
                "[FileReceiver] 모르는 file_id 청크 — file_id=%s seq=%d (FILE_META 누락?)",
                file_id,
                seq,
            )
            return

        # 디스크 append (비동기)
        try:
            await self._append_payload(ctx, payload)
        except Exception as exc:
            self._fail(channel, file_id, f"청크 쓰기 실패 — {exc!s}")
            return

        ctx.last_seq = seq
        ctx.received_bytes += len(payload)
        ctx.bytes_since_ack += len(payload)

        # 진행률 신호 — UI 갱신
        total = ctx.meta.size
        self.progress.emit(file_id, ctx.received_bytes, total)

        # 누적 ACK 간격 도달 시 회신
        if ctx.bytes_since_ack >= self._ack_interval_bytes:
            ctx.bytes_since_ack = 0
            self._send_ack(channel, ctx)

    # ------------------------------------------------------------------
    # 내부 — FILE_META 처리
    # ------------------------------------------------------------------

    async def _handle_file_meta(
        self, channel: "RTCDataChannel", msg: dict[str, Any]
    ) -> None:
        """FILE_META 도착 — 임시 파일 생성 + 컨텍스트 등록."""

        try:
            meta = protocol.parse_file_meta(msg)
        except (KeyError, ValueError) as exc:
            log.warning("[FileReceiver] FILE_META 파싱 실패 — %s", exc)
            return

        if meta.file_id in self._contexts:
            log.warning(
                "[FileReceiver] 중복 FILE_META — file_id=%s 기존 컨텍스트 폐기",
                meta.file_id,
            )
            await self._discard_context(meta.file_id)

        # 임시 파일 생성 — ``.partial`` 접미사
        safe_name = _safe_filename(meta.name)
        temp_path = self._dest_dir / f"{meta.file_id}__{safe_name}.partial"
        try:
            # 빈 파일 미리 생성 (truncate=0)
            await asyncio.to_thread(temp_path.touch, exist_ok=True)
            await asyncio.to_thread(_truncate_file, temp_path)
        except Exception as exc:
            log.exception("[FileReceiver] 임시 파일 생성 실패 — path=%s", temp_path)
            self.error.emit(meta.file_id, f"임시 파일 생성 실패 — {exc!s}")
            return

        ctx = _ReceiveContext(meta=meta, temp_path=temp_path)
        self._contexts[meta.file_id] = ctx
        log.info(
            "[FileReceiver] FILE_META 수신 — file_id=%s name=%s size=%d "
            "mime=%s image=%s",
            meta.file_id,
            meta.name,
            meta.size,
            meta.mime,
            meta.is_image(),
        )
        # 0 진행률 즉시 발행 — UI 가 0% 막대 표시
        self.progress.emit(meta.file_id, 0, meta.size)

    # ------------------------------------------------------------------
    # 내부 — FILE_END 처리 + 해시 검증
    # ------------------------------------------------------------------

    async def _handle_file_end(
        self, channel: "RTCDataChannel", msg: dict[str, Any]
    ) -> None:
        """FILE_END 도착 — 해시 검증 + 최종 파일 이동 + FILE_DONE 회신."""

        file_id = str(msg.get("file_id") or "")
        ctx = self._contexts.get(file_id)
        if ctx is None:
            log.warning(
                "[FileReceiver] 모르는 file_id 의 FILE_END — file_id=%s", file_id
            )
            self._send_done(channel, file_id, ok=False, hash_match=False)
            return

        # 최종 ACK 1회 (이전 ACK 이후 잔여 바이트 모두 포함)
        if ctx.bytes_since_ack > 0:
            ctx.bytes_since_ack = 0
            self._send_ack(channel, ctx)

        # 해시 검증
        actual_hex = ctx.digest.hexdigest()
        hash_match = actual_hex.lower() == ctx.meta.sha256.lower()

        # 최종 파일 위치로 rename — 동일 이름 충돌 시 파일명 뒤에 (1), (2)...
        final_path: Optional[Path] = None
        ok = False
        try:
            final_path = await self._finalize_file(ctx)
            ok = True
        except Exception as exc:
            log.exception(
                "[FileReceiver] 최종 파일 생성 실패 — file_id=%s", file_id
            )
            self.error.emit(file_id, f"최종 파일 생성 실패 — {exc!s}")

        log.info(
            "[FileReceiver] FILE_END — file_id=%s ok=%s hash_match=%s path=%s",
            file_id,
            ok,
            hash_match,
            final_path,
        )
        self._send_done(channel, file_id, ok=ok, hash_match=hash_match)
        self._contexts.pop(file_id, None)

        # 결과 emit — final_path 가 None 이면 임시 경로라도 전달
        emit_path = final_path if final_path is not None else ctx.temp_path
        self.completed.emit(file_id, emit_path, hash_match and ok)

    async def _finalize_file(self, ctx: _ReceiveContext) -> Path:
        """``.partial`` 임시 파일을 최종 이름으로 rename.

        동일 이름이 이미 있으면 ``name (1).ext`` 패턴으로 충돌 회피.
        """

        safe_name = _safe_filename(ctx.meta.name)
        target = self._dest_dir / safe_name
        counter = 1
        stem, dot, suffix = safe_name.rpartition(".")
        while target.exists():
            if dot:
                candidate = f"{stem} ({counter}).{suffix}"
            else:
                candidate = f"{safe_name} ({counter})"
            target = self._dest_dir / candidate
            counter += 1

        await asyncio.to_thread(os.replace, str(ctx.temp_path), str(target))
        return target

    # ------------------------------------------------------------------
    # 내부 — 디스크 append (aiofiles 또는 to_thread)
    # ------------------------------------------------------------------

    async def _append_payload(
        self, ctx: _ReceiveContext, payload: bytes
    ) -> None:
        """청크 payload 를 임시 파일 끝에 append + 해시 update.

        호출자는 본 메서드 호출 후 ``received_bytes`` 를 갱신해야 한다 —
        본 메서드는 디스크 write 와 hash update 만 책임진다.
        """

        if _AIOFILES_AVAILABLE:
            async with aiofiles.open(ctx.temp_path, "ab") as fp:  # type: ignore[arg-type]
                await fp.write(payload)
        else:
            await asyncio.to_thread(_append_bytes_sync, ctx.temp_path, payload)
        # SHA-256 점진적 update — CPU bound 이긴 하나 청크당 비용 미미
        ctx.digest.update(payload)

    # ------------------------------------------------------------------
    # 내부 — ACK / DONE 송신
    # ------------------------------------------------------------------

    def _send_ack(
        self, channel: "RTCDataChannel", ctx: _ReceiveContext
    ) -> None:
        """``FILE_ACK`` 메시지 송신 — channel 비활성이면 로그만."""

        if getattr(channel, "readyState", "closed") != "open":
            log.debug("[FileReceiver] ACK 송신 생략 — channel 닫힘")
            return
        msg = protocol.build_file_ack(
            file_id=ctx.meta.file_id,
            received_bytes=ctx.received_bytes,
            last_seq=ctx.last_seq,
        )
        try:
            channel.send(protocol.encode_text(msg))
            log.debug(
                "[FileReceiver] FILE_ACK 송신 — file_id=%s received=%d last_seq=%d",
                ctx.meta.file_id,
                ctx.received_bytes,
                ctx.last_seq,
            )
        except Exception:
            log.exception("[FileReceiver] FILE_ACK 송신 실패")

    def _send_done(
        self,
        channel: "RTCDataChannel",
        file_id: str,
        *,
        ok: bool,
        hash_match: bool,
    ) -> None:
        """``FILE_DONE`` 메시지 송신 — channel 비활성이면 로그만."""

        if getattr(channel, "readyState", "closed") != "open":
            log.debug("[FileReceiver] DONE 송신 생략 — channel 닫힘")
            return
        msg = protocol.build_file_done(
            file_id=file_id, ok=ok, hash_match=hash_match
        )
        try:
            channel.send(protocol.encode_text(msg))
            log.info(
                "[FileReceiver] FILE_DONE 송신 — file_id=%s ok=%s hash_match=%s",
                file_id,
                ok,
                hash_match,
            )
        except Exception:
            log.exception("[FileReceiver] FILE_DONE 송신 실패")

    # ------------------------------------------------------------------
    # 내부 — 실패/취소 정리
    # ------------------------------------------------------------------

    def _fail(
        self, channel: "RTCDataChannel", file_id: str, message: str
    ) -> None:
        """수신 실패 — ``FILE_DONE`` ok=False + 컨텍스트 정리."""

        log.error("[FileReceiver] 수신 실패 — file_id=%s msg=%s", file_id, message)
        self.error.emit(file_id, message)
        self._send_done(channel, file_id, ok=False, hash_match=False)
        ctx = self._contexts.pop(file_id, None)
        if ctx is not None:
            try:
                ctx.temp_path.unlink(missing_ok=True)
            except Exception:
                log.exception(
                    "[FileReceiver] 임시 파일 삭제 실패 — path=%s", ctx.temp_path
                )

    async def _discard_context(self, file_id: str) -> None:
        """기존 컨텍스트를 폐기 — 임시 파일도 함께 삭제."""

        ctx = self._contexts.pop(file_id, None)
        if ctx is None:
            return
        try:
            await asyncio.to_thread(ctx.temp_path.unlink, missing_ok=True)
        except Exception:
            log.exception(
                "[FileReceiver] 임시 파일 삭제 실패 — path=%s", ctx.temp_path
            )


# ---------------------------------------------------------------------------
# 모듈 헬퍼 — to_thread 안에서 호출되는 동기 IO 함수
# ---------------------------------------------------------------------------


def _truncate_file(path: Path) -> None:
    """파일을 0 바이트로 truncate (동기 IO)."""

    with open(path, "wb") as fp:
        fp.truncate(0)


def _append_bytes_sync(path: Path, payload: bytes) -> None:
    """파일에 바이트열 append (동기 IO).

    반드시 ``asyncio.to_thread`` 안에서 호출돼야 한다 (정본 §E).
    """

    with open(path, "ab") as fp:
        fp.write(payload)
