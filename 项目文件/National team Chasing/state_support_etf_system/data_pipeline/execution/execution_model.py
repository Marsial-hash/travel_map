"""交易执行时间模型。

硬规则：执行价格时间戳必须严格晚于数据可用时间和决策生成时间。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExecutionPriceType(StrEnum):
    NEXT_MINUTE_OPEN = "NEXT_MINUTE_OPEN"
    NEXT_5MIN_VWAP = "NEXT_5MIN_VWAP"
    SAME_DAY_CLOSE = "SAME_DAY_CLOSE"
    NEXT_DAY_OPEN = "NEXT_DAY_OPEN"
    NEXT_DAY_CLOSE = "NEXT_DAY_CLOSE"
    CUSTOM_CONSERVATIVE = "CUSTOM_CONSERVATIVE"


@dataclass(frozen=True)
class ExecutionModel:
    decision_generated_at: datetime
    research_available_at: datetime | None
    execution_eligible_at: datetime
    execution_price_timestamp: datetime
    execution_price_type: ExecutionPriceType
    execution_delay_policy_id: str

    def validate(self) -> bool:
        """执行价格时间戳必须严格晚于数据可用时间和决策生成时间。"""
        if self.execution_price_timestamp <= self.decision_generated_at:
            return False
        if self.research_available_at is not None and self.execution_price_timestamp <= self.research_available_at:
            return False
        return True
