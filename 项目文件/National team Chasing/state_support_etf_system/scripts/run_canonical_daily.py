#!/usr/bin/env python3
"""Phase 1A-C 日批增量（按数据集水位线推进，不生成实时信号）。

用法:
  python scripts/run_canonical_daily.py --trade-date latest
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.tushare_calendar import get_token  # noqa: E402
from data_pipeline.execution.watermark import WatermarkStatus, WatermarkTracker  # noqa: E402
from scripts.run_canonical_backfill import (  # noqa: E402
    build_canonical_share_daily,
    fetch_fund_share_history,
    latest_completed_trade_date,
)


def run_daily(trade_date: str) -> dict[str, Any]:
    token = get_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN not detected")
    calendar = pl.read_parquet(PROJECT_ROOT / "warehouse" / "calendar" / "market_calendar_SSE.parquet")
    latest = latest_completed_trade_date(calendar)
    target = latest if trade_date == "latest" else trade_date.replace("-", "")
    # 只抓目标日附近数据（增量）
    start = f"{target[:4]}-01-01"
    end = f"{target[:4]}-12-31"
    print(f"日批: 目标交易日={target} (latest_completed={latest})")

    # 按数据集水位线：份额/行情/NAV 各推进
    wm = WatermarkTracker()
    results: dict[str, Any] = {}
    for code in ["510300", "510310", "159919", "510050", "510500", "159845"]:
        ex = "SH" if code.startswith("51") else "SZ"
        raw_share = fetch_fund_share_history(token, f"{code}.{ex}", start, end)
        share_daily = build_canonical_share_daily(raw_share, calendar, code)
        latest_share = str(raw_share["trade_date"].max()) if not raw_share.is_empty() else None
        results[code] = {"share_rows": len(share_daily), "latest_share_date": latest_share}
    wm.set_watermark("ETF_SHARE", "TUSHARE_FUND_SHARE", "TUSHARE_FUND_SHARE_V1_CONSERVATIVE",
                     latest_completed_trade_date=date.fromisoformat(target[:4] + "-" + target[4:6] + "-" + target[6:]),
                     latest_observed_trade_date=date.fromisoformat(target[:4] + "-" + target[4:6] + "-" + target[6:]),
                     watermark_status=WatermarkStatus.UP_TO_DATE)
    results["flow_publication_cutoff"] = str(wm.flow_publication_cutoff())
    results["note"] = "日批仅推进缺失数据，不生成实时信号，不执行买卖逻辑"
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trade-date", default="latest")
    args = parser.parse_args()
    import json

    print(json.dumps(run_daily(args.trade_date), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
