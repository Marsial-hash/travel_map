"""指数成交额对账：搜狐供应商字段 vs 参考站JSON有限样本。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.index_turnover import SohuHisqAdapter  # noqa: E402

# 9个趋势分组：index_key -> (index_code, 参考站样本文件)
TREND_GROUPS = {
    "hs300": ("000300", "fixtures/reference_compatibility/index_turnover_hs300.json"),
    "sse50": ("000016", None),
    "sse180": ("000010", None),
    "csi500": ("000905", None),
    "csi800": ("000906", None),
    "csi1000": ("000852", None),
    "chinext": ("399006", None),
    "star50": ("000688", None),
    "sz100": ("399330", None),
}


def run(start: str, end: str) -> dict[str, Any]:
    sohu = SohuHisqAdapter()
    summary: dict[str, Any] = {}
    for index_key, (index_code, ref_file) in TREND_GROUPS.items():
        entry: dict[str, Any] = {"index_code": index_code, "status": "ok"}
        try:
            rows = sohu.fetch_index(index_code, start, end)
            by_date = {r.date: r.amount_wan / 1e4 for r in rows}  # 万元 -> 亿元
            entry["sohu_days"] = len(by_date)
            entry["sohu_sample"] = {d: v for d, v in sorted(by_date.items())[:3]}
            if ref_file:
                ref_path = PROJECT_ROOT / ref_file
                if ref_path.exists():
                    ref = json.loads(ref_path.read_text(encoding="utf-8"))
                    ref_by_date = {r["date"]: r["turnover_yi"] for r in ref["rows"]}
                    overlap = set(by_date) & set(ref_by_date)
                    diffs = [abs(by_date[d] - ref_by_date[d]) / ref_by_date[d] for d in overlap if ref_by_date[d]]
                    entry["reference_overlap_days"] = len(overlap)
                    entry["reference_max_rel_diff_pct"] = round(max(diffs) * 100, 4) if diffs else None
                    entry["reference_mean_rel_diff_pct"] = round(sum(diffs) / len(diffs) * 100, 4) if diffs else None
                else:
                    entry["reference_file"] = "MISSING"
        except Exception as e:  # noqa: BLE001
            entry["status"] = "error"
            entry["error"] = str(e)[:200]
        summary[index_key] = entry
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "index_turnover_reconciliation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = run("2026-05-05", "2026-07-31")
    print(json.dumps(result, ensure_ascii=False, indent=2))
