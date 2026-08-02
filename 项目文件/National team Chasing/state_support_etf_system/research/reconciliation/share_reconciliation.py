"""份额对账（三层）：原始份额 vs 独立源；调整份额 vs Reference复权；raw差分 vs adjusted差分。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.tencent_quotes import TencentQuotesAdapter  # noqa: E402


def run(etfs: list[tuple[str, str]]) -> dict[str, Any]:
    """对账A：Tushare原始份额(从spike原始文件读) vs 腾讯当日份额。"""
    quotes = TencentQuotesAdapter()
    summary: dict[str, Any] = {"reconciliation_a": {}, "note": "对账B/C在Phase 1A-C完成（需调整事件验证）"}
    for code, exchange in etfs:
        raw_path = PROJECT_ROOT / "warehouse" / "raw" / "phase0b" / f"fund_share_{code}.json"
        entry: dict[str, Any] = {}
        if raw_path.exists():
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            if raw:
                # 最近一条记录
                latest = max(raw, key=lambda r: str(r["trade_date"]))
                latest_date = str(latest["trade_date"])
                fd_share_wan = float(latest["fd_share"])
                entry["tushare_latest_date"] = latest_date
                entry["tushare_fd_share_wan"] = fd_share_wan
                entry["tushare_shares_yi"] = fd_share_wan / 1e4  # 万份 -> 亿份
        try:
            q = quotes.fetch_quote(code, exchange)
            if q and q.total_shares:
                tencent_yi = q.total_shares / 1e8
                entry["tencent_total_shares_yi"] = tencent_yi
                if "tushare_shares_yi" in entry and entry["tushare_shares_yi"]:
                    rel_diff = abs(entry["tushare_shares_yi"] - tencent_yi) / tencent_yi
                    entry["rel_diff"] = round(rel_diff, 8)
                    entry["verdict"] = (
                        "PASS_WITHIN_1E-8" if rel_diff <= 1e-8 else "CHECK"
                    )
        except Exception as e:  # noqa: BLE001
            entry["error"] = str(e)[:200]
        summary["reconciliation_a"][code] = entry
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "share_reconciliation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    etfs = [("510300", "SH"), ("510310", "SH"), ("159919", "SZ"), ("510050", "SH"), ("510500", "SH"), ("159845", "SZ")]
    result = run(etfs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
