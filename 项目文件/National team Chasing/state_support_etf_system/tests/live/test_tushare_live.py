"""真实Tushare集成测试（live + requires_tushare_token）。

Token缺失时标记 BLOCKED_MISSING_CREDENTIAL，不得伪装PASS。
"""
from __future__ import annotations

from datetime import date

import pytest

from data_pipeline.adapters.tushare_calendar import TokenDetector
from data_pipeline.adapters.tushare_shares import FundShareAdapter
from data_pipeline.calendar.market_calendar import MarketCalendar

pytestmark = pytest.mark.live

# 510300 上市以来大致范围（具体上市日以fund_basic验证为准）
OPEN_DATES = [date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8), date(2026, 5, 11), date(2026, 5, 12)]


def test_token_detected() -> None:
    assert TokenDetector.detected() is True


@pytest.mark.requires_tushare_token
def test_fund_share_permission_and_fields() -> None:
    """G01-TUSHARE: Token权限 + fund_share 调用成功。"""
    adapter = FundShareAdapter()
    assert adapter.token_available, "TUSHARE_TOKEN not detected → BLOCKED_MISSING_CREDENTIAL"

    cal = MarketCalendar.from_open_dates("SSE", OPEN_DATES, source="TEST", version="v1")
    result = adapter.fetch_complete_range("510300.SH", date(2026, 5, 6), date(2026, 5, 11), cal)
    assert result.api_status in ("SUCCESS_WITH_DATA", "POTENTIALLY_TRUNCATED", "SUCCESS_EMPTY_VALID")
    if result.api_status == "PERMISSION_DENIED":
        pytest.skip("PERMISSION_DENIED: 2000积分可能不足，标记BLOCKED_PERMISSION")
    if result.data is not None and not result.data.empty:
        assert set(result.data.columns).issuperset({"ts_code", "trade_date", "fd_share"})
