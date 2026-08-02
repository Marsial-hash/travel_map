"""Phase 1A-C 修复模块：份额语义分层 + 覆盖起点 + 日期统一（R-01/R-02/R-07）。"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"

# 官方上市日（Tushare fund_basic list_date 实测）
LIST_DATES = {
    "510300": date(2012, 5, 28),
    "510310": date(2013, 3, 25),
    "159919": date(2012, 5, 28),
    "510050": date(2005, 2, 23),
    "510500": date(2013, 3, 15),
    "159845": date(2021, 3, 31),
}


def load_calendar_open_dates() -> list[date]:
    """从物化日历加载开放日（date 类型）。"""
    cal = pl.read_parquet(PROJECT_ROOT / "warehouse" / "calendar" / "market_calendar_SSE.parquet")
    raw = cal.filter(pl.col("is_open") == 1).get_column("cal_date").to_list()
    return sorted([date(int(d[:4]), int(d[4:6]), int(d[6:])) for d in raw])


def share_coverage_start_date(code: str, share_first_date: date) -> date:
    """覆盖起点 = max(listing_date, 份额数据可用起点)。R-01 路径B。"""
    listing = LIST_DATES[code]
    return max(listing, share_first_date)


def build_share_daily_with_semantics(
    raw_shares: pl.DataFrame,
    open_dates: list[date],
    code: str,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """份额归一化 + 语义分层。

    返回 (canonical_trading_share_daily, normalized_nontrading_share_observation, share_semantics_by_year)
    """
    if raw_shares.is_empty():
        empty = pl.DataFrame(
            schema={
                "trade_date": pl.Date, "ts_code": pl.Utf8, "raw_total_shares": pl.Int64,
                "source_record_semantics": pl.Utf8, "is_observed_record": pl.Boolean,
                "reconstruction_mode": pl.Utf8, "future_confirmation_used": pl.Boolean, "source": pl.Utf8,
            }
        )
        empty2 = pl.DataFrame(
            schema={
                "nontrading_date": pl.Date, "prev_open_date": pl.Date, "next_open_date": pl.Date,
                "fd_share": pl.Float64, "source": pl.Utf8, "raw_hash": pl.Utf8,
            }
        )
        return empty, empty2, empty

    open_set = set(open_dates)
    # fd_share 万份 → 份
    df = raw_shares.with_columns(
        (pl.col("fd_share").cast(pl.Float64) * 10000).cast(pl.Int64).alias("raw_total_shares"),
        (
            pl.col("trade_date").str.slice(0, 4) + "-"
            + pl.col("trade_date").str.slice(4, 2) + "-"
            + pl.col("trade_date").str.slice(6, 2)
        ).alias("date"),
    )
    df = df.with_columns(pl.col("date").str.to_date().alias("trade_date")).drop("date")

    # 分离交易日与非交易日记录
    trading = df.filter(pl.col("trade_date").is_in(list(open_set)))
    nontrading = df.filter(~pl.col("trade_date").is_in(list(open_set)))

    # 交易日快照：每开放日最多一条（去重）
    trading = trading.unique(subset=["trade_date"], keep="first").sort("trade_date")
    # 语义：检查是否覆盖全部开放日
    trading_dates = set(trading.get_column("trade_date").to_list())
    start = min(trading_dates)
    cal_from_start = [d for d in open_dates if d >= start]

    trading_out = trading.with_columns(
        pl.lit("MIXED_OR_UNKNOWN" if len(nontrading) > 0 else "DAILY_SNAPSHOT").alias("source_record_semantics"),
        pl.lit(True).alias("is_observed_record"),
        pl.lit("PIT_FORWARD_ONLY_RECONSTRUCTION").alias("reconstruction_mode"),
        pl.lit(False).alias("future_confirmation_used"),
        pl.lit("TUSHARE_FUND_SHARE").alias("source"),
    ).select(["trade_date", "ts_code", "raw_total_shares", "source_record_semantics", "is_observed_record",
              "reconstruction_mode", "future_confirmation_used", "source"])

    # 非交易日观察
    if not nontrading.is_empty():
        # 为每条非交易日记录找前一/后一开放日
        non_rows = []
        for r in nontrading.iter_rows(named=True):
            d = r["trade_date"]
            prev = [x for x in open_dates if x < d][-1] if any(x < d for x in open_dates) else None
            nxt = [x for x in open_dates if x > d][0] if any(x > d for x in open_dates) else None
            non_rows.append({
                "nontrading_date": d, "prev_open_date": prev, "next_open_date": nxt,
                "fd_share": r["fd_share"], "source": "TUSHARE_FUND_SHARE", "raw_hash": "",
            })
        nontrading_out = pl.DataFrame(non_rows)
    else:
        nontrading_out = pl.DataFrame(schema={"nontrading_date": pl.Date, "prev_open_date": pl.Date,
                                              "next_open_date": pl.Date, "fd_share": pl.Float64,
                                              "source": pl.Utf8, "raw_hash": pl.Utf8})

    # 逐年语义
    sem_rows = []
    for d in sorted(cal_from_start):
        y = d.year
    for y in sorted({d.year for d in cal_from_start}):
        yr_cal = [d for d in cal_from_start if d.year == y]
        yr_trading = [d for d in yr_cal if d in trading_dates]
        yr_non = [d for d in non_rows if d["nontrading_date"].year == y] if non_rows else []
        if len(yr_non) > 0:
            sem = "MIXED_OR_UNKNOWN"
            detail = "MIXED_SNAPSHOT_PLUS_NONTRADING"
        elif len(yr_cal) == len(yr_trading):
            sem = "DAILY_SNAPSHOT"
            detail = "DAILY_SNAPSHOT"
        else:
            sem = "MIXED_OR_UNKNOWN"
            detail = "DAILY_SNAPSHOT_WITH_GAPS"
        sem_rows.append({
            "security_code": code, "year": y,
            "expected_open_sessions": len(yr_cal), "trading_records": len(yr_trading),
            "non_trading_records": len(yr_non), "missing_trading_days": len(yr_cal) - len(yr_trading),
            "record_semantics": sem, "record_semantics_detail": detail,
            "pit_reconstruction_eligible": True, "future_confirmation_used": False,
        })
    sem_out = pl.DataFrame(sem_rows)

    return trading_out, nontrading_out, sem_out
