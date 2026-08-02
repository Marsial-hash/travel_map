"""fund_share 记录语义判定测试。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from data_pipeline.adapters.share_semantics import FundShareRecordSemantics, determine_record_semantics

# 2026-05-06(周三) ~ 2026-05-11(周一) 开放日
OPEN_DATES = [date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8), date(2026, 5, 11)]


def make_df(dates: list[str], shares: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"trade_date": dates, "fd_share": shares})


class TestRecordSemantics:
    def test_daily_snapshot_full_coverage(self) -> None:
        """每个开放日都有记录 → DAILY_SNAPSHOT。"""
        df = make_df(
            ["20260506", "20260507", "20260508", "20260511"],
            [100.0, 100.0, 101.0, 101.0],
        )
        v = determine_record_semantics(df, OPEN_DATES)
        assert v.semantics == FundShareRecordSemantics.DAILY_SNAPSHOT
        assert v.forward_fill_unambiguous is True

    def test_change_event_with_unchanged_samples(self) -> None:
        """稀疏记录但份额不变转移样本≥5 → 可前向填充的 CHANGE_EVENT。"""
        from datetime import timedelta

        open_dates = []
        d = date(2026, 3, 2)
        while d <= date(2026, 5, 11):
            if d.weekday() < 5:
                open_dates.append(d)
            d += timedelta(days=1)
        # 变动日记录：只在部分开放日有记录，且大多相邻记录份额相同
        change_dates = [
            "20260302", "20260303", "20260309", "20260310", "20260316",
            "20260317", "20260323", "20260324", "20260330", "20260331",
            "20260406", "20260407",
        ]
        shares = [100.0, 100.0, 100.0, 100.0, 100.5, 100.5, 100.5, 101.0, 101.0, 101.0, 101.5, 101.5]
        df = make_df(change_dates, shares)
        v = determine_record_semantics(df, open_dates)
        # 相邻开放日份额相同转移样本：5对相同 + 1对不同
        assert v.unchanged_transfer_samples >= 5, v.evidence
        assert v.semantics == FundShareRecordSemantics.CHANGE_EVENT
        assert v.forward_fill_unambiguous is True

    def test_mixed_unknown_when_inconsistent(self) -> None:
        """无法无歧义判定 → MIXED_OR_UNKNOWN。"""
        df = make_df(["20260506", "20260507"], [100.0, 101.0])
        v = determine_record_semantics(df, OPEN_DATES)
        # 覆盖低且无足够不变样本
        assert v.semantics == FundShareRecordSemantics.MIXED_OR_UNKNOWN

    def test_empty_df(self) -> None:
        v = determine_record_semantics(pd.DataFrame(), OPEN_DATES)
        assert v.semantics == FundShareRecordSemantics.MIXED_OR_UNKNOWN
