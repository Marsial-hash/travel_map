"""生命周期事件扫描（三层流程）。

1. 份额异常/名称/代码历史筛选候选日期
2. 对候选日期前后90日检索公告
3. 确认事件制作Fixture；未确认保留 UNRESOLVED_SHARE_JUMP

510300 2026-01-28 跳变 -60.28亿份 → 调查候选（不得预先认定为折算）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

CANDIDATES = [
    {
        "event_candidate_id": "EVT-510300-20260128",
        "internal_instrument_id": "INST-510300",
        "event_date": "2026-01-28",
        "raw_share_change": None,  # 待份额源实测
        "reference_adjusted_share_change": -60.282,  # 亿份（参考站series实测EV006）
        "candidate_event_type": "UNKNOWN_EVENT",
        "official_evidence_found": False,
        "official_document": None,
        "verification_status": "UNRESOLVED_SHARE_JUMP",
        "reviewer": "MODEL_CROSS_CHECKED",
    }
]


def run() -> dict[str, Any]:
    """输出调查候选；无官方证据不得升级为 CONFIRMED_SHARE_ADJUSTMENT_EVENT。"""
    result = {
        "scan_range": "成立以来（候选驱动，非全量下载）",
        "candidates": CANDIDATES,
        "confirmed_events": [],
        "note": "只有取得基金管理人/交易所/正式基金公告证据后才升级CONFIRMED；未确认只进异常测试",
    }
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "lifecycle_events.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
