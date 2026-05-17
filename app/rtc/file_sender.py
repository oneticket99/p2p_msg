"""파일 송신기 — 청크 스트리밍 + backpressure + Qt progress 신호.

본 모듈은 송신자 입장의 파일 전송 흐름을 캡슐화한다:

1. ``FILE_META`` 송신 (이미지인 경우 썸네일 base64 포함)
2. 파일을 청크 단위로 읽어 ``encode_chunk`` 로 직렬화 후 DataChannel 송신
3. ``bufferedAmount`` 가 high watermark 를 넘으면 low watermark 이하로
   떨어질 때까지 대기 (backpressure)
4. 모든 청크 송신 후 ``FILE_END`` 송신
5. 수신자의 ``FILE_DONE`` 도착 시 ``completed`` 신호 발행

신호 (Qt 슬롯에서 즉시 수신 가능):

- ``progress_sent(file_id, sent_bytes, total)``  : 송신 큐에 넣은 바이트
- ``progress_acked(file_id, acked_bytes, total)``: 수신자가 ACK 한 바이트
- ``completed(file_id, success)``                : 전체 흐름 종료 (DONE 수신)
- ``error(file_id, message)``                    : 오류 발생

UI 위젯 ``FileProgressWidget`` (role='send') 이 본 3 signal 의 슬롯이다.
``progress_sent`` 는 회색 막대(보낸 양), ``progress_acked`` 는 파란
막대(상대 확인) — 2-stack ProgressBar 시각 표현 정합.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
from pathlib import Path
from typing import Any, Final, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from app.rtc import protocol
from app.rtc.image_processor import (
    guess_mime,
    is_image_mime,
    make_thumbnail_base64,
)

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


# 기본값 — 환경변수 override 가능 (정본 §E)
_DEFAULT_CHUNK_SIZE: Final[int] = 16 * 1024
_DEFAULT_BUFFER_HIGH: Final[int] = 16 * 1024 * 1024
_DEFAULT_BUFFER_LOW: Final[int] = 4 * 1024 * 1024
_DEFAULT_BACKPRESSURE_POLL_MS: Final[int] = 50


def _env_int(key: str, default: int, *, min_value: int = 1) -> int:
    """``os.environ`` 에서 정수 읽기 — 빈/잘못된 값은 default 폴백.

    음수·0 차단을 위해 ``min_value`` 미만이면 default 로 폴백한다.
    """

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


class FileSender(QObject):
    """파일 송신기 — 청크 단위 + bufferedAmount backpressure 적용.

    Notes
    -----
    - 본 클래스는 1회 전송용으로 설계됐다. 다중 파일을 동시에 송신할 경우
      각 파일마다 인스턴스를 새로 만들거나 ``send`` 호출을 직렬화한다.
    - ``on_ack`` 는 외부(메시지 디스패처) 가 ``FILE_ACK`` 수신 시 호출해야
      한다 — 본 클래스 자체는 수신 루프를 보유하지 않는다.
    """

    # Qt 신호
    progress_sent = pyqtSignal(str, int, int)
    progress_acked = pyqtSignal(str, int, int)
    completed = pyqtSignal(str, bool)
    error = pyqtSignal(str, str)

    # 환경변수 키 (외부 노출용 상수)
    ENV_CHUNK_SIZE = "FILE_CHUNK_SIZE"
    ENV_BUFFER_HIGH = "FILE_BUFFER_HIGH"
    ENV_BUFFER_LOW = "FILE_BUFFER_LOW"

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """송신기 인스턴스 생성 — 환경변수에서 파라미터 적재."""

        super().__init__(parent)

        self._chunk_size: int = _env_int(self.ENV_CHUNK_SIZE, _DEFAULT_CHUNK_SIZE)
        self._buffer_high: int = _env_int(
            self.ENV_BUFFER_HIGH, _DEFAULT_BUFFER_HIGH
        )
        self._buffer_low: int = _env_int(
            self.ENV_BUFFER_LOW, _DEFAULT_BUFFER_LOW
        )
        # backpressure poll 주기 (ms) — 환경변수 override 가능
        self._backpressure_poll_ms: int = _env_int(
            "FILE_BACKPRESSURE_POLL_MS",
            _DEFAULT_BACKPRESSURE_POLL_MS,
        )

        # high < low 인 잘못된 환경변수 조합은 default 로 폴백 통일
        if self._buffer_low >= self._buffer_high:
            log.warning(
                "FILE_BUFFER_LOW(%d) >= FILE_BUFFER_HIGH(%d) — 기본값으로 폴백",
                self._buffer_low,
                self._buffer_high,
            )
            self._buffer_high = _DEFAULT_BUFFER_HIGH
            self._buffer_low = _DEFAULT_BUFFER_LOW

        # in-flight 진행 상태 — file_id → (path, size, total)
        self._in_flight: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    @property
    def chunk_size(self) -> int:
        """현재 청크 크기 (바이트). 환경변수 ``FILE_CHUNK_SIZE`` 로 override."""

        return self._chunk_size

    async def send(
        self,
        channel: "RTCDataChannel",
        path: Path,
        file_id: str,
        *,
        mime: Optional[str] = None,
    ) -> None:
        """파일을 DataChannel 로 송신 (FILE_META → CHUNK* → FILE_END).

        본 코루틴은 DataChannel ``send`` 큐에 모든 청크가 들어간 시점에
        반환된다. 수신자의 ``FILE_DONE`` 도착은 별도 흐름 — 외부 디스패처가
        ``on_done`` 을 호출하면 ``completed`` 신호가 발행된다.

        Parameters
        ----------
        channel : RTCDataChannel
            aiortc DataChannel 인스턴스 — 반드시 ``readyState == 'open'``.
        path : Path
            송신할 파일 경로.
        file_id : str
            UUID hex 32자 문자열 — ``protocol.new_file_id()`` 로 생성.
        mime : str | None
            MIME 타입. None 이면 확장자에서 자동 추측.

        Raises
        ------
        FileNotFoundError, ValueError, RuntimeError
            파일 미존재 / 빈 파일 / DataChannel 비활성 등.
        """

        if not path.exists():
            raise FileNotFoundError(f"송신할 파일이 없습니다 — path={path}")
        size = path.stat().st_size
        if size == 0:
            raise ValueError(f"빈 파일은 송신할 수 없습니다 — path={path}")
        if getattr(channel, "readyState", "closed") != "open":
            raise RuntimeError(
                f"DataChannel 이 open 상태가 아닙니다 — "
                f"readyState={getattr(channel, 'readyState', 'unknown')}"
            )

        resolved_mime = mime or guess_mime(path)
        total_chunks = max(1, math.ceil(size / self._chunk_size))

        # 1) SHA-256 해시 산출 (CPU bound — to_thread 경유)
        sha256 = await asyncio.to_thread(_sha256_of_file, path)

        # 2) 이미지면 썸네일 base64 도 함께 산출
        thumbnail_b64: Optional[str] = None
        if is_image_mime(resolved_mime):
            try:
                thumbnail_b64 = await make_thumbnail_base64(path)
            except Exception:
                # 썸네일 실패는 파일 전송 자체를 중단시키지 않는다 — 로그만
                log.exception(
                    "[FileSender] 썸네일 생성 실패 — 일반 파일로 진행 path=%s",
                    path,
                )

        # 3) FILE_META 송신
        meta = protocol.build_file_meta(
            file_id=file_id,
            name=path.name,
            size=size,
            mime=resolved_mime,
            total_chunks=total_chunks,
            sha256=sha256,
            thumbnail_base64=thumbnail_b64,
        )
        self._in_flight[file_id] = {
            "path": str(path),
            "size": size,
            "sent_bytes": 0,
        }
        try:
            channel.send(protocol.encode_text(meta))
            log.info(
                "[FileSender] FILE_META 송신 — file_id=%s name=%s size=%d "
                "total_chunks=%d image=%s",
                file_id,
                path.name,
                size,
                total_chunks,
                bool(thumbnail_b64),
            )
        except Exception as exc:
            self._fail(file_id, f"FILE_META 송신 실패 — {exc!s}")
            return

        # 4) 청크 스트리밍 — 백프레셔 적용
        try:
            await self._stream_chunks(channel, path, file_id, size)
        except asyncio.CancelledError:
            log.info("[FileSender] 송신 취소 — file_id=%s", file_id)
            self._fail(file_id, "송신 취소")
            raise
        except Exception as exc:
            self._fail(file_id, f"청크 송신 실패 — {exc!s}")
            return

        # 5) FILE_END 송신
        try:
            channel.send(protocol.encode_text(protocol.build_file_end(file_id=file_id)))
            log.info("[FileSender] FILE_END 송신 — file_id=%s", file_id)
        except Exception as exc:
            self._fail(file_id, f"FILE_END 송신 실패 — {exc!s}")

    def on_ack(self, file_id: str, received_bytes: int, last_seq: int) -> None:
        """수신자 ``FILE_ACK`` 도착 시 외부 디스패처가 호출.

        ``progress_acked`` 신호를 발행해 UI 가 파란(상대 확인) 막대를 갱신
        하도록 한다. ``last_seq`` 는 디버깅용으로만 사용 — UI 갱신은 누적
        바이트 수 기준.
        """

        info = self._in_flight.get(file_id)
        if info is None:
            log.debug(
                "[FileSender] 모르는 file_id 의 ACK — 무시 file_id=%s last_seq=%d",
                file_id,
                last_seq,
            )
            return
        total = int(info["size"])
        capped = min(int(received_bytes), total)
        self.progress_acked.emit(file_id, capped, total)

    def on_done(self, file_id: str, *, ok: bool, hash_match: bool) -> None:
        """수신자 ``FILE_DONE`` 도착 시 외부 디스패처가 호출.

        ``completed`` 신호를 발행하고 in-flight 엔트리를 제거한다.
        """

        info = self._in_flight.pop(file_id, None)
        success = bool(ok and hash_match)
        if info is None:
            log.debug(
                "[FileSender] 모르는 file_id 의 DONE — emit 만 진행 file_id=%s",
                file_id,
            )
        log.info(
            "[FileSender] FILE_DONE 수신 — file_id=%s ok=%s hash_match=%s",
            file_id,
            ok,
            hash_match,
        )
        self.completed.emit(file_id, success)

    # ------------------------------------------------------------------
    # 내부 — 청크 스트리밍 + backpressure
    # ------------------------------------------------------------------

    async def _stream_chunks(
        self,
        channel: "RTCDataChannel",
        path: Path,
        file_id: str,
        total_size: int,
    ) -> None:
        """파일을 청크로 읽어 DataChannel 에 송신.

        - ``aiofiles`` 가 설치돼 있으면 async file IO 사용
        - 미설치 시 ``asyncio.to_thread`` 로 동기 IO 를 워커 스레드에서 실행
        """

        seq = 0
        sent_bytes = 0

        if _AIOFILES_AVAILABLE:
            async with aiofiles.open(path, "rb") as fp:  # type: ignore[arg-type]
                while True:
                    payload = await fp.read(self._chunk_size)
                    if not payload:
                        break
                    await self._send_one_chunk(
                        channel, file_id, seq, payload
                    )
                    seq += 1
                    sent_bytes += len(payload)
                    self._in_flight[file_id]["sent_bytes"] = sent_bytes
                    self.progress_sent.emit(file_id, sent_bytes, total_size)
        else:
            # 동기 IO 폴백 — 전체 루프를 worker 스레드에서 돌리지 않고,
            # 한 번에 한 청크만 to_thread 로 읽어 backpressure 와 일관 유지.
            file_handle = await asyncio.to_thread(open, path, "rb")
            try:
                while True:
                    payload = await asyncio.to_thread(
                        file_handle.read, self._chunk_size
                    )
                    if not payload:
                        break
                    await self._send_one_chunk(
                        channel, file_id, seq, payload
                    )
                    seq += 1
                    sent_bytes += len(payload)
                    self._in_flight[file_id]["sent_bytes"] = sent_bytes
                    self.progress_sent.emit(file_id, sent_bytes, total_size)
            finally:
                await asyncio.to_thread(file_handle.close)

        log.info(
            "[FileSender] 청크 송신 완료 — file_id=%s sent=%d/%d chunks=%d",
            file_id,
            sent_bytes,
            total_size,
            seq,
        )

    async def _send_one_chunk(
        self,
        channel: "RTCDataChannel",
        file_id: str,
        seq: int,
        payload: bytes,
    ) -> None:
        """청크 1개 송신 + backpressure 대기.

        ``bufferedAmount`` 가 high watermark 초과면 low watermark 이하로
        떨어질 때까지 ``asyncio.sleep`` 으로 양보한다. aiortc 의
        bufferedAmount 는 OS sendmsg 큐가 비워지면 자동으로 감소한다.
        """

        # 송신 직전 backpressure 검사 — 이미 high 면 양보
        await self._wait_for_buffer_low(channel)

        frame = protocol.encode_chunk(file_id, seq, payload)
        channel.send(frame)

    async def _wait_for_buffer_low(self, channel: "RTCDataChannel") -> None:
        """``bufferedAmount`` 가 ``_buffer_low`` 이하로 떨어질 때까지 대기.

        - 폴링 주기는 환경변수 ``FILE_BACKPRESSURE_POLL_MS`` 로 조정 가능.
        - aiortc 가 ``bufferedAmount`` 를 노출하지 않는 환경(테스트 mock 등)
          에서는 ``getattr`` 폴백으로 0 처리 → 대기 없이 통과.
        """

        sleep_secs = max(0.001, self._backpressure_poll_ms / 1000.0)
        while True:
            buffered = int(getattr(channel, "bufferedAmount", 0) or 0)
            if buffered < self._buffer_high:
                # high watermark 미만이면 즉시 송신 가능
                return
            log.debug(
                "[FileSender] backpressure 대기 — buffered=%d high=%d low=%d",
                buffered,
                self._buffer_high,
                self._buffer_low,
            )
            # high 초과 상태 — low 이하로 내려갈 때까지 양보
            while True:
                await asyncio.sleep(sleep_secs)
                buffered = int(getattr(channel, "bufferedAmount", 0) or 0)
                if buffered <= self._buffer_low:
                    return

    # ------------------------------------------------------------------
    # 헬퍼 — 실패 처리
    # ------------------------------------------------------------------

    def _fail(self, file_id: str, message: str) -> None:
        """오류 발생 시 in-flight 정리 + error 신호 발행 + completed(False)."""

        log.error("[FileSender] 송신 실패 — file_id=%s msg=%s", file_id, message)
        self._in_flight.pop(file_id, None)
        self.error.emit(file_id, message)
        self.completed.emit(file_id, False)


# ---------------------------------------------------------------------------
# 모듈 헬퍼 — SHA-256 산출 (to_thread 안에서 실행됨)
# ---------------------------------------------------------------------------


def _sha256_of_file(path: Path) -> str:
    """파일 전체 sha256 hex 문자열 반환 (동기 IO).

    본 함수는 반드시 ``asyncio.to_thread`` 안에서 호출돼 이벤트 루프를
    막지 않도록 한다 (정본 §E).
    """

    digest = hashlib.sha256()
    chunk_size = 64 * 1024  # 해시 산출용 내부 청크 — DataChannel 청크와 무관
    with open(path, "rb") as fp:
        while True:
            block = fp.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()
