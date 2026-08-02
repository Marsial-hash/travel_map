"""真实交易日历物化：Tushare trade_cal → market_calendar（SSE+SZSE 分开拉取）。

next_open_date 为派生字段（lead over open dates）。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from data_pipeline.adapters.tushare_calendar import get_token

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse" / "calendar"


def materialize_market_calendar(start: str, end: str, token: str | None = None) -> dict[str, Any]:
    """物化 SSE+SZSE 交易日历。返回元数据。"""
    import tushare as ts

    token = token or get_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN not detected")
    pro = ts.pro_api(token)
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {}
    for exchange in ("SSE", "SZSE"):
        df = pro.trade_cal(exchange=exchange, start_date=start.replace("-", ""), end_date=end.replace("-", ""))
        df = df.sort_values("cal_date").reset_index(drop=True)
        # 派生 next_open_date / previous_open_date: lead/lag over open dates
        open_idx = df.index[df["is_open"] == 1].tolist()
        next_map: dict[str, str | None] = {}
        prev_map: dict[str, str | None] = {}
        for i, idx in enumerate(open_idx):
            next_map[df.loc[idx, "cal_date"]] = df.loc[open_idx[i + 1], "cal_date"] if i + 1 < len(open_idx) else None
            prev_map[df.loc[idx, "cal_date"]] = df.loc[open_idx[i - 1], "cal_date"] if i > 0 else None
        df["next_open_date"] = df["cal_date"].map(next_map)
        df["previous_open_date"] = df["cal_date"].map(prev_map)
        # 时间字段
        now = datetime.now().isoformat(timespec="seconds")
        out = pl.from_pandas(df)
        out = out.with_columns(
            pl.lit("Asia/Shanghai").alias("timezone"),
            pl.lit(now).alias("system_valid_from"),
            pl.lit(None).alias("system_valid_to"),
            pl.lit("v1-lead-over-open-dates").alias("next_open_date_calculation_version"),
            pl.lit("TUSHARE_TRADE_CAL").alias("calendar_source_version"),
        )
        path = WAREHOUSE_DIR / f"market_calendar_{exchange}.parquet"
        out.write_parquet(path)
        open_count = int(df[df["is_open"] == 1].shape[0])
        result[exchange] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "rows": len(out),
            "open_days": open_count,
            "date_start": start,
            "date_end": end,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }

    # 对账：SSE vs SZSE 开放日集合
    sse = pl.read_parquet(WAREHOUSE_DIR / "market_calendar_SSE.parquet")
    szse = pl.read_parquet(WAREHOUSE_DIR / "market_calendar_SZSE.parquet")
    sse_open = set(sse.filter(pl.col("is_open") == 1).get_column("cal_date").to_list())
    szse_open = set(szse.filter(pl.col("is_open") == 1).get_column("cal_date").to_list())
    result["_reconciliation"] = {
        "sse_open_days": len(sse_open),
        "szse_open_days": len(szse_open),
        "identical": sse_open == szse_open,
    }
    return result


if __name__ == "__main__":
    r = materialize_market_calendar("2015-01-01", "2026-07-31")
    for k, v in r.items():
        if k == "_reconciliation":
            print("reconciliation:", v)
        else:
            print(f"{k}: {v['rows']} rows, {v['open_days']} open days, {v['sha256'][:12]}")
