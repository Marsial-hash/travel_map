"""R-05 幂等 Replay 测试：相同 Raw 重跑不产生重复记录。"""
from __future__ import annotations

import hashlib
from datetime import UTC
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_raw_fingerprint(code: str) -> str:
    p = PROJECT_ROOT / "warehouse" / "raw" / "phase1a_c" / f"fund_share_{code}.json"
    return hashlib.sha256(p.read_bytes()).hexdigest()


class TestIdempotency:
    def test_raw_fingerprint_stable_across_reads(self) -> None:
        """相同 Raw 文件哈希稳定。"""
        for code in ["510300", "510310", "159919", "510050", "510500", "159845"]:
            fp1 = load_raw_fingerprint(code)
            fp2 = load_raw_fingerprint(code)
            assert fp1 == fp2

    def test_canonical_rebuild_is_idempotent(self, tmp_path: Path) -> None:
        """相同输入重建 share_daily 产生相同指纹（模拟Replay）。"""
        from data_pipeline.normalization.remediation import build_share_daily_with_semantics, load_calendar_open_dates

        open_dates = load_calendar_open_dates()
        raw = pl.read_json(PROJECT_ROOT / "warehouse" / "raw" / "phase1a_c" / "fund_share_510300.json")

        trading1, nt1, sem1 = build_share_daily_with_semantics(raw, open_dates, "510300")
        trading2, nt2, sem2 = build_share_daily_with_semantics(raw, open_dates, "510300")

        # 行数相同
        assert len(trading1) == len(trading2)
        assert len(nt1) == len(nt2)
        assert len(sem1) == len(sem2)
        # 数值相同
        assert trading1.get_column("raw_total_shares").sum() == trading2.get_column("raw_total_shares").sum()
        # 无重复开放日
        assert len(trading1) == len(set(trading1.get_column("trade_date").to_list()))

    def test_no_nontrading_in_canonical(self) -> None:
        """Canonical 日度份额表不含非交易日记录（R-02）。"""
        from data_pipeline.normalization.remediation import load_calendar_open_dates

        open_set = set(load_calendar_open_dates())
        for code in ["510300", "510310", "159919", "510050", "510500", "159845"]:
            path = PROJECT_ROOT / "warehouse" / "canonical" / "phase1a_c"
            s = pl.read_parquet(path / f"canonical_etf_share_daily_{code}.parquet")
            dates = set(s.get_column("trade_date").to_list())
            nontrading = [d for d in dates if d not in open_set]
            assert len(nontrading) == 0, f"{code} 存在非交易日记录: {nontrading}"

    def test_supersession_does_not_erase_old(self) -> None:
        """Supersession 后旧版本仍可查询。"""
        from datetime import datetime

        from data_pipeline.execution.versioned_store import AppendOnlyStore

        store = AppendOnlyStore()
        bk = "TEST-510300-2026-01-28"
        v1 = store.insert(bk, {"raw_share": 100}, datetime(2026, 8, 1, tzinfo=UTC))
        v2 = store.insert(bk, {"raw_share": 90}, datetime(2026, 8, 2, tzinfo=UTC), revision_reason="revised")
        # 当前返回新值
        assert store.current(bk).payload["raw_share"] == 90  # type: ignore[union-attr]
        # 修订前 as-of 返回旧值
        old = store.as_of(bk, datetime(2026, 8, 1, 12, tzinfo=UTC))
        assert old.payload["raw_share"] == 100
        # v1 未被删除
        assert len(store.history(bk)) == 2
        assert v2.supersedes_record_id == v1.record_id

    def test_input_change_creates_supersession(self) -> None:
        """输入变化创建新版本，旧版本仍可复现。"""
        from datetime import datetime

        from data_pipeline.execution.versioned_store import AppendOnlyStore

        store = AppendOnlyStore()
        bk = "TEST-CHANGE-1"
        store.insert(bk, {"fd_share": 100.0}, datetime(2026, 8, 1, tzinfo=UTC))
        store.insert(bk, {"fd_share": 105.0}, datetime(2026, 8, 2, tzinfo=UTC), revision_reason="RAW_CHANGED")
        cur = store.current(bk)
        assert cur.payload["fd_share"] == 105.0  # type: ignore[union-attr]
        assert len(store.history(bk)) == 2
