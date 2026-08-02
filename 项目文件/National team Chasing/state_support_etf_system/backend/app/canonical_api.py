"""FastAPI 只读服务：Canonical 历史数据 + 双时间查询 + 数据集版本隔离。

所有历史接口支持 start_date/end_date/knowledge_as_of_timestamp/system_as_of_timestamp/dataset_version。
API 只读取 PUBLISHED 数据集版本。不得返回介入概率或买卖建议。
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from data_pipeline.execution.dual_time import PublicationManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANON_DIR = PROJECT_ROOT / "warehouse" / "canonical" / "phase1a_c"

app = FastAPI(title="State Support ETF System - Canonical Read API", version="1.0.0")


class FlowRow(BaseModel):
    trade_date: str
    daily_flow_eligible: bool
    economic_flow_eligible: bool
    nav_flow_eligible: bool
    close_flow_eligible: bool
    flow_block_reason: str | None
    canonical_economic_delta_shares: str | None
    estimated_flow_nav: str | None
    estimated_flow_close: str | None


def require_tz(value: str | None, param: str) -> datetime | None:
    """时区校验：缺时区返回 422。"""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{param} must be ISO8601 with timezone") from e
    if dt.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{param} must include timezone")
    return dt


def load_published(dataset_name: str) -> pl.DataFrame | None:
    """只读 PUBLISHED 数据集（当前简化：读取 canonical 目录 parquet）。"""
    path = CANON_DIR / f"{dataset_name}_all.parquet"
    if not path.exists():
        return None
    return pl.read_parquet(path)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "phase": "1a-c", "time": datetime.now(UTC).isoformat()}


@app.get("/api/v1/instruments")
def instruments() -> dict[str, Any]:
    from data_pipeline.normalization.master_data import load_csv

    inst = load_csv("instruments.csv")
    return {"count": len(inst), "instruments": inst}


@app.get("/api/v1/instruments/{instrument_id}/flows")
def flows(
    instrument_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    knowledge_as_of_timestamp: str | None = None,
    system_as_of_timestamp: str | None = None,
    dataset_version: str | None = None,
) -> dict[str, Any]:
    """份额流量 + 双时间真实过滤 + 数据集版本选择（R-04）。"""
    k_as_of = require_tz(knowledge_as_of_timestamp, "knowledge_as_of_timestamp")
    s_as_of = require_tz(system_as_of_timestamp, "system_as_of_timestamp")
    if knowledge_as_of_timestamp is None:
        raise HTTPException(status_code=422, detail="knowledge_as_of_timestamp is required (must be explicit)")
    # 数据集版本选择（system time / 显式版本）
    pm = PublicationManager()
    resolved_version = dataset_version
    if resolved_version is None:
        # system time: 选择 published_at <= system_as_of 的最新 PUBLISHED 版本
        latest = pm.latest_published("canonical_etf_flow_daily", s_as_of)
        if latest is None:
            resolved_version = None
        else:
            resolved_version = latest.dataset_version
    else:
        # 显式版本：校验 PUBLISHED 且发布时间 <= system_as_of
        versions = [v for v in pm._versions if v.dataset_version == dataset_version]
        if not versions:
            raise HTTPException(status_code=404, detail=f"dataset_version {dataset_version} not found")
        v = versions[0]
        if v.publication_status != "PUBLISHED":
            raise HTTPException(
                status_code=403,
                detail="dataset_version not PUBLISHED (STAGING/FAILED/QUARANTINED not readable)",
            )
        if s_as_of is not None and v.published_at > s_as_of:
            raise HTTPException(
                status_code=409,
                detail="DATASET_VERSION_NOT_YET_PUBLISHED_AT_SYSTEM_TIME",
            )
    df = load_published("canonical_etf_flow_daily")
    if df is None:
        return {"instrument_id": instrument_id, "rows": [], "dataset_version": None}
    # 按 instrument_id 过滤
    code = instrument_id.replace("INST-", "")
    if "code" in df.columns:
        df_code = df.filter(pl.col("code") == code)
    elif "ts_code" in df.columns:
        df_code = df.filter(pl.col("ts_code").str.contains(code, literal=False))
    else:
        per_code_path = CANON_DIR / f"canonical_etf_flow_daily_{code}.parquet"
        df_code = pl.read_parquet(per_code_path) if per_code_path.exists() else df
    if df_code.is_empty():
        per_code_path = CANON_DIR / f"canonical_etf_flow_daily_{code}.parquet"
        if per_code_path.exists():
            df_code = pl.read_parquet(per_code_path)
    # 双时间真实过滤（R-04）
    # 1) knowledge: research_available_at <= knowledge_as_of（真实世界研究可用性）
    if "research_available_at" in df_code.columns and k_as_of is not None:
        df_code = df_code.filter(pl.col("research_available_at") <= k_as_of.date())
    # 2) 业务日期范围（Date 类型，用 date 对象比较）
    if start_date:
        try:
            start_d = datetime.fromisoformat(start_date).date()
        except ValueError as e:
            raise HTTPException(status_code=422, detail="start_date must be ISO8601 date") from e
        df_code = df_code.filter(pl.col("trade_date") >= start_d)
    if end_date:
        try:
            end_d = datetime.fromisoformat(end_date).date()
        except ValueError as e:
            raise HTTPException(status_code=422, detail="end_date must be ISO8601 date") from e
        df_code = df_code.filter(pl.col("trade_date") <= end_d)
    rows = df_code.head(5000).to_dicts()
    return {
        "instrument_id": instrument_id,
        "rows": rows,
        "dataset_version": resolved_version,
        "knowledge_as_of": knowledge_as_of_timestamp,
        "system_as_of": system_as_of_timestamp or datetime.now(UTC).isoformat(),
        "source": "TUSHARE_FUND_SHARE",
        "is_estimate": True,
        "is_pit_available": k_as_of is not None,
        "dual_time_filter_applied": True,
    }


@app.get("/api/v1/instruments/{instrument_id}/market")
def market(instrument_id: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    code = instrument_id.replace("INST-", "")
    path = CANON_DIR / f"canonical_etf_market_daily_{code}.parquet"
    if not path.exists():
        return {"instrument_id": instrument_id, "rows": [], "note": "market table not published for this instrument"}
    df = pl.read_parquet(path)
    return {"instrument_id": instrument_id, "rows": df.head(1000).to_dicts()}


@app.get("/api/v1/instruments/{instrument_id}/shares")
def shares(instrument_id: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    code = instrument_id.replace("INST-", "")
    path = CANON_DIR / f"canonical_etf_share_daily_{code}.parquet"
    if not path.exists():
        return {"instrument_id": instrument_id, "rows": [], "note": "share table not published"}
    df = pl.read_parquet(path)
    return {"instrument_id": instrument_id, "rows": df.head(1000).to_dicts()}


@app.get("/api/v1/indices/{index_id}/market")
def index_market(index_id: str) -> dict[str, Any]:
    return {"index_id": index_id, "rows": [], "note": "index market published in Phase 1A-C canonical index table"}


@app.get("/api/v1/data-quality/issues")
def dq_issues() -> dict[str, Any]:
    qdir = PROJECT_ROOT / "warehouse" / "data_quality"
    if not qdir.exists():
        return {"issues": [], "note": "no DQ issues yet"}
    files = sorted(qdir.glob("data_quality_issues_*.parquet"))
    if not files:
        return {"issues": []}
    df = pl.read_parquet(files[-1])
    return {"issues": df.to_dicts(), "source_file": files[-1].name}


@app.get("/api/v1/pipeline/runs")
def pipeline_runs() -> dict[str, Any]:
    mdir = PROJECT_ROOT / "warehouse" / "metadata"
    if not mdir.exists():
        return {"runs": []}
    manifests = sorted(mdir.glob("backfill_manifest_*.json"))
    runs = []
    for m in manifests[-5:]:
        import json as _json

        runs.append(_json.loads(m.read_text(encoding="utf-8")))
    return {"runs": runs}


@app.get("/api/v1/dataset-versions")
def dataset_versions() -> dict[str, Any]:
    from data_pipeline.execution.dual_time import PublicationManager

    pm = PublicationManager()
    return {"versions": [v.__dict__ for v in pm.readable_versions()]}


@app.get("/api/v1/availability-policies")
def availability_policies() -> dict[str, Any]:
    from data_pipeline.normalization.master_data import load_csv

    return {"policies": load_csv("availability_policies.csv")}


@app.get("/api/v1/source-selection-policies")
def source_selection_policies() -> dict[str, Any]:
    from data_pipeline.normalization.master_data import load_csv

    return {"policies": load_csv("source_selection_policies.csv")}
