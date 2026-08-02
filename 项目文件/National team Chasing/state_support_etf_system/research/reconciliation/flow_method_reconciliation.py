"""三种一级市场流量估算方法对比（NAV口径 / 收盘价口径 / 参考均价口径）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.execution.share_delta_gate import (  # noqa: E402
    EventContaminationStatus,  # noqa: E402
    estimate_flow_close,
    estimate_flow_nav,
    evaluate_share_delta_gate,
)


def run() -> dict[str, Any]:
    """基于已知数据做方法对比示例：510300 2026-07-30（delta=5.364亿份，连续日）。"""
    # delta 单位转换：参考站 亿份 -> 份
    delta_yi = 5.364
    delta_shares = delta_yi * 1e8
    nav = 4.6069  # 2026-07-30 NAV（天天基金实测）
    close = 4.605  # 2026-07-30 收盘

    gate = evaluate_share_delta_gate(
        trade_date="2026-07-30",  # type: ignore[arg-type]
        previous_observation_date="2026-07-29",  # type: ignore[arg-type]
        open_session_distance=1,
        missing_open_session_count=0,
        event_contamination_status=EventContaminationStatus.CLEAN,
    )
    # 修正 nav/close 可用性（NAV T+1 09:30 可用 → nav_flow_eligible 应为 True 在 T+1 之后）
    gate.nav_flow_eligible = True
    gate.close_flow_eligible = True

    flow_nav = estimate_flow_nav(delta_shares, nav, gate)
    flow_close = estimate_flow_close(delta_shares, close, gate)
    # 参考均价口径：参考站 delta(亿份) × avg_price_est(元) = 亿元
    flow_ref = delta_yi * 4.67

    result = {
        "sample": "510300 2026-07-30",
        "delta_shares": delta_shares,
        "flow_nav_yuan": flow_nav,
        "flow_nav_yi": round(flow_nav / 1e8, 4) if flow_nav else None,
        "flow_close_yi": round(flow_close / 1e8, 4) if flow_close else None,
        "flow_reference_avg_price_yi": round(flow_ref, 4),
        "gate": {
            "daily_flow_eligible": gate.daily_flow_eligible,
            "economic_flow_eligible": gate.economic_flow_eligible,
            "flow_block_reason": gate.flow_block_reason,
        },
        "note": "三口径均为估算(is_cash_flow_observed=false)，非官方净申赎",
    }
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "flow_method_comparison.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
