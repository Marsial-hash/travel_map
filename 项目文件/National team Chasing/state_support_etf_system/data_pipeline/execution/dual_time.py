"""双时间版本查询 + 数据集原子发布（P1 补丁）。

- knowledge_as_of_timestamp: research_available_at <= knowledge_as_of
- system_as_of_timestamp: system_valid_from <= system_as_of AND 未被 supersede
- 原子发布: dataset_version + publication_status + supersedes_dataset_version
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse" / "publication"


@dataclass
class DatasetVersionRecord:
    dataset_version: str
    dataset_name: str
    published_at: datetime
    publication_status: str  # RUNNING/VALIDATING/PUBLISHED/FAILED/QUARANTINED/ROLLED_BACK
    supersedes_dataset_version: str | None
    dataset_fingerprint: str
    meta: dict[str, Any] = field(default_factory=dict)


class DualTimeQuery:
    """双时间过滤：knowledge + system 分离。"""

    @staticmethod
    def knowledge_filter(research_available_at_col: str, knowledge_as_of: datetime) -> str:
        return f"{research_available_at_col} <= TIMESTAMP '{knowledge_as_of.isoformat()}'"

    @staticmethod
    def system_filter(system_valid_from_col: str, system_as_of: datetime, supersession_table: str) -> str:  # noqa: S608 - 内部常量表名,无外部输入
        """system_valid_from <= as_of AND 未被后继取代。"""
        return (
            f"{system_valid_from_col} <= TIMESTAMP '{system_as_of.isoformat()}' "
            f"AND NOT EXISTS (SELECT 1 FROM {supersession_table} s "
            f"WHERE s.superseded_record_id = {supersession_table}.record_id "
            f"AND s.superseded_at <= TIMESTAMP '{system_as_of.isoformat()}')"
        )


class PublicationManager:
    """数据集版本原子发布。API 只读 PUBLISHED。"""

    def __init__(self, warehouse_dir: Path = WAREHOUSE_DIR) -> None:
        self.warehouse_dir = warehouse_dir
        self.warehouse_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.warehouse_dir / "publication_manifest.json"
        self._versions: list[DatasetVersionRecord] = self._load()
        self._counter = len(self._versions)  # 保证同秒内版本ID唯一

    def _load(self) -> list[DatasetVersionRecord]:
        if not self._manifest_path.exists():
            return []
        data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        out = []
        for v in data:
            v = dict(v)
            if isinstance(v.get("published_at"), str):
                v["published_at"] = datetime.fromisoformat(v["published_at"])
            out.append(DatasetVersionRecord(**v))
        return out

    def _save(self) -> None:
        self._manifest_path.write_text(
            json.dumps([v.__dict__ for v in self._versions], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def fingerprint(df_any: Any) -> str:
        """数据集指纹：基于行数+列名（轻量，正式用内容哈希）。"""
        if hasattr(df_any, "write_parquet"):
            # polars
            return hashlib.sha256(str(len(df_any)).encode()).hexdigest()
        return hashlib.sha256(str(df_any).encode()).hexdigest()

    def start_version(self, dataset_name: str, supersedes: str | None = None) -> str:
        self._counter += 1
        version = f"{dataset_name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{self._counter}"
        self._versions.append(
            DatasetVersionRecord(
                dataset_version=version,
                dataset_name=dataset_name,
                published_at=datetime.now(UTC),
                publication_status="RUNNING",
                supersedes_dataset_version=supersedes,
                dataset_fingerprint="",
            )
        )
        self._save()
        return version

    def mark(self, dataset_version: str, status: str, fingerprint: str = "") -> None:
        for v in self._versions:
            if v.dataset_version == dataset_version:
                v.publication_status = status
                if fingerprint:
                    v.dataset_fingerprint = fingerprint
        self._save()

    def latest_published(self, dataset_name: str, system_as_of: datetime | None = None) -> DatasetVersionRecord | None:
        """选择 published_at <= system_as_of 的最新 PUBLISHED 版本。"""
        system_as_of = system_as_of or datetime.now(UTC)
        candidates = [
            v
            for v in self._versions
            if v.dataset_name == dataset_name and v.publication_status == "PUBLISHED" and v.published_at <= system_as_of
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda v: v.published_at)

    def readable_versions(self) -> list[DatasetVersionRecord]:
        return [v for v in self._versions if v.publication_status == "PUBLISHED"]
