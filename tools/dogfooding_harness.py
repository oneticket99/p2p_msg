#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 1 dogfooding harness — 사용자 manual measurement 의 자동화 (사이클 56).

memory `feedback_no_autonomy_dereliction_prevention.md` + observability-baseline.md
§5 6단계 회귀 검증 절차 정합. Phase 1 MVP DoD #1 (RTT < 500ms) + TD-4 (aiortc
약 5Mbps throughput) + RSS + disk leak 4 metric 의 최초 측정 의무.

본 harness 범위
--------------
- ``MetricSample`` dataclass — 단일 측정 결과 (metric_name + value + unit + timestamp)
- ``MetricCollector`` — psutil 기반 RSS + disk usage sample 누적
- ``estimate_rtt`` — WebRTC DataChannel ping/pong round-trip 측정 helper
- ``measure_throughput`` — DataChannel 의 known-size payload 전송 시간 측정
- ``write_report`` — JSON 결과 의 docs/measurements/ 저장

본 cycle 의 범위 외 (사용자 직접 의무):
- 실 데모 시그널링 서버 + 1:1 peer 연결 시나리오 setup
- aiortc 실 통합 환경 의 manual launch
- 분 단위 / 시간 단위 long-running RSS 측정 (사용자 의 별개 시점 직접 실행)
- 결과 의 baseline drift 검출 (observability-baseline.md §3 의 비교)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import psutil  # type: ignore[import]

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class MetricSample:
    """단일 측정 sample.

    Attributes
    ----------
    metric_name : str
        식별자 (rtt_ms / throughput_mbps / rss_mb / disk_used_mb).
    value : float
        측정값.
    unit : str
        단위 (ms / Mbps / MB).
    timestamp_ms : int
        측정 시점 (UNIX epoch ms).
    """

    metric_name: str
    value: float
    unit: str
    timestamp_ms: int

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError("metric_name 빈 문자열 불가")
        if not self.unit:
            raise ValueError("unit 빈 문자열 불가")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")


@dataclass(slots=True)
class MetricCollector:
    """harness session 의 측정 누적 container.

    Attributes
    ----------
    samples : list[MetricSample]
        시간 순서 의 sample list.
    started_at_ms : int
        session 시작 시점.
    """

    samples: List[MetricSample] = field(default_factory=list)
    started_at_ms: int = 0

    def add(self, sample: MetricSample) -> None:
        """sample append (timestamp 자동 정렬 검증)."""

        if self.samples and sample.timestamp_ms < self.samples[-1].timestamp_ms:
            raise ValueError(
                f"timestamp 의 monotonic 의무 — "
                f"last={self.samples[-1].timestamp_ms} new={sample.timestamp_ms}"
            )
        self.samples.append(sample)

    def filter_by_metric(self, metric_name: str) -> List[MetricSample]:
        """특정 metric 의 sample 만 추출."""

        return [s for s in self.samples if s.metric_name == metric_name]

    def stats(self, metric_name: str) -> Dict[str, float]:
        """metric 의 min / max / avg 통계."""

        values = [s.value for s in self.filter_by_metric(metric_name)]
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }


def sample_rss_mb(pid: Optional[int] = None) -> Optional[float]:
    """현재 process RSS (MB). psutil 부재 시 None.

    Parameters
    ----------
    pid : int | None
        대상 PID. None = current process.
    """

    if not _PSUTIL_AVAILABLE:
        return None
    proc = psutil.Process(pid) if pid is not None else psutil.Process()
    return proc.memory_info().rss / (1024 * 1024)


def sample_disk_used_mb(path: str = ".") -> Optional[float]:
    """path 의 disk usage (MB). psutil 부재 시 None."""

    if not _PSUTIL_AVAILABLE:
        return None
    usage = psutil.disk_usage(path)
    return usage.used / (1024 * 1024)


def estimate_rtt_ms(samples_ms: List[float]) -> Dict[str, float]:
    """RTT sample list 의 통계 산출.

    Parameters
    ----------
    samples_ms : list[float]
        각 ping / pong round-trip 의 ms 측정값.

    Returns
    -------
    dict
        count + min + max + avg + p50 + p95 (단, samples_ms 비어 있을 시 count=0).
    """

    if not samples_ms:
        return {"count": 0}
    sorted_samples = sorted(samples_ms)
    n = len(sorted_samples)
    return {
        "count": n,
        "min": sorted_samples[0],
        "max": sorted_samples[-1],
        "avg": sum(sorted_samples) / n,
        "p50": sorted_samples[n // 2],
        "p95": sorted_samples[min(n - 1, int(n * 0.95))],
    }


def estimate_throughput_mbps(bytes_sent: int, elapsed_seconds: float) -> float:
    """bytes_sent / elapsed_seconds → Mbps 변환.

    Parameters
    ----------
    bytes_sent : int
        전송 byte 수.
    elapsed_seconds : float
        전송 elapsed time (초).

    Returns
    -------
    float
        Mbps. elapsed_seconds = 0 시 0.0 반환.
    """

    if elapsed_seconds <= 0:
        return 0.0
    return (bytes_sent * 8) / (elapsed_seconds * 1_000_000)


def now_ms() -> int:
    """현재 시점 UNIX epoch ms."""

    return int(time.time() * 1000)


def write_report(
    collector: MetricCollector,
    output_path: Path,
    *,
    metadata: Optional[Dict[str, str]] = None,
) -> None:
    """collector 의 sample + 통계 의 JSON report 저장.

    Parameters
    ----------
    collector : MetricCollector
        측정 결과 container.
    output_path : Path
        report 저장 경로 (`docs/measurements/dogfooding-YYYY-MM-DD.json` 권장).
    metadata : dict | None
        실행 환경 metadata (OS / hardware / signal_server_host 등).
    """

    metric_names = {s.metric_name for s in collector.samples}
    payload = {
        "started_at_ms": collector.started_at_ms,
        "samples": [asdict(s) for s in collector.samples],
        "stats": {name: collector.stats(name) for name in sorted(metric_names)},
        "metadata": metadata or {},
        "psutil_available": _PSUTIL_AVAILABLE,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    # 사용자 manual measurement entry — 즉시 single-shot RSS + disk sample
    collector = MetricCollector(started_at_ms=now_ms())
    rss = sample_rss_mb()
    if rss is not None:
        collector.add(
            MetricSample(
                metric_name="rss_mb",
                value=rss,
                unit="MB",
                timestamp_ms=now_ms(),
            )
        )
    disk = sample_disk_used_mb(".")
    if disk is not None:
        collector.add(
            MetricSample(
                metric_name="disk_used_mb",
                value=disk,
                unit="MB",
                timestamp_ms=now_ms(),
            )
        )
    report_path = Path("docs/measurements") / f"dogfooding-{int(time.time())}.json"
    write_report(collector, report_path, metadata={"mode": "single-shot"})
    print(f"[dogfooding] report saved — {report_path}")
    print(f"[dogfooding] samples = {len(collector.samples)} (psutil={_PSUTIL_AVAILABLE})")
