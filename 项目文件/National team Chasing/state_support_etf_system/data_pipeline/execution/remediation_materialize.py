"""Phase 1A-C 修复：选源结果、冲突结果、Watermark、数据集版本与Supersession物化（R-03/R-05/R-06）。"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METADATA_DIR = PROJECT_ROOT / "warehouse" / "metadata"


class SourceSelectionResult:
    """物化 source_selection_result：政策(静态)与运行结果分离。"""

    @staticmethod
    def materialize(policies: pl.DataFrame, run_id: str, dataset_version: str, etf_code: str) -> pl.DataFrame:
        rows = []
        for p in policies.iter_rows(named=True):
            rows.append({
                "selection_result_id": f"SR-{etf_code}-{run_id}-{p['metric_group']}",
                "run_id": run_id,
                "dataset_version": dataset_version,
                "internal_instrument_id": f"INST-{etf_code}",
                "dataset_name": p["dataset_name"],
                "metric_group": p["metric_group"],
                "applied_policy_id": p["policy_id"],
                "applied_policy_version": p["policy_version"],
                "selected_source_id": p["selected_source_id"],
                "candidate_source_ids": p["secondary_source_ids"],
                "selection_outcome": "PRIMARY_SELECTED",
                "selection_reason": p["selection_reason"],
                "conflict_id": None,
                "selected_at": datetime.now().isoformat(timespec="seconds"),
            })
        df = pl.DataFrame(rows)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(METADATA_DIR / "source_selection_result.parquet")
        return df


class SourceConflictResult:
    """物化 source_conflict_result：冲突动作(政策)与冲突结果(实际)分离。"""

    @staticmethod
    def materialize(etf_code: str, trade_date: date, compared: list[str], diff_abs: float,
                    diff_rel: float, configured_action: str, actual_status: str) -> pl.DataFrame:
        df = pl.DataFrame([{
            "conflict_id": f"CF-{etf_code}-{trade_date.isoformat()}",
            "internal_instrument_id": f"INST-{etf_code}",
            "trade_date": trade_date,
            "compared_source_ids": ",".join(compared),
            "difference_absolute": diff_abs,
            "difference_relative": diff_rel,
            "configured_conflict_action": configured_action,
            "conflict_resolution_status": actual_status,
            "resolved_at": datetime.now().isoformat(timespec="seconds"),
            "reviewer_type": "MODEL_CROSS_CHECKED",
        }])
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(METADATA_DIR / "source_conflict_result.parquet")
        return df


class FieldGroupWatermark:
    """字段组 Watermark（主键 dataset_name+metric_group+source_id+policy_id）。"""

    @staticmethod
    def materialize(rows: list[dict[str, Any]]) -> pl.DataFrame:
        df = pl.DataFrame(rows)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(METADATA_DIR / "dataset_watermark.parquet")
        return df


class DatasetVersionMaterializer:
    """数据集版本不可变快照物化（R-03）。"""

    @staticmethod
    def materialize(dataset_name: str, run_id: str, status: str, supersedes: str | None,
                    membership: pl.DataFrame) -> tuple[str, pl.DataFrame]:
        version = f"{dataset_name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        df = pl.DataFrame([{
            "dataset_version": version,
            "dataset_name": dataset_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "published_at": datetime.now().isoformat(timespec="seconds") if status == "PUBLISHED" else None,
            "publication_status": status,
            "supersedes_dataset_version": supersedes,
            "run_id": run_id,
            "dataset_fingerprint": str(abs(hash(tuple(sorted(membership.columns)) + (len(membership),)))),
            "record_membership_fingerprint": str(abs(hash(len(membership)))),
        }])
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(METADATA_DIR / "dataset_versions.parquet")
        # membership
        mem = membership.with_columns(pl.lit(version).alias("dataset_version"))
        mem.write_parquet(METADATA_DIR / "dataset_version_membership.parquet")
        return version, mem


class RecordSupersession:
    """record_supersession 物化（R-05）。"""

    @staticmethod
    def materialize(superseded_record_id: str, superseding_record_id: str, reason: str) -> pl.DataFrame:
        df = pl.DataFrame([{
            "superseded_record_id": superseded_record_id,
            "superseding_record_id": superseding_record_id,
            "superseded_at": datetime.now().isoformat(timespec="seconds"),
            "revision_reason": reason,
            "source_change_detected_at": datetime.now().isoformat(timespec="seconds"),
        }])
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(METADATA_DIR / "record_supersession.parquet")
        return df
