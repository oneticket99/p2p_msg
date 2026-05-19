# SPDX-License-Identifier: GPL-3.0-or-later
"""주기 update checker — 시작 시 + 24시간 background 검증 (cycle 133).

Phase 4 cycle 132 의 ``app.updater.version_check`` follow-up — main_window
startup 시점 + 매 24시간 ``check_latest_version`` 호출 + 신 버전 검출 시
``UpdateDialog`` trigger callback.

설계 결정
---------
- ``asyncio.sleep`` + ``while True`` loop 패턴 — task cancel 의 정상
  shutdown 정합 (CancelledError graceful re-raise).
- ``on_new_version`` callback sync 호출 — caller 가 Qt main thread
  의 dispatch 의무 (PyQt6 ``QTimer.singleShot`` 등).
- network / parse exception 의 graceful catch — loop 계속 (next interval
  의 재시도).

본 cycle 범위 외
----------------
- adaptive interval (battery / metered network 감지 시 연장)
- channel 분기 (stable / beta / nightly)
- 강제 업데이트 polling 단축
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Final

from app.updater.version_check import (
    CURRENT_VERSION,
    check_latest_version,
    compare_versions,
)

log = logging.getLogger(__name__)

# 한글 주석: 24시간 = 86400초. 시작 시 1회 + 매 interval 반복
CHECK_INTERVAL_SECONDS: Final[int] = 24 * 3600


async def periodic_check(
    server_url: str,
    on_new_version: Callable[[dict], None],
    interval_seconds: int = CHECK_INTERVAL_SECONDS,
) -> None:
    """매 ``interval_seconds`` 마다 latest version 검증 + callback 호출.

    Parameters
    ----------
    server_url : str
        update server base URL (예 "https://update.tootalk.example").
    on_new_version : Callable[[dict], None]
        신 버전 검출 시 호출되는 callback. caller 의 Qt main thread
        dispatch 의무 (UpdateDialog 표시 전).
    interval_seconds : int
        polling interval — 기본 24시간. 테스트 의 override 가능.

    Notes
    -----
    asyncio.CancelledError 정상 re-raise — shutdown chain 정합.
    """

    while True:
        try:
            latest = await check_latest_version(server_url)
            if latest is not None:
                latest_version = latest.get("version", "")
                if latest_version and compare_versions(
                    CURRENT_VERSION, latest_version
                ) < 0:
                    log.info(
                        "[update-checker] 신 버전 검출 — current=%s latest=%s",
                        CURRENT_VERSION,
                        latest_version,
                    )
                    try:
                        on_new_version(latest)
                    except Exception as exc:  # noqa: BLE001
                        log.warning(
                            "[update-checker] on_new_version callback 실패 — %r",
                            exc,
                        )
                else:
                    log.debug(
                        "[update-checker] 신 버전 없음 — current=%s latest=%s",
                        CURRENT_VERSION,
                        latest_version,
                    )
            else:
                log.debug("[update-checker] latest 정보 없음 — 다음 interval 재시도")
        except asyncio.CancelledError:
            # 한글 주석: shutdown chain 의 정상 cancel — re-raise 의무
            log.info("[update-checker] cancel 수신 — loop 종료")
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("[update-checker] check 실패 — %r", exc)
        await asyncio.sleep(interval_seconds)
