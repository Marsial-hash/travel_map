"""执行时间测试：执行价必须严格晚于数据可用和决策时间。"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from data_pipeline.execution.execution_model import ExecutionModel, ExecutionPriceType

TZ = ZoneInfo("Asia/Shanghai")


def make_model(decision: datetime, available: datetime | None, price_ts: datetime) -> ExecutionModel:
    return ExecutionModel(
        decision_generated_at=decision,
        research_available_at=available,
        execution_eligible_at=price_ts,
        execution_price_timestamp=price_ts,
        execution_price_type=ExecutionPriceType.NEXT_MINUTE_OPEN,
        execution_delay_policy_id="EXEC_DELAY_V1_CONSERVATIVE",
    )


class TestExecutionTiming:
    def test_0930_available_not_0930_open(self) -> None:
        """09:30可用的数据不得按09:30开盘成交。"""
        avail = datetime(2026, 5, 7, 9, 30, tzinfo=TZ)
        m = make_model(decision=avail, available=avail, price_ts=avail)  # 错误：price=09:30
        assert m.validate() is False

    def test_after_close_not_same_day_close(self) -> None:
        """盘后数据不能按当日收盘价成交。"""
        decision = datetime(2026, 5, 7, 15, 30, tzinfo=TZ)
        price_ts = datetime(2026, 5, 7, 15, 0, tzinfo=TZ)  # 错误：当日收盘早于决策
        m = make_model(decision=decision, available=decision, price_ts=price_ts)
        assert m.validate() is False

    def test_price_after_decision_valid(self) -> None:
        decision = datetime(2026, 5, 7, 9, 31, tzinfo=TZ)
        price_ts = datetime(2026, 5, 7, 9, 32, tzinfo=TZ)
        m = make_model(decision=decision, available=decision, price_ts=price_ts)
        assert m.validate() is True

    def test_delay_shifts_execution(self) -> None:
        """数据源延迟时执行时间同步后移。"""
        decision = datetime(2026, 5, 7, 10, 0, tzinfo=TZ)
        available = datetime(2026, 5, 7, 10, 30, tzinfo=TZ)  # 数据延迟
        price_ts = datetime(2026, 5, 7, 10, 0, tzinfo=TZ)  # 错误：早于可用
        m = make_model(decision=decision, available=available, price_ts=price_ts)
        assert m.validate() is False
