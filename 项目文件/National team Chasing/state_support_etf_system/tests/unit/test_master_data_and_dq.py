"""主数据身份解析 + 日历 + 数据质量 + 水位线测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from data_pipeline.execution.watermark import WatermarkStatus, WatermarkTracker
from data_pipeline.normalization.master_data import InvalidInstrumentIdentity, resolve_instrument
from data_pipeline.validation.data_quality import DQTracker, compute_coverage


class TestMasterData:
    def test_resolve_sh(self) -> None:
        r = resolve_instrument("510300")
        assert r["internal_instrument_id"] == "INST-510300"
        assert r["exchange"] == "SH"
        assert r["source_specific_identifier"] == "510300.SH"

    def test_resolve_sz(self) -> None:
        r = resolve_instrument("159919")
        assert r["exchange"] == "SZ"
        assert r["source_specific_identifier"] == "159919.SZ"

    def test_no_market_guess(self) -> None:
        """禁止凭代码首位猜市场。"""
        assert resolve_instrument("510050")["source_specific_identifier"] == "510050.SH"

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(InvalidInstrumentIdentity):
            resolve_instrument("999999")


class TestDataQuality:
    def test_dq_summary(self) -> None:
        dq = DQTracker("test_run")
        dq.record(
            "INST-510300", "CRITICAL", "UNRESOLVED_SHARE_JUMP", "raw_total_shares", "TUSHARE",
            trade_date="2026-01-28", blocks_daily_flow=True,
        )
        dq.record("INST-510300", "MAJOR", "DATA_MISSING", "nav", "EM_NAV", trade_date="2026-01-29")
        assert dq.summary()["CRITICAL"] == 1
        assert dq.summary()["MAJOR"] == 1

    def test_dq_write(self, tmp_path: Path) -> None:
        dq = DQTracker("test_run", tmp_path)
        dq.record("INST-510300", "INFO", "TEST", "x", "src")
        p = dq.write()
        assert p.exists()

    def test_coverage_excludes_valid(self) -> None:
        """分母排除上市前/确认调整日，普通缺失计入。"""
        expected = ["2026-01-27", "2026-01-28", "2026-01-29"]
        observed = ["2026-01-27", "2026-01-29"]
        excluded = {"2026-01-28"}  # 确认调整日排除
        reasons = {"2026-01-29": "NAV_NOT_AVAILABLE"}
        cov = compute_coverage(expected, observed, excluded, reasons)
        assert cov["denominator"] == 2  # 排除调整日后剩2天
        assert cov["covered"] == 2
        assert cov["coverage_ratio"] == 1.0

    def test_coverage_unknown_block(self) -> None:
        expected = ["2026-01-27", "2026-01-28"]
        observed = ["2026-01-27"]
        excluded: set[str] = set()
        reasons: dict[str, str] = {}
        cov = compute_coverage(expected, observed, excluded, reasons)
        assert cov["unknown_blocked"] == 1  # 2026-01-28 无归因 → UNKNOWN


class TestWatermark:
    def test_watermark_status(self, tmp_path: Path) -> None:
        from datetime import date

        wm = WatermarkTracker(tmp_path)
        wm.set_watermark(
            "ETF_SHARE", "TUSHARE_FUND_SHARE", "TUSHARE_FUND_SHARE_V1_CONSERVATIVE",
            latest_research_available_trade_date=date(2026, 7, 31),
            watermark_status=WatermarkStatus.UP_TO_DATE,
        )
        assert wm.get("ETF_SHARE") is not None
        assert wm.get("ETF_SHARE").watermark_status == WatermarkStatus.UP_TO_DATE

    def test_flow_cutoff_min(self, tmp_path: Path) -> None:
        from datetime import date

        wm = WatermarkTracker(tmp_path)
        wm.set_watermark("ETF_SHARE", "A", "P1", latest_research_available_trade_date=date(2026, 7, 30))
        wm.set_watermark("ETF_NAV", "B", "P2", latest_research_available_trade_date=date(2026, 7, 28))
        assert str(wm.flow_publication_cutoff()) == "2026-07-28"  # min
