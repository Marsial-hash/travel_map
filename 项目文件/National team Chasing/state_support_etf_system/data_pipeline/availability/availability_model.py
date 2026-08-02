"""时间可用性模型：八时间字段与 Availability Policy。

- research_available_at 是历史回测唯一依据
- 生产实时使用 first_seen_at
- Policy 版本化，不得原地修改
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_pipeline.calendar.market_calendar import MarketCalendar


class AvailabilityBasis(StrEnum):
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    LIVE_OBSERVATION = "LIVE_OBSERVATION"
    CROSS_SOURCE_INFERENCE = "CROSS_SOURCE_INFERENCE"
    CONSERVATIVE_POLICY = "CONSERVATIVE_POLICY"
    UNKNOWN = "UNKNOWN"


class PolicyConfidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class AvailabilityPolicy:
    policy_id: str
    data_source: str
    dataset_name: str
    conservative_backtest_rule: str  # 人类可读规则
    basis: AvailabilityBasis
    confidence: PolicyConfidence
    live_signal_approved: bool = False
    effective_from: date | None = None
    evidence_status: str = "UNVERIFIED"


@dataclass(frozen=True)
class AvailabilityModel:
    """每条记录的时间字段集合。"""

    event_time: datetime | None = None
    trade_date: date | None = None
    source_published_at: datetime | None = None
    source_observed_at: datetime | None = None
    research_available_at: datetime | None = None
    first_seen_at: datetime | None = None
    ingested_at: datetime | None = None
    revised_at: datetime | None = None
    source_timezone: str = "Asia/Shanghai"
    availability_policy_id: str | None = None
    availability_basis: AvailabilityBasis | None = None
    availability_evidence_id: str | None = None
    policy_confidence: PolicyConfidence | None = None


# 预置 Policy（版本化；不得原地修改，后续新增 V2_OBSERVED）
BUILTIN_POLICIES: dict[str, AvailabilityPolicy] = {
    "TUSHARE_FUND_SHARE_V1_CONSERVATIVE": AvailabilityPolicy(
        policy_id="TUSHARE_FUND_SHARE_V1_CONSERVATIVE",
        data_source="TUSHARE_FUND_SHARE",
        dataset_name="fund_share",
        conservative_backtest_rule="T+2 09:30",
        basis=AvailabilityBasis.CONSERVATIVE_POLICY,
        confidence=PolicyConfidence.LOW,
        live_signal_approved=False,
        evidence_status="UNVERIFIED",
    ),
    "TENCENT_QUOTES_V1": AvailabilityPolicy(
        policy_id="TENCENT_QUOTES_V1",
        data_source="TENCENT_QUOTES",
        dataset_name="etf_quote",
        conservative_backtest_rule="T日15:30",
        basis=AvailabilityBasis.LIVE_OBSERVATION,
        confidence=PolicyConfidence.MEDIUM,
        live_signal_approved=False,
        evidence_status="CONFIRMED",
    ),
    "SOHU_INDEX_V1": AvailabilityPolicy(
        policy_id="SOHU_INDEX_V1",
        data_source="SOHU_HISQ",
        dataset_name="index_turnover",
        conservative_backtest_rule="T日15:30",
        basis=AvailabilityBasis.LIVE_OBSERVATION,
        confidence=PolicyConfidence.MEDIUM,
        live_signal_approved=False,
        evidence_status="CONFIRMED",
    ),
    "EM_NAV_V1": AvailabilityPolicy(
        policy_id="EM_NAV_V1",
        data_source="EM_NAV",
        dataset_name="fund_nav",
        conservative_backtest_rule="T+1 09:30",
        basis=AvailabilityBasis.CONSERVATIVE_POLICY,
        confidence=PolicyConfidence.LOW,
        live_signal_approved=False,
        evidence_status="UNVERIFIED",
    ),
    "FUND_REPORT_V1": AvailabilityPolicy(
        policy_id="FUND_REPORT_V1",
        data_source="FUND_DISCLOSURE",
        dataset_name="fund_periodic_report",
        conservative_backtest_rule="披露日09:30",
        basis=AvailabilityBasis.OFFICIAL_DOCUMENTATION,
        confidence=PolicyConfidence.MEDIUM,
        live_signal_approved=False,
        evidence_status="CONFIRMED",
    ),
}


def research_available_for_tushare_fund_share(trade_date: date, calendar: MarketCalendar) -> datetime:
    """fund_share V1 保守政策：T+2 09:30（第二个后续开放日）。"""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Shanghai")
    # 交易日 T 之后第 2 个开放日 09:30
    t1 = calendar.add_open_days(trade_date, 2)
    return datetime.combine(t1, datetime.min.time().replace(hour=9, minute=30), tzinfo=tz)
