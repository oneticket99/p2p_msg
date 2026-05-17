# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.rtc.protocol`` 단위 테스트.

qa-agent 사이클 13 의 정적 검증 케이스 20건 의 실 pytest 회수.

테스트 범위:
- ``CHUNK_HEADER_SIZE`` 불변식 (20 byte)
- ``new_file_id`` / ``file_id_to_bytes`` / ``file_id_from_bytes`` round-trip
- ``encode_chunk`` / ``decode_chunk`` round-trip (정상 + 경계 + 예외)
- ``build_file_meta`` / ``build_file_ack`` / ``build_file_end`` / ``build_file_done`` 필드 정합
- ``encode_text`` / ``decode_text`` JSON round-trip + 한글 fname 보존
- ``parse_file_meta`` dataclass 변환 + 예외
- ``is_valid_text_type`` 화이트리스트
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.rtc.protocol import (
    CHUNK_HEADER_SIZE,
    MSG_FILE_ACK,
    MSG_FILE_DONE,
    MSG_FILE_END,
    MSG_FILE_META,
    FileMeta,
    build_file_ack,
    build_file_done,
    build_file_end,
    build_file_meta,
    decode_chunk,
    decode_text,
    encode_chunk,
    encode_text,
    file_id_from_bytes,
    file_id_to_bytes,
    is_valid_text_type,
    new_file_id,
    parse_file_meta,
)


# ---------------------------------------------------------------------------
# 1. 헤더 불변식
# ---------------------------------------------------------------------------


class TestHeaderInvariant:
    """청크 헤더 크기 = 20 byte 불변식."""

    def test_header_size_is_20_bytes(self) -> None:
        # 본 불변식 위반 시 ``encode_chunk`` / ``decode_chunk`` 의 모든 케이스 깨짐
        assert CHUNK_HEADER_SIZE == 20


# ---------------------------------------------------------------------------
# 2. file_id 변환 round-trip
# ---------------------------------------------------------------------------


class TestFileIdConversion:
    """``new_file_id`` / ``file_id_to_bytes`` / ``file_id_from_bytes`` 호환성."""

    def test_new_file_id_is_uuid4_hex_32(self) -> None:
        fid = new_file_id()
        # 대시 없는 hex 32자 — 정본 ``file_id_to_bytes`` 의 정합 요건
        assert len(fid) == 32
        assert uuid.UUID(fid).version == 4

    def test_file_id_round_trip(self) -> None:
        fid = new_file_id()
        raw = file_id_to_bytes(fid)
        # raw = 16 byte UUID
        assert len(raw) == 16
        # 복원 후 동일
        assert file_id_from_bytes(raw) == fid

    def test_file_id_dashed_form_accepted(self) -> None:
        # 송신자가 dashed UUID 를 그대로 넘기는 케이스도 round-trip 가능해야 함
        dashed = str(uuid.uuid4())
        raw = file_id_to_bytes(dashed)
        # hex 변환 후 dash 제거 형식 으로 복원
        assert file_id_from_bytes(raw) == dashed.replace("-", "")

    def test_file_id_from_bytes_invalid_length(self) -> None:
        with pytest.raises(ValueError, match="UUID raw 길이 불일치"):
            file_id_from_bytes(b"\x00" * 15)
        with pytest.raises(ValueError, match="UUID raw 길이 불일치"):
            file_id_from_bytes(b"\x00" * 17)

    def test_file_id_to_bytes_invalid_string(self) -> None:
        with pytest.raises(ValueError):
            file_id_to_bytes("not-a-uuid")


# ---------------------------------------------------------------------------
# 3. encode_chunk / decode_chunk round-trip
# ---------------------------------------------------------------------------


class TestChunkCodec:
    """청크 인코딩/디코딩 + 경계 케이스."""

    def test_round_trip_basic(self) -> None:
        fid = new_file_id()
        payload = b"hello tootalk"
        frame = encode_chunk(fid, 0, payload)
        assert len(frame) == CHUNK_HEADER_SIZE + len(payload)

        decoded_fid, decoded_seq, decoded_payload = decode_chunk(frame)
        assert decoded_fid == fid
        assert decoded_seq == 0
        assert decoded_payload == payload

    def test_round_trip_empty_payload(self) -> None:
        # 마지막 청크가 정확히 chunk_size 의 배수 직전 일 때 발생할 수 있음
        fid = new_file_id()
        frame = encode_chunk(fid, 100, b"")
        decoded_fid, decoded_seq, decoded_payload = decode_chunk(frame)
        assert decoded_fid == fid
        assert decoded_seq == 100
        assert decoded_payload == b""

    def test_round_trip_max_seq(self) -> None:
        # uint32 상한 — 2^32 - 1
        fid = new_file_id()
        max_seq = (1 << 32) - 1
        frame = encode_chunk(fid, max_seq, b"x")
        _, decoded_seq, _ = decode_chunk(frame)
        assert decoded_seq == max_seq

    def test_round_trip_binary_payload_with_zero_bytes(self) -> None:
        # null byte 포함 payload — text 인코딩 의 의 의 의 byte-safe 검증
        fid = new_file_id()
        payload = b"\x00\xff\x00\xff" * 64
        frame = encode_chunk(fid, 42, payload)
        _, _, decoded = decode_chunk(frame)
        assert decoded == payload

    def test_encode_chunk_negative_seq(self) -> None:
        fid = new_file_id()
        with pytest.raises(ValueError, match="seq 범위 초과"):
            encode_chunk(fid, -1, b"x")

    def test_encode_chunk_seq_overflow(self) -> None:
        fid = new_file_id()
        with pytest.raises(ValueError, match="seq 범위 초과"):
            encode_chunk(fid, 1 << 32, b"x")

    def test_decode_chunk_truncated_frame(self) -> None:
        # 헤더 미만 길이 → 명시 예외
        with pytest.raises(ValueError, match="청크 프레임 길이 부족"):
            decode_chunk(b"\x00" * 19)


# ---------------------------------------------------------------------------
# 4. build_* 빌더 dict 정합
# ---------------------------------------------------------------------------


class TestBuilders:
    """JSON 메시지 빌더 4종 의 필드 정합."""

    def test_build_file_meta_minimal(self) -> None:
        msg = build_file_meta(
            file_id="abc123",
            name="hello.txt",
            size=1024,
            mime="text/plain",
            total_chunks=1,
            sha256="deadbeef",
        )
        assert msg["type"] == MSG_FILE_META
        assert msg["file_id"] == "abc123"
        assert msg["name"] == "hello.txt"
        assert msg["size"] == 1024
        assert msg["mime"] == "text/plain"
        assert msg["total_chunks"] == 1
        assert msg["sha256"] == "deadbeef"
        # thumbnail 미전달 시 key 자체 부재
        assert "thumbnail_base64" not in msg

    def test_build_file_meta_with_thumbnail(self) -> None:
        msg = build_file_meta(
            file_id="abc",
            name="cat.png",
            size=2048,
            mime="image/png",
            total_chunks=2,
            sha256="cafe",
            thumbnail_base64="iVBORw0KGgo=",
        )
        assert msg["thumbnail_base64"] == "iVBORw0KGgo="

    def test_build_file_meta_coerces_int(self) -> None:
        # size + total_chunks 의 의 의 외부 입력 (str/float) 의 의 int 변환
        msg = build_file_meta(
            file_id="x",
            name="x",
            size=1024.5,  # type: ignore[arg-type]
            mime="x",
            total_chunks="3",  # type: ignore[arg-type]
            sha256="x",
        )
        assert msg["size"] == 1024
        assert msg["total_chunks"] == 3

    def test_build_file_ack(self) -> None:
        msg = build_file_ack(file_id="fid", received_bytes=4096, last_seq=15)
        assert msg == {
            "type": MSG_FILE_ACK,
            "file_id": "fid",
            "received_bytes": 4096,
            "last_seq": 15,
        }

    def test_build_file_end(self) -> None:
        msg = build_file_end(file_id="fid")
        assert msg == {"type": MSG_FILE_END, "file_id": "fid"}

    def test_build_file_done_ok(self) -> None:
        msg = build_file_done(file_id="fid", ok=True, hash_match=True)
        assert msg == {
            "type": MSG_FILE_DONE,
            "file_id": "fid",
            "ok": True,
            "hash_match": True,
        }

    def test_build_file_done_failure(self) -> None:
        # 수신 실패 — ok=False + hash_match=False
        msg = build_file_done(file_id="fid", ok=False, hash_match=False)
        assert msg["ok"] is False
        assert msg["hash_match"] is False


# ---------------------------------------------------------------------------
# 5. JSON encode/decode round-trip
# ---------------------------------------------------------------------------


class TestTextCodec:
    """``encode_text`` / ``decode_text`` JSON round-trip + 한글 보존."""

    def test_round_trip_basic(self) -> None:
        msg = {"type": MSG_FILE_END, "file_id": "fid"}
        raw = encode_text(msg)
        assert decode_text(raw) == msg

    def test_korean_filename_preserved(self) -> None:
        # ensure_ascii=False — 한글 파일명 직 표현 (BPE 호환 정합)
        msg = build_file_meta(
            file_id="x",
            name="안녕하세요.txt",
            size=10,
            mime="text/plain",
            total_chunks=1,
            sha256="x",
        )
        raw = encode_text(msg)
        # JSON 본문 내 한글 그대로 (\\uXXXX escape 아님)
        assert "안녕하세요.txt" in raw
        assert decode_text(raw)["name"] == "안녕하세요.txt"

    def test_decode_text_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="FILE_\\* JSON 파싱 실패"):
            decode_text("{not valid json")

    def test_decode_text_non_dict_returns_empty(self) -> None:
        # JSON array · primitive 의 의 의 의 의 의 dict 폴백
        assert decode_text("[1, 2, 3]") == {}
        assert decode_text("42") == {}
        assert decode_text('"string"') == {}


# ---------------------------------------------------------------------------
# 6. parse_file_meta
# ---------------------------------------------------------------------------


class TestParseFileMeta:
    """JSON dict → ``FileMeta`` dataclass 변환."""

    def test_parse_minimal(self) -> None:
        payload = build_file_meta(
            file_id="fid",
            name="a.txt",
            size=100,
            mime="text/plain",
            total_chunks=1,
            sha256="hash",
        )
        meta = parse_file_meta(payload)
        assert isinstance(meta, FileMeta)
        assert meta.file_id == "fid"
        assert meta.name == "a.txt"
        assert meta.size == 100
        assert meta.mime == "text/plain"
        assert meta.total_chunks == 1
        assert meta.sha256 == "hash"
        assert meta.thumbnail_base64 is None

    def test_parse_with_thumbnail(self) -> None:
        payload = build_file_meta(
            file_id="fid",
            name="cat.png",
            size=2048,
            mime="image/png",
            total_chunks=2,
            sha256="hash",
            thumbnail_base64="iVBORw0KGgo=",
        )
        meta = parse_file_meta(payload)
        assert meta.thumbnail_base64 == "iVBORw0KGgo="

    def test_parse_wrong_type_raises(self) -> None:
        # FILE_ACK payload 를 parse_file_meta 로 호출 → 명시 예외
        payload = build_file_ack(file_id="fid", received_bytes=100, last_seq=1)
        with pytest.raises(ValueError, match="FILE_META 가 아닌"):
            parse_file_meta(payload)

    def test_parse_missing_required_key_raises(self) -> None:
        # name 누락 → KeyError
        payload = {
            "type": MSG_FILE_META,
            "file_id": "fid",
            "size": 100,
            "mime": "text/plain",
            "total_chunks": 1,
            "sha256": "hash",
        }
        with pytest.raises(KeyError):
            parse_file_meta(payload)


# ---------------------------------------------------------------------------
# 7. is_valid_text_type 화이트리스트
# ---------------------------------------------------------------------------


class TestTextTypeWhitelist:
    """4종 type 허용 + 그 외 차단."""

    @pytest.mark.parametrize(
        "value",
        [MSG_FILE_META, MSG_FILE_ACK, MSG_FILE_END, MSG_FILE_DONE],
    )
    def test_valid_types_accepted(self, value: str) -> None:
        assert is_valid_text_type(value) is True

    def test_file_chunk_not_text_type(self) -> None:
        # FILE_CHUNK = 바이너리 frame, text 화이트리스트 제외
        assert is_valid_text_type("FILE_CHUNK") is False

    @pytest.mark.parametrize(
        "value",
        ["", "UNKNOWN", "file_meta", None, 42, [], {}],
    )
    def test_invalid_types_rejected(self, value: object) -> None:
        assert is_valid_text_type(value) is False


# ---------------------------------------------------------------------------
# 8. JSON 직렬화 의 정합 — encode_text + build_*
# ---------------------------------------------------------------------------


class TestEndToEndJson:
    """build → encode → decode round-trip 통합."""

    def test_meta_full_round_trip(self) -> None:
        original = build_file_meta(
            file_id="fid",
            name="hello.txt",
            size=42,
            mime="text/plain",
            total_chunks=1,
            sha256="cafe",
        )
        raw = encode_text(original)
        # 다른 컨텍스트의 디코더가 동일 dict 를 복원
        parsed = json.loads(raw)
        assert parsed == original
        # FileMeta 변환도 정합
        meta = parse_file_meta(parsed)
        assert meta.name == "hello.txt"
        assert meta.size == 42
