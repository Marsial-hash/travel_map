"""数据质量体系：data_quality_issue 物化 + 覆盖率计算。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse" / "data_quality"


class Severity:
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


@dataclass
class DQIssue:
    issue_id: str
    run_id: str
    dataset_version: str | None
    internal_instrument_id: str
    trade_date: str | None
    severity: str
    issue_type: str
    affected_metric: str
    source: str
    detected_at: str
    resolution_status: str = "OPEN"
    blocks_daily_flow: bool = False
    blocks_historical_research: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    resolution_notes: str = ""


class DQTracker:
    def __init__(self, run_id: str, warehouse_dir: Path = WAREHOUSE_DIR) -> None:
        self.run_id = run_id
        self.warehouse_dir = warehouse_dir
        self.warehouse_dir.mkdir(parents=True, exist_ok=True)
        self.issues: list[DQIssue] = []

    def record(
        self,
        internal_instrument_id: str,
        severity: str,
        issue_type: str,
        affected_metric: str,
        source: str,
        trade_date: str | None = None,
        blocks_daily_flow: bool = False,
        blocks_historical_research: bool = False,
        dataset_version: str | None = None,
        evidence_ids: list[str] | None = None,
        notes: str = "",
    ) -> None:
        self.issues.append(
            DQIssue(
                issue_id=f"DQ-{uuid.uuid4().hex[:12]}",
                run_id=self.run_id,
                dataset_version=dataset_version,
                internal_instrument_id=internal_instrument_id,
                trade_date=trade_date,
                severity=severity,
                issue_type=issue_type,
                affected_metric=affected_metric,
                source=source,
                detected_at=datetime.now().isoformat(timespec="seconds"),
                blocks_daily_flow=blocks_daily_flow,
                blocks_historical_research=blocks_historical_research,
                evidence_ids=evidence_ids or [],
                resolution_notes=notes,
            )
        )

    def write(self) -> Path:
        rows = [i.__dict__ for i in self.issues]
        df = pl.DataFrame(rows) if rows else pl.DataFrame(
            schema={
                "issue_id": pl.Utf8, "run_id": pl.Utf8, "dataset_version": pl.Utf8,
                "internal_instrument_id": pl.Utf8, "trade_date": pl.Utf8, "severity": pl.Utf8,
                "issue_type": pl.Utf8, "affected_metric": pl.Utf8, "source": pl.Utf8,
                "detected_at": pl.Utf8, "resolution_status": pl.Utf8,
                "blocks_daily_flow": pl.Boolean, "blocks_historical_research": pl.Boolean,
                "evidence_ids": pl.List(pl.Utf8), "resolution_notes": pl.Utf8,
            }
        )
        path = self.warehouse_dir / f"data_quality_issues_{self.run_id}.parquet"
        df.write_parquet(path)
        return path

    def summary(self) -> dict[str, int]:
        sev = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0}
        for i in self.issues:
            sev[i.severity] = sev.get(i.severity, 0) + 1
        return sev


def compute_coverage(
    expected_dates: list[str],
    observed_dates: list[str],
    excluded_dates: set[str],
    block_reasons: dict[str, str],
) -> dict[str, Any]:
    """覆盖率计算：分母排除上市前/退市后/确认停牌/确认调整日。"""
    denominator = [d for d in expected_dates if d not in excluded_dates]
    if not denominator:
        return {"denominator": 0, "coverage_ratio": 0.0, "blocked": 0, "unknown_blocked": 0}
    present = [d for d in denominator if d in set(observed_dates)]
    blocked = [d for d in denominator if d not in set(observed_dates)]
    unknown_blocked = [d for d in blocked if block_reasons.get(d, "UNKNOWN") == "UNKNOWN"]
    return {
        "denominator": len(denominator),
        "covered": len(present),
        "blocked": len(blocked),
        "coverage_ratio": round(len(present) / len(denominator), 6),
        "unknown_blocked": len(unknown_blocked),
        "unknown_blocked_ratio": round(len(unknown_blocked) / len(denominator), 6),
    }
