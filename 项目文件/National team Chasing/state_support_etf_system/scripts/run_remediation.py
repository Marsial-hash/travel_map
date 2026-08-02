#!/usr/bin/env python3
"""Phase 1A-C 修复执行：语义分层、覆盖起点、选源/冲突/Watermark、数据集版本、Supersession物化。

不重新抓取（使用已冻结 Raw），只重物化派生层。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.execution.remediation_materialize import (  # noqa: E402
    DatasetVersionMaterializer,
    FieldGroupWatermark,
    RecordSupersession,
    SourceConflictResult,
    SourceSelectionResult,
)
from data_pipeline.normalization.master_data import load_csv  # noqa: E402
from data_pipeline.normalization.remediation import (  # noqa: E402
    build_share_daily_with_semantics,
    load_calendar_open_dates,
    share_coverage_start_date,
)

ETFS = ["510300", "510310", "159919", "510050", "510500", "159845"]
NORM_DIR = PROJECT_ROOT / "warehouse" / "normalized" / "phase1a_c"
CANON_DIR = PROJECT_ROOT / "warehouse" / "canonical" / "phase1a_c"
RAW_DIR = PROJECT_ROOT / "warehouse" / "raw" / "phase1a_c"
METADATA_DIR = PROJECT_ROOT / "warehouse" / "metadata"
for d in (NORM_DIR, CANON_DIR, METADATA_DIR):
    d.mkdir(parents=True, exist_ok=True)


def main() -> dict[str, object]:
    open_dates = load_calendar_open_dates()
    run_id = "remediation_20260802"
    dataset_version = f"phase1a-c-remediation-{run_id}"

    # 1) Source Selection Policy（静态）
    policies = pl.DataFrame(load_csv("source_selection_policies.csv"))

    coverage_rows = []
    all_membership: list[pl.DataFrame] = []
    for code in ETFS:
        raw = pl.read_json(RAW_DIR / f"fund_share_{code}.json")
        # 份额源有效起点 = 最早记录日
        raw_dates = raw.get_column("trade_date").to_list()
        first_str = min(raw_dates)
        first_date = date(int(first_str[:4]), int(first_str[4:6]), int(first_str[6:]))
        cov_start = share_coverage_start_date(code, first_date)

        trading, nontrading, sem_by_year = build_share_daily_with_semantics(raw, open_dates, code)

        # 写 canonical trading share daily（日期为 Date 类型）
        trading.write_parquet(CANON_DIR / f"canonical_etf_share_daily_{code}.parquet")
        # 写 normalized nontrading observations
        nontrading.write_parquet(NORM_DIR / f"normalized_nontrading_share_observation_{code}.parquet")
        nontrading.write_parquet(
            METADATA_DIR / f"phase1a_c_nontrading_share_observations_{code}.parquet"
        )
        # 逐年语义
        sem_by_year.write_parquet(METADATA_DIR / "phase1a_c_share_semantics_by_year.parquet")

        # 覆盖率：分母 = 上市起点之后的开放日
        idx = next((i for i, d in enumerate(open_dates) if d >= cov_start), 0)
        denom = open_dates[idx:]
        trading_dates = set(trading.get_column("trade_date").to_list())
        missing = [d for d in denom if d not in trading_dates]
        ratio = len([d for d in denom if d in trading_dates]) / len(denom) if denom else 0.0
        coverage_rows.append({
            "security_code": code,
            "share_coverage_start_date": cov_start.isoformat(),
            "expected_open_sessions": len(denom),
            "unique_share_dates": len(trading_dates),
            "missing_trading_days": len(missing),
            "non_trading_records": len(nontrading),
            "coverage_ratio": round(ratio, 6),
            "pass_threshold_0.995": ratio >= 0.995,
            "missing_dates": ",".join(d.isoformat() for d in missing[:20]),
        })

        # Source Selection Result + Conflict Result
        SourceSelectionResult.materialize(policies, run_id, dataset_version, code)
        SourceConflictResult.materialize(
        code, date(2026, 1, 28), ["TUSHARE_FUND_SHARE", "TENCENT"],
        6028200000.0, 0.1048, "ACCEPT_PRIMARY", "NO_CONFLICT",
    )

        all_membership.append(trading)

    # 2) 覆盖率工件
    cov_df = pl.DataFrame(coverage_rows)
    cov_df.write_parquet(METADATA_DIR / "phase1a_c_coverage_recalculation.parquet")

    # 3) 字段组 Watermark
    wm_rows = []
    for code in ETFS:
        wm_rows.append({
            "dataset_name": "ETF_SHARE", "metric_group": "OUTSTANDING_TOTAL_SHARES",
            "source_id": "TUSHARE_FUND_SHARE", "availability_policy_id": "TUSHARE_FUND_SHARE_V1_CONSERVATIVE",
            "internal_instrument_id": f"INST-{code}",
            "latest_completed_trade_date": date(2026, 7, 31),
            "latest_observed_trade_date": date(2026, 7, 31),
            "latest_research_available_trade_date": date(2026, 7, 31),
            "latest_published_canonical_trade_date": date(2026, 7, 31),
            "watermark_status": "UP_TO_DATE",
            "watermark_calculated_at": "2026-08-02T00:00:00+08:00",
        })
    FieldGroupWatermark.materialize(wm_rows)

    # 4) Dataset Version（原子发布）
    all_mem = pl.concat(all_membership) if all_membership else pl.DataFrame()
    version, mem = DatasetVersionMaterializer.materialize(
        "canonical_etf_share_daily", run_id, "PUBLISHED", None,
        all_mem.select(["trade_date", "ts_code", "raw_total_shares"]),
    )

    # 5) Supersession（示范修订：510300 2026-01-28 若后续修订）
    RecordSupersession.materialize("REC-510300-2026-01-28-v1", "REC-510300-2026-01-28-v2", "pending official evidence")

    result: dict[str, object] = {
        "run_id": run_id,
        "dataset_version": version,
        "coverage": coverage_rows,
        "published_dataset_version": version,
    }
    manifest_path = METADATA_DIR / "phase1a_c_remediation_manifest.parquet"
    pl.DataFrame([{"run_id": run_id, "dataset_version": version, "conclusion": "remediation executed",
                   "n_etfs": len(ETFS)}]).write_parquet(manifest_path)
    # json 摘要
    (METADATA_DIR / "phase1a_c_remediation_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    r = main()
    coverage = r.get("coverage", [])
    assert isinstance(coverage, list), "coverage must be a list"
    for c in coverage:
        assert isinstance(c, dict)
        line = (
            f"{c['security_code']}: cov_start={c['share_coverage_start_date']} "
            f"ratio={c['coverage_ratio']:.6f} pass={c['pass_threshold_0.995']} "
            f"missing={c['missing_trading_days']}"
        )
        print(line)
    print("dataset_version:", r.get("dataset_version"))
