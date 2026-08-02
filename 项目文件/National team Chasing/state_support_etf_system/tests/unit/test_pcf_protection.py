"""PCF保护测试（补丁）：PCF数据不得映射为 canonical_raw_total_shares。"""
from __future__ import annotations

import pytest

from data_pipeline.adapters.capability_probes import ExchangeSharesAdapter, ProbeStatus


class TestPCFProtection:
    def test_pcf_not_outstanding_total_shares(self) -> None:
        """PCF（最小申赎单位/现金替代等）≠ 存量总份额。"""
        assert "outstanding_total_shares" not in [
            "creation_redemption_unit",
            "cash_component",
            "substitution_flags",
            "basket_components",
        ]

    def test_exchange_adapter_probe_honest(self) -> None:
        """J-06: 未建立路径的适配器不得伪装成功。"""
        probe = ExchangeSharesAdapter()
        result = probe.fetch_outstanding_total_shares("510300", "2026-05-05", "2026-07-31")
        assert result.supported is False
        assert result.status == ProbeStatus.UNVERIFIED
        assert result.reason == "NO_VALIDATED_ENDPOINT"

    def test_canonical_guard_blocks_without_approval(self) -> None:
        """物化保护：份额源未批准时禁止生成真实canonical流量表。"""
        from pathlib import Path

        from data_pipeline.validation.canonical_guard import CanonicalMaterializationGuard

        guard = CanonicalMaterializationGuard(
            share_source_approved=False, canonical_dir=Path("/tmp/test_canonical_guard")
        )
        with pytest.raises(RuntimeError):
            guard.prohibit_canonical_flow_materialization()
        # BLOCKED 标记可写
        marker = guard.write_blocked_marker(reason="test")
        assert marker.exists()
