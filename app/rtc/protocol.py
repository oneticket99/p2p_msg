"""파일 전송 프로토콜 — 5종 메시지 정의 + 직렬화/역직렬화 헬퍼.

본 모듈은 ``app.rtc.file_sender`` 와 ``app.rtc.file_receiver`` 가 공유하는
순수 데이터 모델 + 변환 함수만 정의한다. 외부 IO 는 일절 수행하지 않는다.

프로토콜 개요 (송수신 양방향, DataChannel binary + text 혼합):

```
송신 → 수신 : FILE_META   (text JSON) — 파일 시작 알림 + 메타데이터
송신 → 수신 : FILE_CHUNK  (binary)    — 청크 본문 (file_id 16B + seq 4B + payload)
수신 → 송신 : FILE_ACK    (text JSON) — 주기적 진행률 확인
송신 → 수신 : FILE_END    (text JSON) — 모든 청크 송신 완료 알림
수신 → 송신 : FILE_DONE   (text JSON) — 수신 + 해시 검증 결과 회신
```

이미지 메시지는 별도 타입을 두지 않는다 — ``mime`` 가 ``image/*`` 이고
``thumbnail_base64`` 필드가 채워진 ``FILE_META`` 로 식별한다.

본 모듈에서 정의하는 상수·dataclass·함수만 ``send_str`` / ``send_bytes``
시점에 사용 가능하다. 발신 코드가 임의의 메시지 dict 를 만드는 것을 금지
한다 — BPE 호환성과 검증 일관성을 위해 반드시 본 모듈 헬퍼를 경유한다.
"""

from __future__ import annotations

import json
import struct
import uuid
from dataclasses import dataclass
from typing import Any, Final, Literal, Optional, TypedDict


# ---------------------------------------------------------------------------
# 메시지 타입 식별자 — 5종
# ---------------------------------------------------------------------------

MSG_FILE_META: Final[str] = "FILE_META"
MSG_FILE_CHUNK: Final[str] = "FILE_CHUNK"  # 바이너리 프레임 — type 필드 없음
MSG_FILE_ACK: Final[str] = "FILE_ACK"
MSG_FILE_END: Final[str] = "FILE_END"
MSG_FILE_DONE: Final[str] = "FILE_DONE"

# JSON 텍스트 프레임에서 허용되는 type 화이트리스트
TEXT_MSG_TYPES: Final[frozenset[str]] = frozenset(
    {MSG_FILE_META, MSG_FILE_ACK, MSG_FILE_END, MSG_FILE_DONE}
)


# ---------------------------------------------------------------------------
# 바이너리 청크 헤더 포맷 — file_id(16B uuid bytes) + seq(4B big-endian uint32)
# ---------------------------------------------------------------------------
#
# 헤더 총 20바이트. payload 는 그 뒤에 오는 바이트열 전체.
# ``struct`` 모듈 포맷 문자열: 16s I (big-endian 명시 위해 '!' prefix 사용)

_CHUNK_HEADER_FORMAT: Final[str] = "!16sI"
CHUNK_HEADER_SIZE: Final[int] = struct.calcsize(_CHUNK_HEADER_FORMAT)
assert CHUNK_HEADER_SIZE == 20, "청크 헤더 크기 불변식 위반"


# ---------------------------------------------------------------------------
# TypedDict 정의 — 와이어 포맷 검증용
# ---------------------------------------------------------------------------


class FileMetaMessage(TypedDict, total=False):
    """파일 시작 알림 (송신 → 수신).

    이미지인 경우 ``thumbnail_base64`` 가 채워지며, 일반 파일은 미정의.
    ``sha256`` 은 송신자가 산출한 전체 파일 해시 — 수신자가 검증한다.
    """

    type: Literal["FILE_META"]
    file_id: str
    name: str
    size: int
    mime: str
    total_chunks: int
    sha256: str
    # 이미지 한정 — base64 인코딩된 썸네일 PNG/JPEG 바이트
    thumbnail_base64: str


class FileAckMessage(TypedDict):
    """수신 진행률 확인 메시지 (수신 → 송신).

    ``received_bytes`` 는 누적 수신 바이트 수 (헤더 제외 payload 만).
    ``last_seq`` 는 마지막으로 수신 완료된 청크 seq 번호.
    """

    type: Literal["FILE_ACK"]
    file_id: str
    received_bytes: int
    last_seq: int


class FileEndMessage(TypedDict):
    """모든 청크 송신 완료 알림 (송신 → 수신)."""

    type: Literal["FILE_END"]
    file_id: str


class FileDoneMessage(TypedDict):
    """수신 + 해시 검증 결과 회신 (수신 → 송신).

    ``ok`` 는 파일 저장 성공 여부, ``hash_match`` 는 sha256 일치 여부.
    둘 다 ``True`` 일 때만 송신자는 송신 성공으로 처리한다.
    """

    type: Literal["FILE_DONE"]
    file_id: str
    ok: bool
    hash_match: bool


# ---------------------------------------------------------------------------
# dataclass — 파싱 결과 표현 (TypedDict 보다 메서드 사용이 편한 위치에서 사용)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FileMeta:
    """파싱된 FILE_META 컨테이너.

    Attributes
    ----------
    file_id : str
        UUID 문자열 형식 (hex 32자 또는 dashed 36자 둘 다 허용).
    name : str
        원본 파일명 (디렉토리 경로 제외).
    size : int
        전체 바이트 수.
    mime : str
        MIME 타입 (예: ``application/octet-stream``, ``image/png``).
    total_chunks : int
        예상 청크 수 — 수신자는 진행률 계산 보조용으로 사용.
    sha256 : str
        전체 파일 sha256 hex 문자열 (64자).
    thumbnail_base64 : str | None
        이미지일 때 base64 인코딩 썸네일. 일반 파일은 None.
    """

    file_id: str
    name: str
    size: int
    mime: str
    total_chunks: int
    sha256: str
    thumbnail_base64: Optional[str] = None

    def is_image(self) -> bool:
        """MIME 가 ``image/`` 로 시작하면 이미지로 판정."""

        return self.mime.lower().startswith("image/")


# ---------------------------------------------------------------------------
# 인코딩 / 디코딩 헬퍼
# ---------------------------------------------------------------------------


def new_file_id() -> str:
    """신규 file_id (UUID4 hex 32자) 생성.

    Returns
    -------
    str
        대시 없는 hex 32자 문자열. 바이너리 청크 헤더에 담을 때 ``bytes``
        16바이트로 다시 변환된다 — ``file_id_to_bytes`` 참조.
    """

    return uuid.uuid4().hex


def file_id_to_bytes(file_id: str) -> bytes:
    """``file_id`` 문자열을 16바이트 UUID raw 로 변환.

    Raises
    ------
    ValueError
        형식이 UUID hex 또는 dashed 가 아닌 경우.
    """

    return uuid.UUID(file_id).bytes


def file_id_from_bytes(raw: bytes) -> str:
    """UUID 16바이트 raw 를 hex 32자 문자열로 복원.

    Raises
    ------
    ValueError
        길이가 16 이 아닌 경우.
    """

    if len(raw) != 16:
        raise ValueError(
            f"UUID raw 길이 불일치 — len={len(raw)} (기대=16)"
        )
    return uuid.UUID(bytes=raw).hex


def encode_chunk(file_id: str, seq: int, payload: bytes) -> bytes:
    """청크 1개를 바이너리 프레임으로 직렬화.

    Parameters
    ----------
    file_id : str
        UUID hex 문자열.
    seq : int
        0부터 시작하는 단조증가 청크 번호 (0 ≤ seq < 2**32).
    payload : bytes
        청크 본문.

    Returns
    -------
    bytes
        ``header(20B) + payload`` 바이트 시퀀스. DataChannel ``send`` 로
        그대로 전송 가능.
    """

    if seq < 0 or seq >= (1 << 32):
        raise ValueError(f"seq 범위 초과 — seq={seq}")
    header = struct.pack(_CHUNK_HEADER_FORMAT, file_id_to_bytes(file_id), seq)
    return header + payload


def decode_chunk(frame: bytes) -> tuple[str, int, bytes]:
    """바이너리 청크 프레임을 (file_id, seq, payload) 로 분해.

    Returns
    -------
    tuple[str, int, bytes]
        - file_id (hex 32자)
        - seq (uint32)
        - payload (헤더 이후 바이트열, 비어 있을 수도 있음)

    Raises
    ------
    ValueError
        프레임 길이가 헤더 크기 미만인 경우.
    """

    if len(frame) < CHUNK_HEADER_SIZE:
        raise ValueError(
            f"청크 프레임 길이 부족 — len={len(frame)} "
            f"(최소 {CHUNK_HEADER_SIZE} 필요)"
        )
    raw_uuid, seq = struct.unpack(
        _CHUNK_HEADER_FORMAT, frame[:CHUNK_HEADER_SIZE]
    )
    payload = bytes(frame[CHUNK_HEADER_SIZE:])
    return file_id_from_bytes(raw_uuid), int(seq), payload


def build_file_meta(
    *,
    file_id: str,
    name: str,
    size: int,
    mime: str,
    total_chunks: int,
    sha256: str,
    thumbnail_base64: Optional[str] = None,
) -> dict[str, Any]:
    """``FILE_META`` 메시지 dict 빌더.

    이미지의 경우 호출자가 ``thumbnail_base64`` 를 채워 전달한다 —
    ``app.rtc.image_processor.make_thumbnail_base64`` 참조.

    Returns
    -------
    dict[str, Any]
        JSON 직렬화 준비 완료된 dict. ``encode_text`` 로 문자열화 가능.
    """

    msg: dict[str, Any] = {
        "type": MSG_FILE_META,
        "file_id": file_id,
        "name": name,
        "size": int(size),
        "mime": mime,
        "total_chunks": int(total_chunks),
        "sha256": sha256,
    }
    if thumbnail_base64:
        msg["thumbnail_base64"] = thumbnail_base64
    return msg


def build_file_ack(
    *, file_id: str, received_bytes: int, last_seq: int
) -> dict[str, Any]:
    """``FILE_ACK`` 메시지 dict 빌더."""

    return {
        "type": MSG_FILE_ACK,
        "file_id": file_id,
        "received_bytes": int(received_bytes),
        "last_seq": int(last_seq),
    }


def build_file_end(*, file_id: str) -> dict[str, Any]:
    """``FILE_END`` 메시지 dict 빌더."""

    return {"type": MSG_FILE_END, "file_id": file_id}


def build_file_done(
    *, file_id: str, ok: bool, hash_match: bool
) -> dict[str, Any]:
    """``FILE_DONE`` 메시지 dict 빌더."""

    return {
        "type": MSG_FILE_DONE,
        "file_id": file_id,
        "ok": bool(ok),
        "hash_match": bool(hash_match),
    }


def encode_text(msg: dict[str, Any]) -> str:
    """JSON 직렬화 — UTF-8 그대로(``ensure_ascii=False``).

    한글 파일명을 그대로 전달하기 위해 ascii escape 를 비활성화한다.
    """

    return json.dumps(msg, ensure_ascii=False)


def decode_text(raw: str) -> dict[str, Any]:
    """JSON 역직렬화 — dict 가 아니면 빈 dict 폴백.

    Raises
    ------
    ValueError
        JSON 파싱 실패 시.
    """

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"FILE_* JSON 파싱 실패 — err={exc}") from exc

    if not isinstance(parsed, dict):
        return {}
    return parsed


def parse_file_meta(payload: dict[str, Any]) -> FileMeta:
    """``FILE_META`` payload dict 를 ``FileMeta`` dataclass 로 변환.

    Raises
    ------
    KeyError
        필수 키 (file_id/name/size/mime/total_chunks/sha256) 누락 시.
    ValueError
        type 필드가 ``FILE_META`` 가 아닌 경우.
    """

    if payload.get("type") != MSG_FILE_META:
        raise ValueError(
            f"FILE_META 가 아닌 메시지로 parse_file_meta 호출 "
            f"— type={payload.get('type')!r}"
        )

    return FileMeta(
        file_id=str(payload["file_id"]),
        name=str(payload["name"]),
        size=int(payload["size"]),
        mime=str(payload["mime"]),
        total_chunks=int(payload["total_chunks"]),
        sha256=str(payload["sha256"]),
        thumbnail_base64=(
            str(payload["thumbnail_base64"])
            if payload.get("thumbnail_base64")
            else None
        ),
    )


def is_valid_text_type(value: Any) -> bool:
    """JSON 텍스트 메시지의 ``type`` 필드가 허용 화이트리스트에 있는지 검증."""

    return isinstance(value, str) and value in TEXT_MSG_TYPES
