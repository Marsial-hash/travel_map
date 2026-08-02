#!/usr/bin/env python3
"""可靠性燃烧测试脚本（J-05）。

目标：连续5-10个交易日自动采集；当前环境无法跨日时：
- 脚本完整创建
- 批量测试历史日期
- 对当前日期多次间隔采集
- reliability_status 保持 UNVERIFIED
- 不得虚假宣称完成燃烧测试
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.tencent_quotes import TencentQuotesAdapter  # noqa: E402


def run(etfs: list[tuple[str, str]], iterations: int, interval_seconds: int) -> dict[str, Any]:
    quotes = TencentQuotesAdapter()
    records: list[dict[str, Any]] = []
    for i in range(iterations):
        iter_record: dict[str, Any] = {
            "iteration": i + 1,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "sources": {},
        }
        for code, exchange in etfs:
            try:
                q = quotes.fetch_quote(code, exchange)
                iter_record["sources"][code] = {
                    "ok": q is not None,
                    "close": q.close if q else None,
                    "total_shares": q.total_shares if q else None,
                }
            except Exception as e:  # noqa: BLE001
                iter_record["sources"][code] = {"ok": False, "error": str(e)[:200]}
        iter_record["finished_at"] = datetime.now().isoformat(timespec="seconds")
        records.append(iter_record)
        if i < iterations - 1:
            time.sleep(interval_seconds)

    ok_flags = [bool(v.get("ok")) for r in records for v in r["sources"].values()]
    success = sum(ok_flags)
    total = len(ok_flags)
    summary: dict[str, Any] = {
        "iterations": iterations,
        "interval_seconds": interval_seconds,
        "success_rate": round(success / total, 4) if total else 0.0,
        "reliability_status": "UNVERIFIED",
        "note": "未完成连续多日燃烧测试；仅完成当前会话间隔采集，live_signal_approved=false",
        "records": records,
    }
    out_path = PROJECT_ROOT / "warehouse" / "metadata" / "burn_in_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="source burn-in test")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    result = run(
        [("510300", "SH"), ("510310", "SH"), ("159919", "SZ"), ("510050", "SH"), ("510500", "SH"), ("159845", "SZ")],
        args.iterations,
        args.interval,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
