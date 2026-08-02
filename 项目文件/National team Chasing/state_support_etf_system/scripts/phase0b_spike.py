#!/usr/bin/env python3
"""Phase 0B 数据可行性 Spike。

用法:
  python scripts/phase0b_spike.py \\
    --etfs 510300,510310,159919,510050,510500,159845 \\
    --start 2026-05-05 \\
    --end 2026-07-31

输出:
  warehouse/raw/phase0b/      原始响应
  warehouse/normalized/phase0b/
  warehouse/canonical/phase0b/ (含物化保护)
  warehouse/reference_compatible/phase0b/
  warehouse/metadata/phase0b_runs.parquet
  docs/data_feasibility_report.md
  docs/phase0b_go_no_go.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.capability_probes import (  # noqa: E402
    ExchangeSharesAdapter,
    FundDisclosuresAdapter,
    TushareFundDailyAdapter,
)
from data_pipeline.adapters.fund_nav import FundNavAdapter  # noqa: E402
from data_pipeline.adapters.index_turnover import SohuHisqAdapter  # noqa: E402
from data_pipeline.adapters.share_semantics import determine_record_semantics  # noqa: E402
from data_pipeline.adapters.tencent_quotes import TencentQuotesAdapter  # noqa: E402
from data_pipeline.adapters.tushare_calendar import TokenDetector  # noqa: E402
from data_pipeline.adapters.tushare_shares import FundShareAdapter  # noqa: E402
from data_pipeline.calendar.instrument_code_resolver import InstrumentCodeResolver  # noqa: E402
from data_pipeline.calendar.market_calendar import MarketCalendar  # noqa: E402
from data_pipeline.validation.canonical_guard import CanonicalMaterializationGuard  # noqa: E402


@dataclass
class EtfSpikeResult:
    code: str
    name: str
    exchange: str
    tushare_code: str
    quotes_rows: int = 0
    sohu_rows: int = 0
    nav_rows: int = 0
    fund_share: dict[str, Any] | None = None
    semantics: dict[str, Any] | None = None
    gaps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    probes_notes: dict[str, Any] = field(default_factory=dict)


def save_raw(warehouse: Path, name: str, payload: dict[str, Any] | list[Any]) -> str:
    """保存原始响应并计算哈希。"""
    raw_dir = warehouse / "raw" / "phase0b"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{name}.json"
    text = json.dumps(payload, ensure_ascii=False, default=str)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_spike(etfs: list[str], start: str, end: str) -> dict[str, Any]:
    results: list[EtfSpikeResult] = []
    resolver = InstrumentCodeResolver()
    quotes = TencentQuotesAdapter()
    sohu = SohuHisqAdapter()
    nav = FundNavAdapter()
    share_adapter = FundShareAdapter()
    exchange_probe = ExchangeSharesAdapter()
    disclosure_probe = FundDisclosuresAdapter()
    fund_daily_probe = TushareFundDailyAdapter()
    token_detected = TokenDetector.detected()

    # 交易日历（离线构建：2026-05-05 ~ 2026-07-31 开放日按周一至周五近似）
    open_dates = []
    d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    while d <= end_d:
        if d.weekday() < 5:  # 周一至周五（无节假日修正，标注近似）
            open_dates.append(d)
        d = date.fromisoformat(d.isoformat()).fromordinal(d.toordinal() + 1)
    calendar = MarketCalendar.from_open_dates("SSE", open_dates, source="APPROX_WEEKDAY", version="v0-approx")
    print(f"TUSHARE_TOKEN detected: {'yes' if token_detected else 'no'}")

    for code in etfs:
        r = EtfSpikeResult(code=code, name="", exchange="", tushare_code="")
        try:
            inst = resolver.resolve(code)
            r.exchange = inst.exchange
            r.tushare_code = inst.tushare_code
        except KeyError as e:
            r.errors.append(f"resolve: {e}")
            results.append(r)
            continue
        try:
            # 1) 行情
            q = quotes.fetch_quote(code, r.exchange)
            if q:
                r.name = q.name
            kline = quotes.fetch_fqkline(code, r.exchange, start, end)
            r.quotes_rows = len(kline)
            save_raw(PROJECT_ROOT / "warehouse", f"quote_{code}", {"kline": kline, "quote": q.__dict__ if q else None})
        except Exception as e:  # noqa: BLE001
            r.errors.append(f"quotes: {str(e)[:200]}")
        try:
            # 2) 搜狐真实成交额
            sohu_rows = sohu.fetch_etf(code, start, end)
            r.sohu_rows = len(sohu_rows)
            save_raw(PROJECT_ROOT / "warehouse", f"sohu_etf_{code}", [row.__dict__ for row in sohu_rows])
        except Exception as e:  # noqa: BLE001
            r.errors.append(f"sohu: {str(e)[:200]}")
        try:
            # 3) NAV
            nav_rows = nav.fetch_history(code, start, end)
            r.nav_rows = len(nav_rows)
            save_raw(PROJECT_ROOT / "warehouse", f"nav_{code}", [row.__dict__ for row in nav_rows])
        except Exception as e:  # noqa: BLE001
            r.errors.append(f"nav: {str(e)[:200]}")
        try:
            # 4) fund_share（真实Token实测）
            result = share_adapter.fetch_complete_range(
                r.tushare_code, date.fromisoformat(start), date.fromisoformat(end), calendar
            )
            r.fund_share = {
                "api_status": result.api_status,
                "returned_rows": result.returned_rows,
                "returned_min_date": result.returned_min_date,
                "returned_max_date": result.returned_max_date,
                "hit_row_limit": result.hit_row_limit,
                "is_potentially_truncated": result.is_potentially_truncated,
                "error_message": result.api_error_message,
            }
            if result.data is not None and not result.data.empty:
                save_raw(PROJECT_ROOT / "warehouse", f"fund_share_{code}", result.data.to_dict(orient="records"))
                verdict = determine_record_semantics(result.data, open_dates)
                r.semantics = {
                    "semantics": verdict.semantics.value,
                    "open_days_total": verdict.open_days_total,
                    "records_count": verdict.records_count,
                    "records_per_open_day": verdict.records_per_open_day,
                    "unchanged_transfer_samples": verdict.unchanged_transfer_samples,
                    "missing_days_with_same_value": verdict.missing_days_with_same_value,
                    "missing_days_with_changed_value": verdict.missing_days_with_changed_value,
                    "forward_fill_unambiguous": verdict.forward_fill_unambiguous,
                    "evidence": verdict.evidence,
                }
        except Exception as e:  # noqa: BLE001
            r.errors.append(f"fund_share: {str(e)[:200]}")
        results.append(r)

    # 能力探针
    probes = {
        "exchange_shares": exchange_probe.probe(),
        "fund_disclosures": disclosure_probe.probe(),
        "fund_daily": fund_daily_probe.probe(),
    }

    # Canonical 物化保护：份额源批准状态 = fund_share 全部 SUCCESS_WITH_DATA 且语义明确
    share_approved = all(
        r.fund_share
        and r.fund_share["api_status"] == "SUCCESS_WITH_DATA"
        and r.semantics
        and r.semantics["forward_fill_unambiguous"]
        for r in results
        if r.fund_share
    ) and len(results) == len(etfs) and all(r.fund_share for r in results)

    guard = CanonicalMaterializationGuard(
        canonical_dir=PROJECT_ROOT / "warehouse" / "canonical",
        share_source_approved=share_approved,
    )

    run_meta = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "etfs": etfs,
        "start": start,
        "end": end,
        "token_detected": token_detected,
        "share_source_approved": share_approved,
        "results": [r.__dict__ for r in results],
        "probes": {k: v.__dict__ for k, v in probes.items()},
    }
    # manifest
    meta_dir = PROJECT_ROOT / "warehouse" / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([run_meta]).to_parquet(meta_dir / "phase0b_runs.parquet")

    if not share_approved:
        guard.write_blocked_marker(reason="canonical share source not approved", run_metadata=run_meta)
    else:
        # 批准：仅写Schema，不物化真实流量（Phase 1A-C 才做）
        guard.write_schema_only({"etf_daily_share": "schema_v1", "etf_daily_flow": "schema_v1"})

    return run_meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0B data feasibility spike")
    parser.add_argument("--etfs", required=True, help="comma separated ETF codes")
    parser.add_argument("--start", required=True, help="start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="end date YYYY-MM-DD")
    args = parser.parse_args()

    etfs = [c.strip() for c in args.etfs.split(",")]
    meta = run_spike(etfs, args.start, args.end)

    print(json.dumps({k: v for k, v in meta.items() if k != "results"}, ensure_ascii=False, indent=2))
    for r in meta["results"]:
        fs = r.get("fund_share") or {}
        sem = r.get("semantics") or {}
        print(
            f"{r['code']}: quotes={r['quotes_rows']} sohu={r['sohu_rows']} nav={r['nav_rows']} "
            f"fund_share_status={fs.get('api_status')} rows={fs.get('returned_rows')} "
            f"semantics={sem.get('semantics')} errors={len(r['errors'])}"
        )
    print(f"share_source_approved: {meta['share_source_approved']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
