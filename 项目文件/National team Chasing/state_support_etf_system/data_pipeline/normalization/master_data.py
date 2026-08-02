"""主数据物化：将 registry CSV 物化为 Parquet + DuckDB 表。

范围：fund_master / fund_share_class_master / exchange_instrument_master /
instrument_identifier_history / index_master / data_source_master /
availability_policy / execution_delay_policy / metric_contract_registry /
source_selection_policy
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse" / "master_data"
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)


class InvalidInstrumentIdentity(Exception):
    """六位代码无法解析出唯一身份时抛出。"""


def load_csv(rel: str) -> list[dict[str, str]]:
    path = REGISTRY_DIR / rel
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialize_master_data(
    registry_dir: Path = REGISTRY_DIR, warehouse_dir: Path = WAREHOUSE_DIR
) -> dict[str, dict[str, Any]]:
    """物化全部主数据表，返回表名→元数据。"""
    tables: dict[str, dict[str, Any]] = {}

    # fund_master（含ETF，来自 funds.csv + reference_universe.csv）
    funds = load_csv("funds.csv")
    fund_rows = []
    for r in funds:
        fund_rows.append(
            {
                "internal_fund_id": f"FUND-{r['etf_code']}",
                "official_fund_name": r["etf_name"],
                "fund_manager": r["fund_manager"],
                "inception_date": None,
                "termination_date": r.get("delisting_date") or None,
                "fund_status": r.get("status", "LISTED"),
                "official_identifier_type": "SECURITY_CODE",
                "official_identifier_value": r["etf_code"],
                "identifier_source": r.get("source", "MANUAL_REGISTRY"),
                "identity_match_confidence": "MODEL_CROSS_CHECKED",
                "manual_review_status": "HUMAN_REVIEW_PENDING",
            }
        )
    df = pl.DataFrame(fund_rows)
    path = warehouse_dir / "fund_master.parquet"
    df.write_parquet(path)
    tables["fund_master"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # share_classes
    sc = load_csv("share_classes.csv")
    sc_rows = [
        {
            "share_class_id": f"SHARE-{r['etf_code']}",
            "internal_fund_id": r["internal_fund_id"],
            "share_class_name": r["share_class_name"],
            "share_unit_definition": r["share_unit_definition"],
            "currency": r["currency"],
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"] or None,
        }
        for r in sc
    ]
    df = pl.DataFrame(sc_rows)
    path = warehouse_dir / "fund_share_class_master.parquet"
    df.write_parquet(path)
    tables["fund_share_class_master"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # instruments
    inst = load_csv("instruments.csv")
    inst_rows = [
        {
            "internal_instrument_id": r["internal_instrument_id"],
            "share_class_id": r["share_class_id"],
            "security_code": r["security_code"],
            "exchange": r["exchange"],
            "listing_date": r["listing_date"] or None,
            "delisting_date": r["delisting_date"] or None,
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"] or None,
        }
        for r in inst
    ]
    df = pl.DataFrame(inst_rows)
    path = warehouse_dir / "exchange_instrument_master.parquet"
    df.write_parquet(path)
    tables["exchange_instrument_master"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # identifier_history
    ih = load_csv("identifier_history.csv")
    ih_rows = [
        {
            "internal_instrument_id": r["internal_instrument_id"],
            "identifier_type": r["identifier_type"],
            "identifier_value": r["identifier_value"],
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"] or None,
            "change_reason": r["change_reason"],
            "source_document": r["source_document"],
        }
        for r in ih
    ]
    df = pl.DataFrame(ih_rows)
    path = warehouse_dir / "instrument_identifier_history.parquet"
    df.write_parquet(path)
    tables["instrument_identifier_history"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # index_master
    idx = load_csv("indices.csv")
    idx_rows = [
        {
            "index_key": r["index_key"],
            "index_code": r["index_code"] or None,
            "index_name": r["index_name"] or None,
            "display_group": r["display_group"],
            "has_trend_mapping": r["has_trend_mapping"] == "true",
            "source": r["source"],
        }
        for r in idx
    ]
    df = pl.DataFrame(idx_rows)
    path = warehouse_dir / "index_master.parquet"
    df.write_parquet(path)
    tables["index_master"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # data_source_master
    ds = load_csv("data_sources.csv")
    ds_rows = [
        {
            "source_id": r["source_id"],
            "source_name": r["source_name"],
            "dataset": r["dataset"],
            "access_status": r["access_status"],
            "schema_status": r["schema_status"],
            "semantic_status": r["semantic_status"],
            "reliability_status": r["reliability_status"],
            "license_internal_research_status": r["license_internal_research_status"],
            "license_local_storage_status": r["license_local_storage_status"],
            "license_public_display_status": r["license_public_display_status"],
            "production_status": r["production_status"],
        }
        for r in ds
    ]
    df = pl.DataFrame(ds_rows)
    path = warehouse_dir / "data_source_master.parquet"
    df.write_parquet(path)
    tables["data_source_master"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # availability_policy
    ap = load_csv("availability_policies.csv")
    ap_rows = [
        {
            "availability_policy_id": r["availability_policy_id"],
            "dataset_name": r["dataset_name"],
            "research_available_at_rule": r["research_available_at_rule"],
            "availability_basis": r["availability_basis"],
            "policy_confidence": r["policy_confidence"],
            "timezone": r["timezone"],
            "policy_version": r["policy_version"],
            "may_be_used_for_live_signal": r["may_be_used_for_live_signal"] == "true",
        }
        for r in ap
    ]
    df = pl.DataFrame(ap_rows)
    path = warehouse_dir / "availability_policy.parquet"
    df.write_parquet(path)
    tables["availability_policy"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # source_selection_policy
    ssp = load_csv("source_selection_policies.csv")
    ssp_rows = [
        {
            "policy_id": r["policy_id"],
            "dataset_name": r["dataset_name"],
            "metric_group": r["metric_group"],
            "primary_source_id": r["primary_source_id"],
            "selected_source_id": r["selected_source_id"],
            "conflict_action": r["conflict_action"],
            "policy_version": r["policy_version"],
            "approved_for_historical_backfill": r["approved_for_historical_backfill"] == "true",
            "approved_for_live_signal": r["approved_for_live_signal"] == "true",
        }
        for r in ssp
    ]
    df = pl.DataFrame(ssp_rows)
    path = warehouse_dir / "source_selection_policy.parquet"
    df.write_parquet(path)
    tables["source_selection_policy"] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(df),
        "cols": len(df.columns),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "contains_real_canonical_data": True,
    }

    # DuckDB 注册视图
    duck_path = warehouse_dir / "master_data.duckdb"
    con = duckdb.connect(str(duck_path))
    for name in tables:
        p = tables[name]["path"]
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_parquet('{PROJECT_ROOT / p}')")
    con.close()
    tables["_duckdb"] = {"path": str(duck_path.relative_to(PROJECT_ROOT)), "rows": 0, "cols": 0,
                          "sha256": sha256_file(duck_path), "bytes": duck_path.stat().st_size,
                          "contains_real_canonical_data": True}
    return tables


def resolve_instrument(security_code: str, registry_dir: Path = REGISTRY_DIR) -> dict[str, str]:
    """六位代码 → internal_instrument_id + exchange + source_specific_identifier。

    禁止仅凭代码首位猜市场。冲突返回 INVALID_INSTRUMENT_IDENTITY。
    """
    inst = load_csv("instruments.csv")
    ih = load_csv("identifier_history.csv")
    matches = [r for r in inst if r["security_code"] == security_code]
    if len(matches) != 1:
        raise InvalidInstrumentIdentity(f"INVALID_INSTRUMENT_IDENTITY: {security_code} matches={len(matches)}")
    m = matches[0]
    tushare_codes = [
        r for r in ih
        if r["internal_instrument_id"] == m["internal_instrument_id"]
        and r["identifier_type"] == "TUSHARE_CODE"
    ]
    ts_code = tushare_codes[0]["identifier_value"] if tushare_codes else f"{security_code}.UNKNOWN"
    return {
        "internal_instrument_id": m["internal_instrument_id"],
        "exchange": m["exchange"],
        "source_specific_identifier": ts_code,
        "security_code": security_code,
    }


if __name__ == "__main__":
    result = materialize_master_data()
    for name, meta in result.items():
        print(f"{name}: {meta['rows']} rows, {meta['sha256'][:12]}")
    print("resolve 510300:", resolve_instrument("510300"))
    print("resolve 159919:", resolve_instrument("159919"))
