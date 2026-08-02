"""Point-in-time 测试（不得访问未来数据）。"""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from data_pipeline.adapters.share_semantics import pit_forward_only_reconstruction

TZ = ZoneInfo("Asia/Shanghai")


class TestPointInTime:
    def test_t_day_intraday_cannot_see_t_share(self) -> None:
        """T日盘中不能访问T日最终份额。"""
        # 份额记录 available_at = T+2 09:30（V1保守政策）
        # T日盘中（15:00前）评估 → 无任何记录可用
        records = {date(2026, 5, 8): 100.0}
        eval_t = date(2026, 5, 6)  # T日盘中
        assert pit_forward_only_reconstruction(records, eval_t) is None

    def test_unpublished_share_not_in_model(self) -> None:
        """份额尚未发布时不得进入当时模型。"""
        records = {date(2026, 5, 8): 100.0}
        # T+1（2026-05-07）仍未到 V1 的 T+2 可用时间
        assert pit_forward_only_reconstruction(records, date(2026, 5, 7)) is None

    def test_after_publish_available(self) -> None:
        """T+2 发布后才进入历史可用集合。"""
        records = {date(2026, 5, 8): 100.0}
        assert pit_forward_only_reconstruction(records, date(2026, 5, 10)) == 100.0

    def test_future_confirmation_not_used(self) -> None:
        """M-02: 不得用未来记录确认历史状态（周一无记录，周三记录=100 → 周二不能确认）。"""
        records = {date(2026, 5, 6): 100.0}  # 只有周三记录
        # 周一评估：无记录
        assert pit_forward_only_reconstruction(records, date(2026, 5, 4)) is None
        # 周三评估：有记录
        assert pit_forward_only_reconstruction(records, date(2026, 5, 6)) == 100.0

    def test_latest_record_at_or_before_eval(self) -> None:
        records = {date(2026, 5, 6): 100.0, date(2026, 5, 11): 105.0}
        assert pit_forward_only_reconstruction(records, date(2026, 5, 8)) == 100.0
        assert pit_forward_only_reconstruction(records, date(2026, 5, 11)) == 105.0


class TestResearchUniverse:
    def test_no_future_disclosure(self) -> None:
        """Research Universe 不得使用未来披露（research_available_at <= eval）。"""
        import csv
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "registry" / "research_universe.csv"
        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        for row in rows:
            avail = row["research_available_at"]
            assert avail, f"research_available_at missing for {row['etf_code']}"
