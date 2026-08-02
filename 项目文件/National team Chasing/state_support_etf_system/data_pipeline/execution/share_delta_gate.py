"""份额差分与流量门控（J-01 + M-03 + 补丁12-1/2/9）。

两层门控：
1. daily_flow_eligible = open_session_distance==1 AND missing_open_session_count==0
2. economic_flow_eligible = daily_flow_eligible AND unit_consistency_passed AND
   identity_continuity_passed AND event_contamination_status==CLEAN AND
   source_revision_status != UNRESOLVED
3. nav_flow_eligible / close_flow_eligible 分别验证 NAV/价格可用性
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class EventContaminationStatus(StrEnum):
    CLEAN = "CLEAN"
    CONFIRMED_ADJUSTMENT_APPLIED = "CONFIRMED_ADJUSTMENT_APPLIED"
    UNRESOLVED_SHARE_JUMP = "UNRESOLVED_SHARE_JUMP"
    POSSIBLE_UNIT_CHANGE = "POSSIBLE_UNIT_CHANGE"
    POSSIBLE_SOURCE_REVISION = "POSSIBLE_SOURCE_REVISION"
    IDENTITY_DISCONTINUITY = "IDENTITY_DISCONTINUITY"


@dataclass
class ShareDeltaGate:
    """单条份额差分记录的门控结果。"""

    trade_date: date
    previous_observation_date: date | None
    open_session_distance: int
    missing_open_session_count: int
    is_consecutive_trading_day: bool
    daily_flow_eligible: bool
    interval_flow_only: bool
    missing_share_observation_count: int
    unit_consistency_passed: bool
    identity_continuity_passed: bool
    event_contamination_status: EventContaminationStatus
    unresolved_event_candidate_id: str | None
    source_revision_status: str
    adjustment_factor_verified: bool
    share_unit_basis_matched: bool
    valuation_unit_basis_matched: bool
    economic_flow_eligible: bool
    nav_flow_eligible: bool
    close_flow_eligible: bool
    flow_block_reason: str | None = None

    @property
    def flow_allowed(self) -> bool:
        return self.daily_flow_eligible and self.economic_flow_eligible


def evaluate_share_delta_gate(
    trade_date: date,
    previous_observation_date: date | None,
    open_session_distance: int,
    missing_open_session_count: int,
    *,
    unit_consistency_passed: bool = True,
    identity_continuity_passed: bool = True,
    event_contamination_status: EventContaminationStatus = EventContaminationStatus.CLEAN,
    unresolved_event_candidate_id: str | None = None,
    source_revision_status: str = "CLEAN",
    adjustment_factor_verified: bool = False,
    share_unit_basis_matched: bool = True,
    valuation_unit_basis_matched: bool = True,
) -> ShareDeltaGate:
    """按两层门控计算流量资格。

    硬规则（补丁12-2）：CONFIRMED_ADJUSTMENT_APPLIED 时须三验证全true。
    """
    is_consecutive = (
        previous_observation_date is not None
        and open_session_distance == 1
        and missing_open_session_count == 0
    )
    daily_flow_eligible = is_consecutive

    # 第二层：经济流量门控
    contamination_ok = event_contamination_status in (
        EventContaminationStatus.CLEAN,
        EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
    )
    if event_contamination_status == EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED:
        contamination_ok = (
            adjustment_factor_verified and share_unit_basis_matched and valuation_unit_basis_matched
        )
    revision_ok = source_revision_status != "UNRESOLVED"

    economic_flow_eligible = (
        daily_flow_eligible
        and unit_consistency_passed
        and identity_continuity_passed
        and contamination_ok
        and revision_ok
    )

    flow_block_reason: str | None = None
    if not daily_flow_eligible:
        flow_block_reason = "NON_CONSECUTIVE_SHARE_OBSERVATIONS"
    elif not unit_consistency_passed:
        flow_block_reason = "UNIT_INCONSISTENCY"
    elif not identity_continuity_passed:
        flow_block_reason = "IDENTITY_DISCONTINUITY"
    elif event_contamination_status == EventContaminationStatus.UNRESOLVED_SHARE_JUMP:
        flow_block_reason = f"UNRESOLVED_SHARE_JUMP:{unresolved_event_candidate_id or 'unknown'}"
    elif not contamination_ok:
        flow_block_reason = f"ADJUSTMENT_NOT_VERIFIED:{event_contamination_status.value}"
    elif not revision_ok:
        flow_block_reason = "SOURCE_REVISION_UNRESOLVED"

    # NAV/价格可用性（由调用方基于具体日期提供）
    nav_flow_eligible = economic_flow_eligible  # 若NAV日期/单位验证通过则由调用方更新
    close_flow_eligible = economic_flow_eligible

    return ShareDeltaGate(
        trade_date=trade_date,
        previous_observation_date=previous_observation_date,
        open_session_distance=open_session_distance,
        missing_open_session_count=missing_open_session_count,
        is_consecutive_trading_day=is_consecutive,
        daily_flow_eligible=daily_flow_eligible,
        interval_flow_only=not daily_flow_eligible,
        missing_share_observation_count=missing_open_session_count,
        unit_consistency_passed=unit_consistency_passed,
        identity_continuity_passed=identity_continuity_passed,
        event_contamination_status=event_contamination_status,
        unresolved_event_candidate_id=unresolved_event_candidate_id,
        source_revision_status=source_revision_status,
        adjustment_factor_verified=adjustment_factor_verified,
        share_unit_basis_matched=share_unit_basis_matched,
        valuation_unit_basis_matched=valuation_unit_basis_matched,
        economic_flow_eligible=economic_flow_eligible,
        nav_flow_eligible=nav_flow_eligible,
        close_flow_eligible=close_flow_eligible,
        flow_block_reason=flow_block_reason,
    )


def estimate_flow_nav(
    economic_delta_shares: float,
    nav: float,
    gate: ShareDeltaGate,
) -> float | None:
    """NAV口径估算一级市场净申赎规模。仅当两层门控+nav门控通过。"""
    if not (gate.flow_allowed and gate.nav_flow_eligible):
        return None
    return economic_delta_shares * nav


def estimate_flow_close(
    economic_delta_shares: float,
    close: float,
    gate: ShareDeltaGate,
) -> float | None:
    """收盘价口径估算一级市场净申赎规模。仅当两层门控+close门控通过。"""
    if not (gate.flow_allowed and gate.close_flow_eligible):
        return None
    return economic_delta_shares * close
