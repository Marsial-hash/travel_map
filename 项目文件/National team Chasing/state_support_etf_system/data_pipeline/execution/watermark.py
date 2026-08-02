"""数据集水位线（P3 补丁）：各数据集独立延迟状态与流量发布截止日。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse" / "watermark"


class WatermarkStatus:
    UP_TO_DATE = "UP_TO_DATE"
    EXPECTED_SOURCE_LAG = "EXPECTED_SOURCE_LAG"
    UNEXPECTED_DATA_GAP = "UNEXPECTED_DATA_GAP"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    BLOCKED_BY_QUALITY = "BLOCKED_BY_QUALITY"
    UNKNOWN = "UNKNOWN"


@dataclass
class DatasetWatermark:
    dataset_name: str
    source_id: str
    latest_completed_trade_date: date | None
    latest_observed_trade_date: date | None
    latest_source_expected_trade_date: date | None
    latest_research_available_trade_date: date | None
    latest_published_canonical_trade_date: date | None
    watermark_calculated_at: datetime
    availability_policy_id: str
    watermark_status: str


class WatermarkTracker:
    def __init__(self, warehouse_dir: Path = WAREHOUSE_DIR) -> None:
        self.warehouse_dir = warehouse_dir
        self.warehouse_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.warehouse_dir / "dataset_watermarks.json"
        self._watermarks: dict[str, DatasetWatermark] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._watermarks[k] = DatasetWatermark(**v)

    def _save(self) -> None:
        payload = {k: v.__dict__ for k, v in self._watermarks.items()}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def set_watermark(
        self, dataset_name: str, source_id: str, availability_policy_id: str, **fields: Any
    ) -> DatasetWatermark:
        wm = DatasetWatermark(
            dataset_name=dataset_name,
            source_id=source_id,
            latest_completed_trade_date=fields.get("latest_completed_trade_date"),
            latest_observed_trade_date=fields.get("latest_observed_trade_date"),
            latest_source_expected_trade_date=fields.get("latest_source_expected_trade_date"),
            latest_research_available_trade_date=fields.get("latest_research_available_trade_date"),
            latest_published_canonical_trade_date=fields.get("latest_published_canonical_trade_date"),
            watermark_calculated_at=datetime.now(),
            availability_policy_id=availability_policy_id,
            watermark_status=fields.get("watermark_status", WatermarkStatus.UP_TO_DATE),
        )
        self._watermarks[dataset_name] = wm
        self._save()
        return wm

    def flow_publication_cutoff(self) -> date | None:
        """流量发布截止日 = min(份额/NAV或Close/日历/主数据/生命周期 cutoffs)。"""
        cutoffs: list[date] = []
        for wm in self._watermarks.values():
            if wm.latest_research_available_trade_date is not None:
                cutoffs.append(wm.latest_research_available_trade_date)
        if not cutoffs:
            return None
        return min(cutoffs)

    def get(self, dataset_name: str) -> DatasetWatermark | None:
        return self._watermarks.get(dataset_name)
