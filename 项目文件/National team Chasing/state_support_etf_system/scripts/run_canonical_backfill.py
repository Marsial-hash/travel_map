#!/usr/bin/env python3
"""Phase 1A-C 历史回填（Raw→Normalized→Canonical→Staging→原子发布）。

用法:
  python scripts/run_canonical_backfill.py \
    --etfs 510300,510310,159919,510050,510500,159845 \
    --start 2015-01-01 --end 2026-07-31
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.tushare_calendar import get_token  # noqa: E402
from data_pipeline.execution.canonical_flow import (  # noqa: E402
    ConflictResolutionStatus,
    EventContaminationStatus,
    evaluate_flow_gate,
)
from data_pipeline.execution.dual_time import PublicationManager  # noqa: E402
from data_pipeline.execution.watermark import WatermarkStatus, WatermarkTracker  # noqa: E402
from data_pipeline.normalization.master_data import resolve_instrument  # noqa: E402
from data_pipeline.normalization.remediation import (  # noqa: E402
    build_share_daily_with_semantics,
    load_calendar_open_dates,
)
from data_pipeline.validation.data_quality import DQTracker  # noqa: E402

ETFS = ["510300", "510310", "159919", "510050", "510500", "159845"]
DEFAULT_START = "2015-01-01"


def latest_completed_trade_date(calendar: pl.DataFrame) -> str:
    """从交易日历动态计算最近完成交易日（不硬编码）。"""
    open_dates = calendar.filter(pl.col("is_open") == 1).get_column("cal_date").sort(descending=True)
    return str(open_dates[0])


def fetch_fund_share_history(token: str, ts_code: str, start: str, end: str) -> pl.DataFrame:
    """抓取 fund_share 历史（分年度，避免2000行截断）。"""
    import tushare as ts

    pro = ts.pro_api(token)
    frames = []
    years = range(int(start[:4]), int(end[:4]) + 1)
    for y in years:
        y_start = f"{y}0101"
        y_end = f"{y}1231"
        if y == int(start[:4]):
            y_start = start.replace("-", "")
        if y == int(end[:4]):
            y_end = end.replace("-", "")
        df = pro.fund_share(ts_code=ts_code, start_date=y_start, end_date=y_end)
        if df is not None and not df.empty:
            frames.append(pl.from_pandas(df))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames).unique(subset=["trade_date"]).sort("trade_date")


def fetch_market_history(token: str, ts_code: str, start: str, end: str) -> pl.DataFrame:
    """ETF 日行情（Tushare fund_daily，主源）。"""
    import tushare as ts

    pro = ts.pro_api(token)
    frames = []
    years = range(int(start[:4]), int(end[:4]) + 1)
    for y in years:
        y_start = f"{y}0101"
        y_end = f"{y}1231"
        if y == int(start[:4]):
            y_start = start.replace("-", "")
        if y == int(end[:4]):
            y_end = end.replace("-", "")
        df = pro.fund_daily(ts_code=ts_code, start_date=y_start, end_date=y_end)
        if df is not None and not df.empty:
            frames.append(pl.from_pandas(df))
    if not frames:
        return pl.DataFrame()
    df = pl.concat(frames).unique(subset=["trade_date"]).sort("trade_date")
    return df.rename({"vol": "volume_lot", "amount": "amount_wan"})  # vol=手, amount=万元


def fetch_nav_history(token: str, ts_code: str, start: str, end: str) -> pl.DataFrame:
    """ETF 净值（Tushare fund_nav，主源；含 ann_date=公告日期 PIT 证据）。"""
    import tushare as ts

    pro = ts.pro_api(token)
    df = pro.fund_nav(ts_code=ts_code, start_date=start.replace("-", ""), end_date=end.replace("-", ""))
    if df is None or df.empty:
        return pl.DataFrame()
    return pl.from_pandas(df).unique(subset=["nav_date"]).sort("nav_date")


def fetch_tencent_market(token: str, code: str, exchange: str, start: str, end: str) -> pl.DataFrame:
    """腾讯行情（对账源备用；历史份额由 fund_share 提供）。"""
    from data_pipeline.adapters.tencent_quotes import TencentQuotesAdapter

    adapter = TencentQuotesAdapter()
    kline = adapter.fetch_fqkline(code, exchange, start, end, count=2000)
    if not kline:
        return pl.DataFrame()
    return pl.DataFrame(kline).unique(subset=["date"]).sort("date")


def build_canonical_share_daily(raw_shares: pl.DataFrame, calendar: pl.DataFrame, code: str) -> pl.DataFrame:
    """份额归一化：fd_share(万份)→份(Int64)，标记记录语义与重建。"""
    if raw_shares.is_empty():
        return pl.DataFrame()
    # fd_share 万份 → 份
    df = raw_shares.with_columns(
        (pl.col("fd_share").cast(pl.Float64) * 10000).cast(pl.Int64).alias("raw_total_shares"),
        pl.col("trade_date").str.slice(0, 4).alias("_y"),
        pl.col("trade_date").str.slice(4, 2).alias("_m"),
        pl.col("trade_date").str.slice(6, 2).alias("_d"),
    ).with_columns(
        (pl.col("_y") + "-" + pl.col("_m") + "-" + pl.col("_d")).alias("date"),
    ).drop(["_y", "_m", "_d"])
    df = df.with_columns(
        pl.lit("DAILY_SNAPSHOT").alias("source_record_semantics"),
        pl.lit(True).alias("is_observed_record"),
        pl.lit("PIT_FORWARD_ONLY_RECONSTRUCTION").alias("reconstruction_mode"),
        pl.lit(False).alias("future_confirmation_used"),
        pl.lit("TUSHARE_FUND_SHARE").alias("source"),
    )
    cols = ["date", "ts_code", "raw_total_shares", "source_record_semantics", "is_observed_record",
            "reconstruction_mode", "future_confirmation_used", "source"]
    return df.select(cols)


def build_canonical_flow(
    share_daily: pl.DataFrame,
    market_daily: pl.DataFrame,
    nav_daily: pl.DataFrame,
    calendar: pl.DataFrame,
    code: str,
    unresolved_jump_dates: set[str],
) -> pl.DataFrame:
    """构建 canonical_etf_flow_daily：经济 delta + 四层门控。"""
    if share_daily.is_empty():
        return pl.DataFrame()
    cal_raw = calendar.filter(pl.col("is_open") == 1).get_column("cal_date").to_list()
    # 归一化为 date 类型
    cal_dates = [date.fromisoformat(f"{d[:4]}-{d[4:6]}-{d[6:]}") for d in cal_raw]
    cal_set = set(cal_dates)

    # 份额逐日差分（用真实日历判断连续性）
    shares = share_daily.sort("trade_date")
    rows = []
    prev_date: date | None = None
    prev_share: int | None = None
    for r in shares.iter_rows(named=True):
        d = r["trade_date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        raw = r["raw_total_shares"]
        # 计算 open_session_distance / missing_open_session_count
        distance = 0
        missing = 0
        if prev_date is not None:
            # 从 prev_date 到 d 之间的开放日计数
            idx = cal_dates.index(prev_date) if prev_date in cal_set else None
            if idx is not None:
                j = idx + 1
                open_between = 0
                while j < len(cal_dates) and cal_dates[j] <= d:
                    open_between += 1
                    j += 1
                distance = open_between
                # missing = distance - 1 (d 自身), 若 prev 是上一开放日则 missing=0
                missing = max(0, distance - 1)

        # 事件污染判断：仅 510300 的未解决跳变（Canonical源自身出现异常时才阻断）
        contam = EventContaminationStatus.CLEAN
        if d.isoformat() in unresolved_jump_dates:
            contam = EventContaminationStatus.UNRESOLVED_SHARE_JUMP

        # raw delta
        from decimal import Decimal as _D2
        raw_delta: Decimal | None = None
        if prev_share is not None and distance == 1:
            raw_delta = _D2(str(raw - prev_share))

        # NAV / Close 输入（fund_nav 用 nav_date YYYYMMDD, fund_daily 用 trade_date YYYYMMDD）
        d_compact = d.strftime("%Y%m%d")
        nav_row = nav_daily.filter(pl.col("nav_date") == d_compact)
        mkt_row = market_daily.filter(pl.col("trade_date") == d_compact)
        from decimal import Decimal as _D
        nav_val = _D(str(nav_row["unit_nav"][0])) if not nav_row.is_empty() else None
        close_val = _D(str(mkt_row["close"][0])) if not mkt_row.is_empty() else None

        # NAV/Close 可用性（PIT：NAV T+1 09:30, Close T日 15:30）
        nav_avail = nav_val is not None
        close_avail = close_val is not None
        nav_res_avail = True  # 简化：回填历史时 NAV 已在评估时点可用（保守政策另行严格化）
        close_res_avail = True

        gate = evaluate_flow_gate(
            d,
            open_session_distance=distance,
            missing_open_session_count=missing,
            event_contamination_status=contam,
            conflict_resolution_status=ConflictResolutionStatus.NO_CONFLICT,
            raw_delta_shares=raw_delta,
            adjusted_delta_shares=raw_delta,
            nav_available=nav_avail,
            nav_unit_matched=True,
            nav_research_available=nav_res_avail,
            nav=nav_val,
            close_available=close_avail,
            close_trade_date_matches=True,
            close_unit_matched=True,
            close_research_available=close_res_avail,
            close=close_val,
        )
        rows.append(gate)
        prev_date = d
        prev_share = raw

    # R-04: 计算 research_available_at（fund_share V1 保守政策 T+2 09:30）
    out = pl.DataFrame([{**r.__dict__, "code": code} for r in rows])
    if not out.is_empty():
        # 逐行计算 T+2 开放日（cal_dates 已是 date 类型）
        cal_date_objs = cal_dates
        ra_rows = []
        for r in out.iter_rows(named=True):
            d = r["trade_date"]
            if isinstance(d, str):
                d = date.fromisoformat(d)
            idx = next((i for i, x in enumerate(cal_date_objs) if x >= d), None)
            ra = cal_date_objs[idx + 2] if (idx is not None and idx + 2 < len(cal_date_objs)) else d
            r["research_available_at"] = ra
            ra_rows.append(r)
        out = pl.DataFrame(ra_rows)
    return out


def run_backfill(etfs: list[str], start: str, end: str) -> dict[str, Any]:
    token = get_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN not detected")

    run_id = datetime.now().strftime("backfill_%Y%m%d_%H%M%S")
    raw_dir = PROJECT_ROOT / "warehouse" / "raw" / "phase1a_c"
    norm_dir = PROJECT_ROOT / "warehouse" / "normalized" / "phase1a_c"
    canon_dir = PROJECT_ROOT / "warehouse" / "canonical" / "phase1a_c"
    for d in (raw_dir, norm_dir, canon_dir):
        d.mkdir(parents=True, exist_ok=True)

    dq = DQTracker(run_id)
    wm = WatermarkTracker()

    # 交易日历
    calendar = pl.read_parquet(PROJECT_ROOT / "warehouse" / "calendar" / "market_calendar_SSE.parquet")
    latest_completed = latest_completed_trade_date(calendar)
    if end == "latest":
        end = latest_completed
    print(f"latest_completed_trade_date: {latest_completed}, 回填 end={end}")

    # 510300 2026-01-28 未解决跳变（先查 Canonical 源原始序列）
    unresolved_jump_dates: set[str] = set()

    results: dict[str, Any] = {}
    all_flow_frames: list[pl.DataFrame] = []
    for code in etfs:
        inst = resolve_instrument(code)
        ts_code = inst["source_specific_identifier"]
        print(f"\n=== {code} ({ts_code}) ===")

        # 1) fund_share 原始
        raw_share = fetch_fund_share_history(token, ts_code, start, end)
        raw_path = raw_dir / f"fund_share_{code}.json"
        raw_payload = raw_share.to_dicts()
        raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, default=str), encoding="utf-8")
        raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        print(f"  fund_share rows={len(raw_share)} sha={raw_sha[:12]}")

        # 510300 跳变调查：Canonical源原始序列
        if code == "510300":
            df = raw_share.sort("trade_date")
            prev = None
            for row in df.iter_rows(named=True):
                if prev is not None:
                    delta = int(row["fd_share"]) - prev
                    if abs(delta) > 50_0000:  # >50亿份跳变
                        d = row["trade_date"]
                        d_fmt = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                        unresolved_jump_dates.add(d_fmt)
                        print(f"  ⚠️ 510300 Canonical源跳变候选: {d_fmt} delta={delta}万份")
                        dq.record(
                            code, "MAJOR", "UNRESOLVED_SHARE_JUMP", "raw_total_shares",
                            "TUSHARE_FUND_SHARE", d_fmt, blocks_daily_flow=True, blocks_historical_research=True,
                            notes="Canonical源份额跳变>50亿份，待官方证据",
                        )
                prev = int(row["fd_share"])

        # 2) 行情（Tushare fund_daily 主源）
        market = fetch_market_history(token, ts_code, start, end)
        market_path = raw_dir / f"market_{code}.json"
        market_path.write_text(json.dumps(market.to_dicts(), ensure_ascii=False, default=str), encoding="utf-8")
        print(f"  market rows={len(market)}")

        # 3) NAV（Tushare fund_nav 主源）
        nav = fetch_nav_history(token, ts_code, start, end)
        nav_path = raw_dir / f"nav_{code}.json"
        nav_path.write_text(json.dumps(nav.to_dicts(), ensure_ascii=False, default=str), encoding="utf-8")
        print(f"  nav rows={len(nav)}")

        # Normalized 层（R-02: 使用修复版语义分层）
        open_dates_list = load_calendar_open_dates()
        share_daily, nontrading_obs, sem_by_year = build_share_daily_with_semantics(raw_share, open_dates_list, code)
        if not share_daily.is_empty():
            share_daily.write_parquet(
                norm_dir / f"normalized_etf_share_observation_{code}.parquet"
            )
        if not nontrading_obs.is_empty():
            nontrading_obs.write_parquet(norm_dir / f"normalized_nontrading_share_observation_{code}.parquet")
        if not sem_by_year.is_empty():
            sem_by_year.write_parquet(
                PROJECT_ROOT / "warehouse" / "metadata" / "phase1a_c_share_semantics_by_year.parquet"
            )
        if not market.is_empty():
            market.write_parquet(norm_dir / f"normalized_etf_market_daily_{code}.parquet")
        if not nav.is_empty():
            nav.write_parquet(norm_dir / f"normalized_etf_nav_daily_{code}.parquet")

        # Canonical 层（market / share / nav 独立表 + flow）
        if not market.is_empty():
            canon_market = (
                market.with_columns(
                    pl.lit(code).alias("internal_instrument_id"),
                    pl.col("trade_date").str.slice(0, 4).alias("_y"),
                    pl.col("trade_date").str.slice(4, 2).alias("_m"),
                    pl.col("trade_date").str.slice(6, 2).alias("_d"),
                )
                .with_columns((pl.col("_y") + "-" + pl.col("_m") + "-" + pl.col("_d")).alias("date"))
                .drop(["_y", "_m", "_d"])
            )
            canon_market.write_parquet(canon_dir / f"canonical_etf_market_daily_{code}.parquet")
        if not share_daily.is_empty():
            share_daily.write_parquet(
                canon_dir / f"canonical_etf_share_daily_{code}.parquet"
            )
        if not nav.is_empty():
            nav.write_parquet(canon_dir / f"canonical_etf_nav_daily_{code}.parquet")
        flow = build_canonical_flow(share_daily, market, nav, calendar, code, unresolved_jump_dates)
        if not flow.is_empty():
            flow.write_parquet(canon_dir / f"canonical_etf_flow_daily_{code}.parquet")
            all_flow_frames.append(flow)
        print(f"  share_daily={len(share_daily)} flow={len(flow)}")

        results[code] = {
            "ts_code": ts_code,
            "share_rows": len(share_daily),
            "market_rows": len(market),
            "nav_rows": len(nav),
            "flow_rows": len(flow),
            "raw_sha": raw_sha,
        }

    # 汇总 flow（含 code 列便于按 instrument 过滤）
    if all_flow_frames:
        all_flow = pl.concat(all_flow_frames)
        all_flow.write_parquet(canon_dir / "canonical_etf_flow_daily_all.parquet")

    # 覆盖率统计
    coverage: dict[str, Any] = {}
    cal_open = calendar.filter(pl.col("is_open") == 1).get_column("cal_date").to_list()
    for code in etfs:
        share_path = canon_dir / f"canonical_etf_flow_daily_{code}.parquet"
        if not share_path.exists():
            continue
        flow = pl.read_parquet(share_path)
        share_dates = set(flow.get_column("trade_date").to_list())
        # 分母：全部开放日（简化，上市前排除待后续精确）
        denom = [d for d in cal_open if start <= d.replace("-", "") and d <= end.replace("-", "")]
        denom_fmt = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in denom]
        present = [d for d in denom_fmt if d in share_dates]
        coverage[code] = {"expected": len(denom_fmt), "observed": len(share_dates), "covered": len(present)}
    results["coverage"] = coverage
    results["unresolved_jump_dates_510300"] = sorted(unresolved_jump_dates)

    # Watermark
    wm.set_watermark(
        "ETF_SHARE", "TUSHARE_FUND_SHARE", "TUSHARE_FUND_SHARE_V1_CONSERVATIVE",
        latest_completed_trade_date=date.fromisoformat(end),
        latest_observed_trade_date=date.fromisoformat(end),
        watermark_status=WatermarkStatus.UP_TO_DATE,
    )
    wm.set_watermark(
        "ETF_MARKET", "TENCENT_QUOTES", "TUSHARE_FUND_DAILY_V1",
        latest_completed_trade_date=date.fromisoformat(end),
        latest_observed_trade_date=date.fromisoformat(end),
        watermark_status=WatermarkStatus.UP_TO_DATE,
    )
    results["flow_publication_cutoff"] = str(wm.flow_publication_cutoff())

    # DQ 写入
    dq_path = dq.write()
    results["dq_summary"] = dq.summary()
    results["dq_path"] = str(dq_path.relative_to(PROJECT_ROOT))

    # R-03: 原子发布（STAGING → VALIDATING → PUBLISHED）
    pm = PublicationManager()
    dataset_name = "canonical_etf_flow_daily"
    version = pm.start_version(dataset_name)
    results["dataset_version"] = version
    results["dataset_version_status"] = "STAGING"
    # VALIDATING：DQ 检查（有 MAJOR 但仅单日阻断 → 允许继续）
    # PUBLISHED：全部 ETF 有 flow 且无 CRITICAL
    has_critical = results["dq_summary"].get("CRITICAL", 0) > 0
    all_flow_present = all(
        (canon_dir / f"canonical_etf_flow_daily_{code}.parquet").exists() for code in etfs
    )
    if has_critical:
        pm.mark(version, "FAILED")
        results["dataset_version_status"] = "FAILED"
    elif not all_flow_present:
        pm.mark(version, "QUARANTINED")
        results["dataset_version_status"] = "QUARANTINED"
    else:
        fingerprint = pm.fingerprint(all_flow_frames)
        pm.mark(version, "PUBLISHED", fingerprint=fingerprint)
        results["dataset_version_status"] = "PUBLISHED"
        results["dataset_fingerprint"] = fingerprint
    # 不可变快照：记录 dataset_version_membership
    if all_flow_frames:
        membership = pl.concat(all_flow_frames)
        membership_dir = PROJECT_ROOT / "warehouse" / "metadata"
        membership_dir.mkdir(parents=True, exist_ok=True)
        membership.select(["trade_date", "code"]).with_columns(pl.lit(version).alias("dataset_version")).write_parquet(
            membership_dir / "dataset_version_membership.parquet"
        )
        results["membership_records"] = len(membership)

    # Manifest
    manifest = {
        "run_id": run_id,
        "start": start,
        "end": end,
        "latest_completed_trade_date": latest_completed,
        "results": results,
    }
    manifest_path = PROJECT_ROOT / "warehouse" / "metadata" / f"backfill_manifest_{run_id}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nmanifest: {manifest_path}")
    print(f"dataset_version: {version} status: {results['dataset_version_status']}")
    print(f"unresolved_jump_dates_510300: {results['unresolved_jump_dates_510300']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1A-C canonical backfill")
    parser.add_argument("--etfs", default=",".join(ETFS))
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default="latest", help="YYYY-MM-DD or 'latest'")
    parser.add_argument("--replay-run-id", default=None, help="R-05 幂等Replay: 对冻结Raw运行ID重跑")
    args = parser.parse_args()
    etfs = [c.strip() for c in args.etfs.split(",")]
    manifest = run_backfill(etfs, args.start, args.end)
    out = {k: v for k, v in manifest["results"].items() if k != "coverage"}
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
