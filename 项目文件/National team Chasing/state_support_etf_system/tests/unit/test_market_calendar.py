"""交易日历单元测试。"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from data_pipeline.calendar.market_calendar import (
    ASIA_SHANGHAI,
    MarketCalendar,
    MarketSession,
    is_within_session,
    next_valid_execution_time,
)

# 2026-05-01(周五,劳动节)至2026-05-08: 5/1-5/5劳动节假期(近似), 5/6(周三)开市
OPEN_DATES = [
    date(2026, 4, 30),
    date(2026, 5, 6),
    date(2026, 5, 7),
    date(2026, 5, 8),
    date(2026, 5, 11),
]


@pytest.fixture()
def cal() -> MarketCalendar:
    return MarketCalendar.from_open_dates("SSE", OPEN_DATES, source="TEST", version="v1")


class TestMarketCalendar:
    def test_is_open(self, cal: MarketCalendar) -> None:
        assert cal.is_open(date(2026, 5, 6))
        assert not cal.is_open(date(2026, 5, 1))

    def test_next_open_date_derived(self, cal: MarketCalendar) -> None:
        """J-04: next_open_date 为派生字段。"""
        assert cal.next_open_date(date(2026, 4, 30)) == date(2026, 5, 6)
        assert cal.next_open_date(date(2026, 5, 7)) == date(2026, 5, 8)
        assert cal.next_open_date(date(2026, 5, 11)) is None

    def test_previous_open_date(self, cal: MarketCalendar) -> None:
        assert cal.previous_open_date(date(2026, 5, 6)) == date(2026, 4, 30)
        assert cal.previous_open_date(date(2026, 5, 8)) == date(2026, 5, 7)

    def test_open_session_distance(self, cal: MarketCalendar) -> None:
        """J-01: 周一->周二距离=1。"""
        assert cal.open_session_distance(date(2026, 5, 7), date(2026, 5, 8)) == 1

    def test_missing_open_session_count(self, cal: MarketCalendar) -> None:
        """周一->周三且周二缺数据: missing=1。"""
        assert cal.missing_open_session_count(date(2026, 5, 7), date(2026, 5, 8)) == 0

    def test_add_open_days(self, cal: MarketCalendar) -> None:
        assert cal.add_open_days(date(2026, 4, 30), 1) == date(2026, 5, 6)
        assert cal.add_open_days(date(2026, 5, 6), 2) == date(2026, 5, 8)


class TestMarketSessions:
    def test_within_morning(self) -> None:
        dt = datetime(2026, 5, 7, 10, 0, tzinfo=ASIA_SHANGHAI)
        assert is_within_session(dt, MarketSession("SSE"))

    def test_lunch_break_not_within(self) -> None:
        dt = datetime(2026, 5, 7, 12, 0, tzinfo=ASIA_SHANGHAI)
        assert not is_within_session(dt, MarketSession("SSE"))

    def test_afternoon(self) -> None:
        dt = datetime(2026, 5, 7, 14, 0, tzinfo=ASIA_SHANGHAI)
        assert is_within_session(dt, MarketSession("SSE"))

    def test_after_close_not_within(self) -> None:
        dt = datetime(2026, 5, 7, 15, 30, tzinfo=ASIA_SHANGHAI)
        assert not is_within_session(dt, MarketSession("SSE"))


class TestNextValidExecutionTime:
    def test_0930_available_not_0930_execution(self, cal: MarketCalendar) -> None:
        """硬规则：09:30可用的数据不得按09:30开盘成交。"""
        avail = datetime(2026, 5, 7, 9, 30, tzinfo=ASIA_SHANGHAI)
        nxt = next_valid_execution_time(avail, cal, MarketSession("SSE"))
        assert nxt > avail
        assert nxt.time().hour == 9 and nxt.time().minute == 31

    def test_lunch_break_no_1131(self, cal: MarketCalendar) -> None:
        """午间休市不能生成11:31成交。"""
        t = datetime(2026, 5, 7, 11, 30, tzinfo=ASIA_SHANGHAI)
        nxt = next_valid_execution_time(t, cal, MarketSession("SSE"))
        assert nxt.time().hour == 13 and nxt.time().minute == 0

    def test_after_close_no_1501(self, cal: MarketCalendar) -> None:
        """15:00后不能生成15:01成交。"""
        t = datetime(2026, 5, 7, 15, 0, tzinfo=ASIA_SHANGHAI)
        nxt = next_valid_execution_time(t, cal, MarketSession("SSE"))
        assert nxt.date() == date(2026, 5, 8)
        assert nxt.time().hour == 9 and nxt.time().minute == 30

    def test_holiday_no_execution(self, cal: MarketCalendar) -> None:
        """节假日不能生成交易价格。"""
        t = datetime(2026, 5, 1, 10, 0, tzinfo=ASIA_SHANGHAI)
        nxt = next_valid_execution_time(t, cal, MarketSession("SSE"))
        assert nxt.date() == date(2026, 5, 6)
