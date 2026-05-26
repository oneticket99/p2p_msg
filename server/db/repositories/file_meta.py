# SPDX-License-Identifier: GPL-3.0-or-later
"""file_meta 테이블 repository — 파일 송수신 메타데이터 영속화 (Agent #16).

역할
----
DataChannel 파일 전송의 메타데이터(파일 id/이름/크기/MIME/sha256/썸네일)와 전송 상태를 영속한다.
실 바이트는 별도 청크 스트림으로 운반되고, 본 테이블은 무결성 검증·재표시용 메타만 보관한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = signaling 영속화 bridge(FILE_META/FILE_DONE 메시지 처리).

상태 머신 invariant
------------------
- status = uploading → completed / failed (단방향 전이). 신규 row 는 uploading 으로 시작.
- mark_completed 는 WHERE 에 ``status = 'uploading'`` 을 둬 이미 종료된 전송의 재완료를 차단한다.
- file_id = UUID hex(애플리케이션 생성 식별자). 모든 SQL parameterized.
- 4 공개 함수 — insert_file_meta + mark_completed + mark_failed + get_by_file_id.

부작용
------
insert/mark_completed/mark_failed 는 write(commit). get_by_file_id 는 부작용 없음(SELECT only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class FileMetaRow:
    """file_meta 단일 row 의 read-only 투영 — 12 column 정합.

    책임: ``get_by_file_id`` SELECT 결과 래핑. 불변식: frozen + 필드 순서 = SELECT 컬럼 1:1.
    ``completed_at`` None = 전송 미완(uploading/failed), 값 존재 = 완료 시각.
    ``thumbnail_base64`` 는 이미지 전송 시 인라인 미리보기용(비이미지 None).
    """

    id: int
    file_id: str
    room_id: int
    sender_id: int
    name: str
    size: int
    mime: str
    sha256: str
    status: str
    thumbnail_base64: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


async def insert_file_meta(
    pool: Any,
    *,
    file_id: str,
    room_id: int,
    sender_id: int,
    name: str,
    size: int,
    mime: str,
    sha256: str,
    thumbnail_base64: Optional[str] = None,
) -> int:
    """FILE_META 메시지 수신 시 메타 row 생성. status=uploading 으로 시작, 신규 id 반환.

    의도: 파일 전송 시작 시점 — 청크 도착 전 메타를 먼저 영속해 진행/무결성 추적의 기준을 만든다.
    부작용: file_meta INSERT + commit 즉시 영속.
    """

    sql = (
        "INSERT INTO file_meta (file_id, room_id, sender_id, name, size, "
        "                       mime, sha256, status, thumbnail_base64) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'uploading', %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (file_id, room_id, sender_id, name, size, mime, sha256, thumbnail_base64),
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def mark_completed(pool: Any, file_id: str) -> None:
    """FILE_DONE 수신 시 status=completed + completed_at=CURRENT_TIMESTAMP.

    의도: 전송 정상 종료 표시. WHERE 의 ``status = 'uploading'`` 가드로 이미 완료/실패한
    전송의 재완료(상태 덮어쓰기)를 차단한다(단방향 전이 보장). 부작용: UPDATE + commit.
    """

    sql = (
        "UPDATE file_meta SET status = 'completed', "
        "                     completed_at = CURRENT_TIMESTAMP "
        "WHERE file_id = %s AND status = 'uploading'"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
        await conn.commit()


async def mark_failed(pool: Any, file_id: str) -> None:
    """전송 오류 시 status=failed 표시. 부작용: UPDATE + commit 즉시 영속.

    의도: 청크 유실·무결성 실패·연결 단절 등 비정상 종료 기록(재시도/정리 분기의 근거).
    """

    sql = "UPDATE file_meta SET status = 'failed' WHERE file_id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
        await conn.commit()


async def get_by_file_id(pool: Any, file_id: str) -> Optional[FileMetaRow]:
    """file_id(UUID hex) 단건 lookup. 부재 시 None. 부작용 없음(SELECT only).

    의도: 청크 수신/완료 처리 시 메타 조회 + 무결성(sha256) 검증의 기준. file_id 는 UNIQUE.
    """

    sql = (
        "SELECT id, file_id, room_id, sender_id, name, size, mime, sha256, "
        "       status, thumbnail_base64, created_at, completed_at "
        "FROM file_meta WHERE file_id = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return FileMetaRow(*row)
