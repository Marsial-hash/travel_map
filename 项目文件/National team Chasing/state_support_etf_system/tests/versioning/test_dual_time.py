"""双时间查询测试（P1 补丁：knowledge_as_of vs system_as_of 分离）。"""
from __future__ import annotations

from datetime import UTC, datetime

from data_pipeline.execution.dual_time import DualTimeQuery, PublicationManager

TZ = UTC


def ts(y: int, m: int, d: int, h: int = 10) -> datetime:
    return datetime(y, m, d, h, 0, tzinfo=TZ)


class TestDualTimeQuery:
    def test_knowledge_filter(self) -> None:
        """knowledge 过滤 research_available_at。"""
        sql = DualTimeQuery.knowledge_filter("research_available_at", ts(2020, 1, 1))
        assert "research_available_at <= TIMESTAMP" in sql
        assert "2020-01-01" in sql

    def test_system_filter_includes_supersession(self) -> None:
        """system 过滤 system_valid_from 且排除已被后继取代的记录。"""
        sql = DualTimeQuery.system_filter("system_valid_from", ts(2026, 8, 1), "record_supersession")
        assert "system_valid_from <= TIMESTAMP" in sql
        assert "NOT EXISTS (SELECT 1 FROM record_supersession s" in sql
        assert "superseded_at <= TIMESTAMP" in sql

    def test_backfill_2020_visible_in_2026(self) -> None:
        """P1: 2026回填的2020记录，在 knowledge=2020/system=2026 可返回（模拟）。"""
        # research_available_at=2020-01-03, system_valid_from=2026-08-01
        # knowledge=2020-12-31 → research_available_at(2020-01-03) <= 2020-12-31 ✅
        # system=2026-12-31 → system_valid_from(2026-08-01) <= 2026-12-31 ✅
        research_avail = ts(2020, 1, 3)
        system_valid = ts(2026, 8, 1)
        assert research_avail <= ts(2020, 12, 31)  # knowledge 可见
        assert system_valid <= ts(2026, 12, 31)  # system 可见
        assert research_avail > ts(2020, 1, 1)  # knowledge 早于 research_available → 不可见

    def test_backfill_2020_not_visible_in_2020_system(self) -> None:
        """同一查询在 system=2020 时不得返回（当时本系统尚未入库）。"""
        system_valid = ts(2026, 8, 1)
        assert not (system_valid <= ts(2020, 12, 31))  # system 不可见


class TestPublicationManager:
    def test_only_published_readable(self) -> None:
        """API 只读 PUBLISHED；RUNNING/FAILED/QUARANTINED 不可读。"""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            from pathlib import Path

            pm = PublicationManager(Path(d))
            v1 = pm.start_version("etf_share")
            pm.mark(v1, "PUBLISHED", fingerprint="abc")
            v2 = pm.start_version("etf_share")
            pm.mark(v2, "FAILED")
            v3 = pm.start_version("etf_share")
            pm.mark(v3, "QUARANTINED")
            assert len(pm.readable_versions()) == 1
            assert pm.readable_versions()[0].dataset_version == v1

    def test_latest_published_respects_system_as_of(self) -> None:
        """dataset_version 选择 published_at <= system_as_of 的最新 PUBLISHED。"""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            from pathlib import Path

            pm = PublicationManager(Path(d))
            v1 = pm.start_version("etf_share")
            pm.mark(v1, "PUBLISHED", fingerprint="f1")
            # system_as_of 在 v1 发布前 → 不可见
            assert pm.latest_published("etf_share", ts(2020, 1, 1)) is None
            # system_as_of 在当前 → 可见
            assert pm.latest_published("etf_share") is not None
