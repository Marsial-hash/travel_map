"""份额差分门控测试（J-01/M-03 + 补丁12-1/2/9）。"""
from __future__ import annotations

from datetime import date

import pytest

from data_pipeline.execution.share_delta_gate import (
    EventContaminationStatus,
    estimate_flow_close,
    estimate_flow_nav,
    evaluate_share_delta_gate,
)


class TestDailyFlowEligible:
    def test_consecutive_open_days(self) -> None:
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 7),
            previous_observation_date=date(2026, 5, 6),
            open_session_distance=1,
            missing_open_session_count=0,
        )
        assert gate.daily_flow_eligible is True
        assert gate.economic_flow_eligible is True
        assert gate.flow_block_reason is None

    def test_missing_one_open_day(self) -> None:
        """周一->周三，周二缺失: daily_flow_eligible=false。"""
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 8),
            previous_observation_date=date(2026, 5, 6),
            open_session_distance=2,
            missing_open_session_count=1,
        )
        assert gate.daily_flow_eligible is False
        assert gate.interval_flow_only is True
        assert gate.flow_block_reason == "NON_CONSECUTIVE_SHARE_OBSERVATIONS"

    def test_weekend_only(self) -> None:
        """周五->周一：distance=1, missing=0 → eligible。"""
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 11),
            previous_observation_date=date(2026, 5, 8),
            open_session_distance=1,
            missing_open_session_count=0,
        )
        assert gate.daily_flow_eligible is True


class TestEconomicFlowEligible:
    def test_unresolved_share_jump_blocks(self) -> None:
        """M-03: 510300 2026-01-28 跳变即使日期连续也阻断。"""
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 1, 28),
            previous_observation_date=date(2026, 1, 27),
            open_session_distance=1,
            missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.UNRESOLVED_SHARE_JUMP,
            unresolved_event_candidate_id="EVT-510300-20260128",
        )
        assert gate.daily_flow_eligible is True
        assert gate.economic_flow_eligible is False
        assert "UNRESOLVED_SHARE_JUMP" in (gate.flow_block_reason or "")

    def test_confirmed_adjustment_requires_all_verified(self) -> None:
        """补丁12-2: CONFIRMED_ADJUSTMENT_APPLIED 须三验证全true。"""
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 1, 28),
            previous_observation_date=date(2026, 1, 27),
            open_session_distance=1,
            missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
            adjustment_factor_verified=False,
            share_unit_basis_matched=True,
            valuation_unit_basis_matched=True,
        )
        assert gate.economic_flow_eligible is False
        assert "ADJUSTMENT_NOT_VERIFIED" in (gate.flow_block_reason or "")

        gate_ok = evaluate_share_delta_gate(
            trade_date=date(2026, 1, 28),
            previous_observation_date=date(2026, 1, 27),
            open_session_distance=1,
            missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.CONFIRMED_ADJUSTMENT_APPLIED,
            adjustment_factor_verified=True,
            share_unit_basis_matched=True,
            valuation_unit_basis_matched=True,
        )
        assert gate_ok.economic_flow_eligible is True

    def test_unit_inconsistency_blocks(self) -> None:
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 7),
            previous_observation_date=date(2026, 5, 6),
            open_session_distance=1,
            missing_open_session_count=0,
            unit_consistency_passed=False,
        )
        assert gate.economic_flow_eligible is False
        assert gate.flow_block_reason == "UNIT_INCONSISTENCY"


class TestFlowEstimation:
    def test_flow_nav_requires_gates(self) -> None:
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 7),
            previous_observation_date=date(2026, 5, 6),
            open_session_distance=1,
            missing_open_session_count=0,
        )
        gate.nav_flow_eligible = True
        flow = estimate_flow_nav(100_000_000, 4.6069, gate)
        assert flow == pytest.approx(460_690_000)

    def test_flow_nav_blocked_by_jump(self) -> None:
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 1, 28),
            previous_observation_date=date(2026, 1, 27),
            open_session_distance=1,
            missing_open_session_count=0,
            event_contamination_status=EventContaminationStatus.UNRESOLVED_SHARE_JUMP,
        )
        gate.nav_flow_eligible = True
        assert estimate_flow_nav(100_000_000, 4.6, gate) is None

    def test_flow_close(self) -> None:
        gate = evaluate_share_delta_gate(
            trade_date=date(2026, 5, 7),
            previous_observation_date=date(2026, 5, 6),
            open_session_distance=1,
            missing_open_session_count=0,
        )
        gate.close_flow_eligible = True
        flow = estimate_flow_close(100_000_000, 4.605, gate)
        assert flow == pytest.approx(460_500_000)
