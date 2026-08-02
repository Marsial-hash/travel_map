"""Canonical 层构建：从 Normalized 数据生成 canonical_etf_flow_daily 等表。

实现：
- canonical_economic_delta_shares（非 float，用 Decimal/Int）
- 四层门控（日期/经济/NAV/Close）
- 使用实际 conflict_resolution_status
- 覆盖起点拆分
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EventContaminationStatus(StrEnum):
    CLEAN = "CLEAN"
    CONFIRMED_ADJUSTMENT_APPLIED = "CONFIRMED_ADJUSTMENT_APPLIED"
    UNRESOLVED_SHARE_JUMP = "UNRESOLVED_SHARE_JUMP"
    POSSIBLE_UNIT_CHANGE = "POSSIBLE_UNIT_CHANGE"
    POSSIBLE_SOURCE_REVISION = "POSSIBLE_SOURCE_REVISION"
    IDENTITY_DISCONTINUITY = "IDENTITY_DISCONTINUITY"


class ConflictResolutionStatus(StrEnum):
    NO_CONFLICT = "NO_CONFLICT"
    WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
    RESOLVED_PRIMARY_ACCEPTED = "RESOLVED_PRIMARY_ACCEPTED"
    RESOLVED_SECONDARY_ACCEPTED = "RESOLVED_SECONDARY_ACCEPTED"
    WARNING_ACCEPTED = "WARNING_ACCEPTED"
    MANUAL_REVIEW_PENDING = "MANUAL_REVIEW_PENDING"
    QUARANTINED = "QUARANTINED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


CONFLICT_ALLOW = {
    ConflictResolutionStatus.NO_CONFLICT,
    ConflictResolutionStatus.WITHIN_TOLERANCE,
    ConflictResolutionStatus.RESOLVED_PRIMARY_ACCEPTED,
    ConflictResolutionStatus.WARNING_ACCEPTED,
}


class BlockReason(StrEnum):
    DATA_MISSING = "DATA_MISSING"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    IDENTITY_DISCONTINUITY = "IDENTITY_DISCONTINUITY"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNRESOLVED_SHARE_JUMP = "UNRESOLVED_SHARE_JUMP"
    POSSIBLE_SOURCE_REVISION = "POSSIBLE_SOURCE_REVISION"
    NAV_NOT_AVAILABLE_AT_EVALUATION = "NAV_NOT_AVAILABLE_AT_EVALUATION"
    CLOSE_NOT_AVAILABLE = "CLOSE_NOT_AVAILABLE"
    NON_CONSECUTIVE_OPEN_SESSION = "NON_CONSECUTIVE_OPEN_SESSION"
    OTHER_EXPLAINED = "OTHER_EXPLAINED"
    UNKNOWN = "UNKNOWN"


@dataclass
class FlowGateResult:
    trade_date: str
    open_session_distance: int
    missing_open_session_count: int
    daily_flow_eligible: bool
    economic_flow_eligible: bool
    nav_flow_eligible: bool
    close_flow_eligible: bool
    flow_block_reason: str | None
    canonical_economic_delta_shares: Decimal | None
    canonical_delta_raw_shares: Decimal | None
    estimated_flow_nav: Decimal | None
    estimated_flow_close: Decimal | None


def evaluate_flow_gate(
    trade_date: str,
    *,
    open_session_distance: int,
    missing_open_session_count: int,
    unit_consistency_passed: bool = True,
    identity_continuity_passed: bool = True,
    event_contamination_status: EventContaminationStatus = EventContaminationStatus.CLEAN,
    conflict_resolution_status: ConflictResolutionStatus = ConflictResolutionStatus.NO_CONFLICT,
    source_revision_status: str = "CLEAN",
    adjustment_factor_verified: bool = False,
    share_unit_basis_matched: bool = True,
    valuation_unit_basis_matched: bool = True,
    official_event_evidence_verified: bool = False,
    raw_delta_shares: Decimal | None = None,
    adjusted_delta_shares: Decimal | None = None,
    nav_available: bool = False,
    nav_unit_matched: bool = False,
    nav_research_available: bool = False,
    nav: Decimal | None = None,
    close_available: bool = False,
    close_trade_date_matches: bool = False,
    close_unit_matched: bool = False,
    close_research_available: bool = False,
    close: Decimal | None = None,
) -> FlowGateResult:
    """四层门控评估（非 float，用 Decimal）。"""
    # 日期门控
    daily_flow_eligible = open_session_distance == 1 and missing_open_session_count == 0

    # 冲突实际状态
    conflict_ok = conflict_resolution_status in CONFLICT_ALLOW

    # 事件污染
    if event_contamination_status == EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED:
        event_ok = (
            adjustment_factor_verified
            and share_unit_basis_matched
            and valuation_unit_basis_matched
            and official_event_evidence_verified
        )
    else:
        event_ok = event_contamination_status in (
            EventContaminationStatus.CLEAN,
            EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
        )

    revision_ok = source_revision_status != "UNRESOLVED"

    economic_flow_eligible = (
        daily_flow_eligible
        and unit_consistency_passed
        and identity_continuity_passed
        and conflict_ok
        and event_ok
        and revision_ok
    )

    # 经济 delta（非 float）
    economic_delta: Decimal | None = None
    if economic_flow_eligible:
        if event_contamination_status == EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED:
            economic_delta = adjusted_delta_shares  # 单位统一后（已验证）
        else:
            economic_delta = raw_delta_shares  # 普通日
    else:
        economic_delta = None

    # NAV / Close 独立门控
    nav_flow_eligible = economic_flow_eligible and nav_available and nav_unit_matched and nav_research_available
    close_flow_eligible = (
        economic_flow_eligible
        and close_available
        and close_trade_date_matches
        and close_unit_matched
        and close_research_available
    )

    # 阻断原因
    reason: str | None = None
    if not daily_flow_eligible:
        reason = BlockReason.NON_CONSECUTIVE_OPEN_SESSION.value
    elif not unit_consistency_passed:
        reason = BlockReason.UNIT_MISMATCH.value
    elif not identity_continuity_passed:
        reason = BlockReason.IDENTITY_DISCONTINUITY.value
    elif not conflict_ok:
        reason = BlockReason.SOURCE_CONFLICT.value
    elif event_contamination_status == EventContaminationStatus.UNRESOLVED_SHARE_JUMP:
        reason = BlockReason.UNRESOLVED_SHARE_JUMP.value
    elif not event_ok:
        reason = BlockReason.OTHER_EXPLAINED.value
    elif not revision_ok:
        reason = BlockReason.POSSIBLE_SOURCE_REVISION.value

    # 流量估算
    flow_nav: Decimal | None = None
    flow_close: Decimal | None = None
    if nav_flow_eligible and economic_delta is not None and nav is not None:
        flow_nav = economic_delta * nav
    if close_flow_eligible and economic_delta is not None and close is not None:
        flow_close = economic_delta * close

    return FlowGateResult(
        trade_date=trade_date,
        open_session_distance=open_session_distance,
        missing_open_session_count=missing_open_session_count,
        daily_flow_eligible=daily_flow_eligible,
        economic_flow_eligible=economic_flow_eligible,
        nav_flow_eligible=nav_flow_eligible,
        close_flow_eligible=close_flow_eligible,
        flow_block_reason=reason,
        canonical_economic_delta_shares=economic_delta,
        canonical_delta_raw_shares=raw_delta_shares,
        estimated_flow_nav=flow_nav,
        estimated_flow_close=flow_close,
    )
