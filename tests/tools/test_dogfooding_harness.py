# SPDX-License-Identifier: GPL-3.0-or-later
"""``tools.dogfooding_harness`` 단위 테스트.

MetricSample 검증 + MetricCollector monotonic + stats + RTT 통계 +
throughput 변환 + JSON report write round-trip.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# tools 디렉토리 path 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import dogfooding_harness as dh  # noqa: E402


class TestMetricSampleValidation:
    """``MetricSample`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        sample = dh.MetricSample(
            metric_name="rtt_ms", value=42.5, unit="ms", timestamp_ms=100
        )
        assert sample.metric_name == "rtt_ms"

    def test_empty_metric_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="metric_name 빈 문자열 불가"):
            dh.MetricSample(metric_name="", value=1, unit="ms", timestamp_ms=0)

    def test_empty_unit_rejected(self) -> None:
        with pytest.raises(ValueError, match="unit 빈 문자열 불가"):
            dh.MetricSample(metric_name="rtt_ms", value=1, unit="", timestamp_ms=0)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            dh.MetricSample(
                metric_name="rtt_ms", value=1, unit="ms", timestamp_ms=-1
            )


class TestMetricCollector:
    """``MetricCollector`` monotonic + stats 검증."""

    def test_empty_collector(self) -> None:
        collector = dh.MetricCollector()
        assert collector.samples == []
        assert collector.stats("rtt_ms") == {"count": 0}

    def test_add_samples_in_order(self) -> None:
        collector = dh.MetricCollector()
        collector.add(dh.MetricSample("rtt_ms", 10.0, "ms", 100))
        collector.add(dh.MetricSample("rtt_ms", 20.0, "ms", 200))
        collector.add(dh.MetricSample("rtt_ms", 30.0, "ms", 300))
        stats = collector.stats("rtt_ms")
        assert stats["count"] == 3
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0

    def test_monotonic_violation_rejected(self) -> None:
        collector = dh.MetricCollector()
        collector.add(dh.MetricSample("rtt_ms", 10.0, "ms", 200))
        with pytest.raises(ValueError, match="monotonic 의무"):
            collector.add(dh.MetricSample("rtt_ms", 20.0, "ms", 100))

    def test_filter_by_metric(self) -> None:
        collector = dh.MetricCollector()
        collector.add(dh.MetricSample("rtt_ms", 10.0, "ms", 100))
        collector.add(dh.MetricSample("rss_mb", 250.0, "MB", 110))
        collector.add(dh.MetricSample("rtt_ms", 12.0, "ms", 120))
        rtt = collector.filter_by_metric("rtt_ms")
        assert len(rtt) == 2
        rss = collector.filter_by_metric("rss_mb")
        assert len(rss) == 1


class TestEstimateRtt:
    """``estimate_rtt_ms`` 통계 산출 검증."""

    def test_empty_samples(self) -> None:
        assert dh.estimate_rtt_ms([]) == {"count": 0}

    def test_single_sample(self) -> None:
        stats = dh.estimate_rtt_ms([42.5])
        assert stats["count"] == 1
        assert stats["min"] == 42.5
        assert stats["max"] == 42.5
        assert stats["avg"] == 42.5

    def test_multi_sample_stats(self) -> None:
        stats = dh.estimate_rtt_ms([10.0, 20.0, 30.0, 40.0, 50.0])
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["avg"] == 30.0
        assert stats["p50"] == 30.0

    def test_p95_index(self) -> None:
        # 100 sample = p95 의 index 95
        samples = [float(i) for i in range(1, 101)]
        stats = dh.estimate_rtt_ms(samples)
        assert stats["p95"] >= 95.0


class TestEstimateThroughput:
    """``estimate_throughput_mbps`` 변환 검증."""

    def test_zero_elapsed_returns_zero(self) -> None:
        assert dh.estimate_throughput_mbps(1000, 0) == 0.0

    def test_1mb_in_1s_equals_8mbps(self) -> None:
        # 1 MB = 1_000_000 byte / 1 sec = 8 Mbps
        assert dh.estimate_throughput_mbps(1_000_000, 1.0) == 8.0

    def test_5mbps_target(self) -> None:
        # observability-baseline TD-4 의 5 Mbps target
        result = dh.estimate_throughput_mbps(625_000, 1.0)
        assert result == 5.0


class TestWriteReport:
    """``write_report`` JSON round-trip 검증."""

    def test_empty_collector_report(self, tmp_path: Path) -> None:
        collector = dh.MetricCollector(started_at_ms=100)
        report_path = tmp_path / "report.json"
        dh.write_report(collector, report_path, metadata={"mode": "test"})
        payload = json.loads(report_path.read_text())
        assert payload["started_at_ms"] == 100
        assert payload["samples"] == []
        assert payload["metadata"]["mode"] == "test"

    def test_report_with_samples(self, tmp_path: Path) -> None:
        collector = dh.MetricCollector(started_at_ms=100)
        collector.add(dh.MetricSample("rtt_ms", 42.5, "ms", 110))
        collector.add(dh.MetricSample("rss_mb", 250.0, "MB", 120))
        report_path = tmp_path / "out" / "report.json"
        dh.write_report(collector, report_path)
        assert report_path.exists()
        payload = json.loads(report_path.read_text())
        assert len(payload["samples"]) == 2
        assert "rtt_ms" in payload["stats"]
        assert payload["stats"]["rtt_ms"]["count"] == 1
        assert "rss_mb" in payload["stats"]

    def test_report_korean_metadata(self, tmp_path: Path) -> None:
        # ensure_ascii=False 한글 보존
        collector = dh.MetricCollector(started_at_ms=100)
        report_path = tmp_path / "report.json"
        dh.write_report(collector, report_path, metadata={"환경": "macOS"})
        text = report_path.read_text(encoding="utf-8")
        assert "macOS" in text
        assert "환경" in text
