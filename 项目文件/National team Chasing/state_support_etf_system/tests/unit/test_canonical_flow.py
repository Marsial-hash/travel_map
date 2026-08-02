"""Canonical 经济流量门控测试（四层门控 + 冲突状态分离 + 非 float）。"""
from __future__ import annotations

from decimal import Decimal

from data_pipeline.execution.canonical_flow import (
    BlockReason,
    ConflictResolutionStatus,
    EventContaminationStatus,
    evaluate_flow_gate,
)


class TestFlowGates:
    def test_clean_consecutive_day(self) -> None:
        """普通连续日：economic_delta=raw delta，NAV/Close 均可生成。"""
        g = evaluate_flow_gate(
            "2026-05-07",
            open_session_distance=1,
            missing_open_session_count=0,
            raw_delta_shares=Decimal("1000000"),
            adjusted_delta_shares=Decimal("1000000"),
            nav_available=True, nav_unit_matched=True, nav_research_available=True,
            nav=Decimal("4.60"),
            close_available=True, close_trade_date_matches=True,
            close_unit_matched=True, close_research_available=True, close=Decimal("4.61"),
        )
        assert g.daily_flow_eligible is True
        assert g.economic_flow_eligible is True
        assert g.nav_flow_eligible is True
        assert g.close_flow_eligible is True
        assert g.canonical_economic_delta_shares == Decimal("1000000")
        assert g.estimated_flow_nav == Decimal("4600000.0")
        assert g.estimated_flow_close == Decimal("4610000.0")
        assert g.flow_block_reason is None

    def test_unresolved_share_jump_blocks_all_flow(self) -> None:
        """510300 2026-01-28 Canonical源跳变 → economic_delta=NULL, 阻断NAV/Close。"""
        g = evaluate_flow_gate(
            "2026-01-28",
            open_session_distance=1,
            missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.UNRESOLVED_SHARE_JUMP,
            raw_delta_shares=Decimal("-6028200000"),  # -60.28亿份
            nav_available=True, nav=Decimal("4.6"),
            close_available=True, close=Decimal("4.6"),
        )
        assert g.daily_flow_eligible is True  # 日期连续
        assert g.economic_flow_eligible is False
        assert g.nav_flow_eligible is False
        assert g.close_flow_eligible is False
        assert g.canonical_economic_delta_shares is None
        assert g.estimated_flow_nav is None
        assert g.estimated_flow_close is None
        assert g.flow_block_reason == BlockReason.UNRESOLVED_SHARE_JUMP.value

    def test_confirmed_adjustment_requires_verification(self) -> None:
        """CONFIRMED_ADJUSTMENT_APPLIED 须四验证全 true。"""
        # 未验证 → 阻断
        g1 = evaluate_flow_gate(
            "2026-01-28",
            open_session_distance=1, missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
            adjustment_factor_verified=False, share_unit_basis_matched=True,
            valuation_unit_basis_matched=True, official_event_evidence_verified=True,
            raw_delta_shares=Decimal("100"), adjusted_delta_shares=Decimal("50"),
        )
        assert g1.economic_flow_eligible is False
        # 全验证 → 放行且用 adjusted delta
        g2 = evaluate_flow_gate(
            "2026-01-28",
            open_session_distance=1, missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
            adjustment_factor_verified=True, share_unit_basis_matched=True,
            valuation_unit_basis_matched=True, official_event_evidence_verified=True,
            raw_delta_shares=Decimal("100"), adjusted_delta_shares=Decimal("50"),
            nav_available=True, nav=Decimal("2"), close_available=True, close=Decimal("2"),
        )
        assert g2.economic_flow_eligible is True
        assert g2.canonical_economic_delta_shares == Decimal("50")

    def test_conflict_status_gating(self) -> None:
        """门控使用实际冲突状态；QUARANTINED/BLOCKED 阻断。"""
        g_blocked = evaluate_flow_gate(
            "2026-05-07",
            open_session_distance=1, missing_open_session_count=0,
            conflict_resolution_status=ConflictResolutionStatus.BLOCKED,
            raw_delta_shares=Decimal("100"),
        )
        assert g_blocked.economic_flow_eligible is False
        assert g_blocked.flow_block_reason == BlockReason.SOURCE_CONFLICT.value

        g_ok = evaluate_flow_gate(
            "2026-05-07",
            open_session_distance=1, missing_open_session_count=0,
            conflict_resolution_status=ConflictResolutionStatus.WITHIN_TOLERANCE,
            raw_delta_shares=Decimal("100"),
        )
        assert g_ok.economic_flow_eligible is True

    def test_non_consecutive_blocks(self) -> None:
        """缺失开放日 → daily_flow_eligible=false。"""
        g = evaluate_flow_gate(
            "2026-05-11",
            open_session_distance=2, missing_open_session_count=1,
            raw_delta_shares=Decimal("100"),
        )
        assert g.daily_flow_eligible is False
        assert g.economic_flow_eligible is False
        assert g.flow_block_reason == BlockReason.NON_CONSECUTIVE_OPEN_SESSION.value

    def test_nav_and_close_independent(self) -> None:
        """NAV 缺失不影响 Close；反之亦然（独立放行）。"""
        g = evaluate_flow_gate(
            "2026-05-07",
            open_session_distance=1, missing_open_session_count=0,
            raw_delta_shares=Decimal("1000000"),
            nav_available=False,  # NAV 缺失
            close_available=True, close_trade_date_matches=True,
            close_unit_matched=True, close_research_available=True, close=Decimal("4.6"),
        )
        assert g.nav_flow_eligible is False
        assert g.close_flow_eligible is True
        assert g.estimated_flow_nav is None
        assert g.estimated_flow_close == Decimal("4600000.0")
