"""成交额对账：Canonical真实成交额 vs Reference估算成交额（6 ETF × 60日）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.index_turnover import SohuHisqAdapter  # noqa: E402
from data_pipeline.adapters.tencent_quotes import TencentQuotesAdapter  # noqa: E402
from data_pipeline.normalization.units import estimate_turnover_yi  # noqa: E402


def run(etfs: list[tuple[str, str]], start: str, end: str) -> dict[str, Any]:
    """对账：每ETF逐日 真实成交额(亿) vs 估算成交额(亿)。"""
    quotes = TencentQuotesAdapter()
    sohu = SohuHisqAdapter()
    summary: dict[str, Any] = {"per_etf": {}, "overall": {}}
    all_abs_errors: list[float] = []
    all_rel_errors: list[float] = []

    for code, exchange in etfs:
        try:
            kline = quotes.fetch_fqkline(code, exchange, start, end)
            sohu_rows = {r.date: r for r in sohu.fetch_etf(code, start, end)}
        except Exception as e:  # noqa: BLE001
            summary["per_etf"][code] = {"error": str(e)[:200]}
            continue
        rows = []
        for k in kline:
            d = k["date"]
            typical = (k["high"] + k["low"] + k["close"]) / 3
            est_yi = estimate_turnover_yi(typical, k["volume"])
            real_yi = sohu_rows[d].amount_wan / 1e4 if d in sohu_rows else None
            if real_yi is None:
                continue
            abs_err = abs(est_yi - real_yi)
            rel_err = abs_err / real_yi if real_yi else None
            row = {
                "date": d,
                "real_turnover_yi": real_yi,
                "est_turnover_yi": est_yi,
                "abs_error": abs_err,
                "rel_error": rel_err,
            }
            rows.append(row)
            all_abs_errors.append(abs_err)
            if rel_err is not None:
                all_rel_errors.append(rel_err)
        if rows:
            abs_list = [r["abs_error"] for r in rows]
            rel_list = [r["rel_error"] for r in rows if r["rel_error"] is not None]
            summary["per_etf"][code] = {
                "n_days": len(rows),
                "abs_error_mean": round(sum(abs_list) / len(abs_list), 6),
                "abs_error_median": round(sorted(abs_list)[len(abs_list) // 2], 6),
                "abs_error_max": round(max(abs_list), 6),
                "rel_error_mean_pct": round(sum(rel_list) / len(rel_list) * 100, 4) if rel_list else None,
                "rel_error_max_pct": round(max(rel_list) * 100, 4) if rel_list else None,
                "abnormal_dates": [r["date"] for r in rows if r["rel_error"] is not None and r["rel_error"] > 0.05],
            }
        else:
            summary["per_etf"][code] = {"n_days": 0, "error": "no overlapping days"}

    if all_abs_errors:
        summary["overall"] = {
            "n": len(all_abs_errors),
            "abs_error_mean": round(sum(all_abs_errors) / len(all_abs_errors), 6),
            "abs_error_median": round(sorted(all_abs_errors)[len(all_abs_errors) // 2], 6),
            "abs_error_max": round(max(all_abs_errors), 6),
            "rel_error_mean_pct": round(sum(all_rel_errors) / len(all_rel_errors) * 100, 4) if all_rel_errors else None,
        }
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "turnover_reconciliation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = run(
        [("510300", "SH"), ("510310", "SH"), ("159919", "SZ"), ("510050", "SH"), ("510500", "SH"), ("159845", "SZ")],
        "2026-05-05",
        "2026-07-31",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
